import json

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_generation import (
    ChapterCandidate,
    ChapterHandoff,
    ChapterMeasurement,
    ChapterPlanRow,
    Finding,
    OutlineProposal,
)
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.modules.longform.candidates import CandidateService
from writestory_be.modules.longform.findings import FindingService
from writestory_be.modules.longform.resync_job import ResyncJobService, ResyncRequest
from writestory_be.modules.longform.revise_job import ReviseJobRequest, ReviseJobService
from writestory_be.modules.longform.write_service import WriteJobRequest, WriteJobService

router = APIRouter(tags=["longform"])


class JobWriteRequest(BaseModel):
    type: str = "write"
    work_id: str
    chapter_no: int | None = Field(default=None, ge=1)
    mode: str = "review_each"
    idempotency_key: str = Field(min_length=8, max_length=200)
    instruction: str | None = None
    chapter_id: str | None = None
    base_revision_id: str | None = None
    scope: dict = Field(default_factory=dict)
    finding_ids: list[str] = Field(default_factory=list)


@router.post("/v1/jobs", status_code=status.HTTP_202_ACCEPTED, name="create_write_job")
async def create_job(body: JobWriteRequest, runtime: RuntimeDep):
    if body.type == "revise":
        if not body.chapter_id or not body.base_revision_id or not body.instruction:
            raise AppError(ErrorCode.VALIDATION, detail={"field": "revise_request"})
        return await ReviseJobService(runtime).enqueue(
            body.work_id,
            ReviseJobRequest(
                chapter_id=body.chapter_id,
                base_revision_id=body.base_revision_id,
                mode=body.mode,
                scope=body.scope,
                instruction=body.instruction,
                finding_ids=body.finding_ids,
                idempotency_key=body.idempotency_key,
            ),
        )
    if body.type != "write" or body.chapter_no is None:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "type_or_chapter_no"})
    result = await WriteJobService(runtime).enqueue(
        body.work_id,
        WriteJobRequest(
            chapter_no=body.chapter_no,
            mode=body.mode,
            idempotency_key=body.idempotency_key,
            instruction=body.instruction,
        ),
    )
    return result


@router.post("/v1/works/{work_id}/resync", name="create_resync_job")
async def create_resync_job(
    work_id: str, body: ResyncRequest, runtime: RuntimeDep, response: Response
):
    result = await ResyncJobService(runtime).create(work_id, body)
    if "job_id" in result:
        response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.get("/v1/chapters/{chapter_id}/candidates", name="list_candidates")
async def list_candidates(
    chapter_id: str, runtime: RuntimeDep, status_filter: str | None = Query(None, alias="status")
):
    return await CandidateService(runtime).list_for_chapter(chapter_id, status_filter)


@router.get("/v1/candidates/{candidate_id}", name="get_candidate")
async def get_candidate(candidate_id: str, runtime: RuntimeDep):
    return await CandidateService(runtime).get(candidate_id)


class CandidateAccept(BaseModel):
    expected_revision_id: str
    paragraph_ids: list[str] | None = None
    note: str | None = None


@router.post("/v1/candidates/{candidate_id}/accept", name="accept_candidate")
async def accept_candidate(candidate_id: str, body: CandidateAccept, runtime: RuntimeDep):
    return await CandidateService(runtime).accept(
        candidate_id,
        expected_revision_id=body.expected_revision_id,
        paragraph_ids=body.paragraph_ids,
        note=body.note,
    )


@router.post("/v1/candidates/{candidate_id}/reject", name="reject_candidate")
async def reject_candidate(candidate_id: str, body: dict, runtime: RuntimeDep):
    return await CandidateService(runtime).reject(candidate_id, body.get("reason"))


@router.post("/v1/jobs/{job_id}/accept", name="accept_job_candidate")
async def accept_job_candidate(job_id: str, body: CandidateAccept, runtime: RuntimeDep):
    async with runtime.ensure_database_services().read_sessions() as session:
        candidate = await session.scalar(
            select(ChapterCandidate)
            .where(ChapterCandidate.job_id == job_id, ChapterCandidate.status == "ready")
            .order_by(ChapterCandidate.created_at.desc())
            .limit(1)
        )
        if candidate is None:
            raise AppError(ErrorCode.NOT_FOUND)
        candidate_id = candidate.id
    return await CandidateService(runtime).accept(
        candidate_id,
        expected_revision_id=body.expected_revision_id,
        paragraph_ids=body.paragraph_ids,
        note=body.note,
    )


@router.get("/v1/works/{work_id}/findings", name="list_findings")
async def list_findings(
    work_id: str,
    runtime: RuntimeDep,
    status_filter: str | None = Query(None, alias="status"),
    chapter: int | None = None,
    severity: str | None = None,
    source: str | None = None,
):
    return await FindingService(runtime).list(
        work_id, status=status_filter, chapter=chapter, severity=severity, source=source
    )


class FindingDecision(BaseModel):
    note: str | None = None


@router.post("/v1/findings/{finding_id}/resolve", name="resolve_finding")
async def resolve_finding(finding_id: str, body: FindingDecision, runtime: RuntimeDep):
    return await FindingService(runtime).decide(finding_id, "resolve", body.note)


@router.post("/v1/findings/{finding_id}/dismiss", name="dismiss_finding")
async def dismiss_finding(finding_id: str, body: FindingDecision, runtime: RuntimeDep):
    return await FindingService(runtime).decide(finding_id, "dismiss", body.note)


class UserFindingCreate(BaseModel):
    kind: str
    severity: str
    message: str = Field(min_length=1)
    evidence: list[dict] = Field(default_factory=list)


@router.post("/v1/chapters/{chapter_id}/findings", name="create_user_finding")
async def create_user_finding(chapter_id: str, body: UserFindingCreate, runtime: RuntimeDep):
    async with runtime.ensure_database_services().read_sessions() as session:
        chapter = await session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
    return await FindingService(runtime).create_user(
        chapter,
        kind=body.kind,
        severity=body.severity,
        message=body.message,
        evidence=body.evidence,
    )


@router.get("/v1/works/{work_id}/continuity", name="get_continuity")
async def get_continuity(work_id: str, runtime: RuntimeDep):
    async def read(session):
        work = await session.get(Work, work_id)
        if work is None:
            raise AppError(ErrorCode.NOT_FOUND)
        handoff = await session.scalar(
            select(ChapterHandoff)
            .where(ChapterHandoff.work_id == work_id, ChapterHandoff.is_current.is_(True))
            .order_by(ChapterHandoff.chapter_no.desc())
            .limit(1)
        )
        findings = (
            await session.scalars(
                select(Finding).where(Finding.work_id == work_id, Finding.status == "open")
            )
        ).all()
        return {
            "status": work.continuity_status,
            "chapter_no": work.continuity_chapter_no,
            "reason": json.loads(work.continuity_reason) if work.continuity_reason else None,
            "latest_handoff": (
                {
                    "chapter_no": handoff.chapter_no,
                    "revision_id": handoff.revision_id,
                    "ending_state": json.loads(handoff.ending_state),
                    "open_threads": json.loads(handoff.open_threads),
                }
                if handoff
                else None
            ),
            "open_findings": {
                level: sum(x.severity == level for x in findings)
                for level in ("blocker", "major", "minor")
            },
        }

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/works/{work_id}/continuity/metrics", name="get_continuity_metrics")
async def get_continuity_metrics(
    work_id: str,
    runtime: RuntimeDep,
    from_chapter: int | None = Query(None, alias="from"),
    to_chapter: int | None = Query(None, alias="to"),
):
    async def read(session):
        if await session.get(Work, work_id) is None:
            raise AppError(ErrorCode.NOT_FOUND)
        query = select(ChapterMeasurement).where(ChapterMeasurement.work_id == work_id)
        if from_chapter is not None:
            query = query.where(ChapterMeasurement.chapter_no >= from_chapter)
        if to_chapter is not None:
            query = query.where(ChapterMeasurement.chapter_no <= to_chapter)
        rows = (await session.scalars(query)).all()
        values = [json.loads(x.metrics_json) for x in rows]
        return {
            "count": len(rows),
            "state_applied_false": sum(not x.get("state_applied", True) for x in values),
            "seam_pass_rate": (
                sum(bool(x.get("seam_pass_first_try")) for x in values) / len(values)
                if values
                else None
            ),
            "measurements": values,
        }

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/chapters/{chapter_id}/plan", name="get_chapter_plan")
async def get_plan(chapter_id: str, runtime: RuntimeDep):
    async def read(session):
        chapter = await session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        row = await session.scalar(
            select(ChapterPlanRow)
            .where(
                ChapterPlanRow.work_id == chapter.work_id,
                ChapterPlanRow.chapter_no == chapter.chapter_no,
                ChapterPlanRow.status == "active",
            )
            .order_by(ChapterPlanRow.created_at.desc())
            .limit(1)
        )
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return {
            "id": row.id,
            "input_hash": row.input_hash,
            "plan": json.loads(row.plan_json),
            "edited_by_user": row.edited_by_user,
        }

    return await runtime.ensure_database_services().read(read)


class HandoffUpdate(BaseModel):
    expected_handoff_revision: int = Field(ge=1)
    ending_state: dict
    open_threads: list = Field(default_factory=list)
    next_opening_requirements: list = Field(default_factory=list)
    note: str | None = None


@router.get("/v1/chapters/{chapter_id}/handoff", name="get_chapter_handoff")
async def get_handoff(chapter_id: str, runtime: RuntimeDep):
    async def read(session):
        chapter = await session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        row = await session.scalar(
            select(ChapterHandoff).where(
                ChapterHandoff.work_id == chapter.work_id,
                ChapterHandoff.chapter_no == chapter.chapter_no,
                ChapterHandoff.is_current.is_(True),
            )
        )
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return {
            "chapter_no": row.chapter_no,
            "revision_id": row.revision_id,
            "handoff_revision": row.handoff_revision,
            "ending_state": json.loads(row.ending_state),
            "open_threads": json.loads(row.open_threads),
            "next_opening_requirements": json.loads(row.next_opening_requirements),
            "note": row.note,
        }

    return await runtime.ensure_database_services().read(read)


@router.put("/v1/chapters/{chapter_id}/handoff", name="update_chapter_handoff")
async def update_handoff(chapter_id: str, body: HandoffUpdate, runtime: RuntimeDep):
    async def write(ctx):
        chapter = await ctx.session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        latest = await ctx.session.scalar(
            select(Chapter.chapter_no)
            .where(
                Chapter.work_id == chapter.work_id,
                Chapter.status == "committed",
                Chapter.deleted_at.is_(None),
            )
            .order_by(Chapter.chapter_no.desc())
            .limit(1)
        )
        if chapter.chapter_no != latest:
            raise AppError(ErrorCode.VALIDATION, detail={"reason": "only_latest_handoff_editable"})
        old = await ctx.session.scalar(
            select(ChapterHandoff).where(
                ChapterHandoff.work_id == chapter.work_id,
                ChapterHandoff.chapter_no == chapter.chapter_no,
                ChapterHandoff.is_current.is_(True),
            )
        )
        if old is None or old.handoff_revision != body.expected_handoff_revision:
            raise AppError(
                ErrorCode.REVISION_CONFLICT,
                detail={
                    "expected_handoff_revision": body.expected_handoff_revision,
                    "current_handoff_revision": old.handoff_revision if old else None,
                },
            )
        old.is_current = False
        old.superseded_at = utcnow_iso()
        row = ChapterHandoff(
            id=new_id(),
            work_id=chapter.work_id,
            chapter_no=chapter.chapter_no,
            revision_id=chapter.current_revision_id,
            handoff_revision=old.handoff_revision + 1,
            ending_state=json.dumps(body.ending_state, ensure_ascii=False),
            tail_text=old.tail_text,
            tail_paragraph_ids=old.tail_paragraph_ids,
            tail_tokens=old.tail_tokens,
            tail_counted_for_model=old.tail_counted_for_model,
            open_threads=json.dumps(body.open_threads, ensure_ascii=False),
            next_opening_requirements=json.dumps(
                body.next_opening_requirements, ensure_ascii=False
            ),
            source="user_edit",
            note=body.note,
            is_current=True,
            created_at=utcnow_iso(),
        )
        ctx.session.add(row)
        return {
            "chapter_no": row.chapter_no,
            "revision_id": row.revision_id,
            "handoff_revision": row.handoff_revision,
            "ending_state": body.ending_state,
            "open_threads": body.open_threads,
            "next_opening_requirements": body.next_opening_requirements,
            "note": row.note,
        }

    return await runtime.ensure_database_services().write(write)


class PlanUpdate(BaseModel):
    expected_plan_id: str
    plan: dict


@router.put("/v1/chapters/{chapter_id}/plan", name="update_chapter_plan")
async def update_plan(chapter_id: str, body: PlanUpdate, runtime: RuntimeDep):
    async def write(ctx):
        chapter = await ctx.session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        old = await ctx.session.get(ChapterPlanRow, body.expected_plan_id)
        if old is None or old.work_id != chapter.work_id or old.chapter_no != chapter.chapter_no:
            raise AppError(ErrorCode.REVISION_CONFLICT)
        old.status = "superseded"
        row = ChapterPlanRow(
            id=new_id(),
            work_id=chapter.work_id,
            chapter_no=chapter.chapter_no,
            input_hash=old.input_hash,
            inputs=old.inputs,
            plan_json=json.dumps(body.plan, ensure_ascii=False),
            status="active",
            edited_by_user=True,
            job_id=old.job_id,
            model_id=old.model_id,
            created_at=utcnow_iso(),
        )
        ctx.session.add(row)
        return {
            "id": row.id,
            "input_hash": row.input_hash,
            "plan": body.plan,
            "edited_by_user": True,
        }

    return await runtime.ensure_database_services().write(write)


@router.post("/v1/outline-proposals/{proposal_id}/apply", name="apply_outline_proposal")
async def apply_outline_proposal(proposal_id: str, body: dict, runtime: RuntimeDep):
    async def write(ctx):
        row = await ctx.session.get(OutlineProposal, proposal_id)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        if row.status != "pending":
            raise AppError(ErrorCode.REVISION_CONFLICT)
        changes = json.loads(row.changes_json)
        requested = body.get("change_ids")
        if requested:
            changes = [change for change in changes if change.get("id") in requested]
        row.status = (
            "applied" if not requested or len(changes) == len(requested) else "partially_applied"
        )
        row.decided_at = utcnow_iso()
        return {
            "id": row.id,
            "chapter_no": row.chapter_no,
            "changes": changes,
            "pacing_assessment": row.pacing_assessment,
            "status": row.status,
        }

    return await runtime.ensure_database_services().write(write)


@router.get("/v1/chapters/{chapter_id}/seam", name="get_chapter_seam")
async def get_seam(chapter_id: str, runtime: RuntimeDep):
    async def read(session):
        chapter = await session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        row = await session.scalar(
            select(ChapterCandidate)
            .where(
                ChapterCandidate.chapter_id == chapter_id, ChapterCandidate.seam_json.is_not(None)
            )
            .order_by(ChapterCandidate.created_at.desc())
            .limit(1)
        )
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return json.loads(row.seam_json)

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/works/{work_id}/outline-proposals", name="list_outline_proposals")
async def list_outline_proposals(
    work_id: str, runtime: RuntimeDep, status_filter: str | None = Query("pending", alias="status")
):
    async def read(session):
        query = select(OutlineProposal).where(OutlineProposal.work_id == work_id)
        if status_filter:
            query = query.where(OutlineProposal.status == status_filter)
        rows = (await session.scalars(query.order_by(OutlineProposal.created_at.desc()))).all()
        return [
            {
                "id": x.id,
                "chapter_no": x.chapter_no,
                "changes": json.loads(x.changes_json),
                "pacing_assessment": x.pacing_assessment,
                "status": x.status,
            }
            for x in rows
        ]

    return await runtime.ensure_database_services().read(read)


@router.post("/v1/outline-proposals/{proposal_id}/reject", name="reject_outline_proposal")
async def reject_outline_proposal(proposal_id: str, runtime: RuntimeDep):
    async def write(ctx):
        row = await ctx.session.get(OutlineProposal, proposal_id)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        if row.status != "pending":
            raise AppError(ErrorCode.REVISION_CONFLICT)
        row.status, row.decided_at = "rejected", utcnow_iso()
        return {"id": row.id, "status": row.status}

    return await runtime.ensure_database_services().write(write)
