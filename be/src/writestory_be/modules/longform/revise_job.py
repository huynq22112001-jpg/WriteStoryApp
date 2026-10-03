from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.chapters import Chapter, ChapterRevision
from writestory_be.infrastructure.db.models.longform_generation import ChapterCandidate
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.jobs.locks import WorkLockManager


class ReviseJobRequest(BaseModel):
    chapter_id: str
    base_revision_id: str
    mode: str
    scope: dict = Field(default_factory=dict)
    instruction: str = Field(min_length=1)
    finding_ids: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ReviseJobService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()
        self.locks = WorkLockManager(self.uow, f"backend:{runtime.pid}")

    async def enqueue(self, work_id: str, body: ReviseJobRequest):
        if body.mode not in {"spot_fix", "polish", "rewrite", "rework"}:
            raise AppError(ErrorCode.VALIDATION, detail={"field": "mode"})
        now, job_id = utcnow_iso(), new_id()

        async def write(ctx):
            existing = await ctx.session.scalar(
                select(Job).where(Job.idempotency_key == body.idempotency_key)
            )
            if existing:
                if (
                    existing.work_id != work_id
                    or existing.base_revision_id != body.base_revision_id
                ):
                    raise AppError(ErrorCode.IDEMPOTENCY_CONFLICT)
                return {"job_id": existing.id, "status": existing.status}
            work = await ctx.session.get(Work, work_id)
            chapter = await ctx.session.get(Chapter, body.chapter_id)
            if work is None or chapter is None or chapter.work_id != work_id:
                raise AppError(ErrorCode.NOT_FOUND)
            if chapter.current_revision_id != body.base_revision_id:
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={
                        "current_revision_id": chapter.current_revision_id,
                        "expected_revision_id": body.base_revision_id,
                    },
                )
            revision = await ctx.session.get(ChapterRevision, body.base_revision_id)
            position = (
                int(
                    await ctx.session.scalar(
                        select(func.max(Job.queue_position)).where(
                            Job.work_id == work_id, Job.status.in_(("queued", "waiting_slot"))
                        )
                    )
                    or 0
                )
                + 1
            )
            ctx.session.add(
                Job(
                    id=job_id,
                    idempotency_key=body.idempotency_key,
                    type="revise",
                    work_id=work_id,
                    status="queued",
                    priority=0,
                    queue_position=position,
                    input_json=json.dumps(
                        {
                            **body.model_dump(mode="json"),
                            "chapter_no": chapter.chapter_no,
                            "paragraphs": json.loads(revision.paragraphs_json),
                        },
                        ensure_ascii=False,
                    ),
                    base_revision_id=body.base_revision_id,
                    attempt=0,
                    created_at=now,
                    updated_at=now,
                    revision=1,
                )
            )
            ctx.add_event(
                "job.queued",
                {"job_type": "revise", "queue_position": position},
                work_id=work_id,
                job_id=job_id,
                chapter_no=chapter.chapter_no,
            )
            return {
                "job_id": job_id,
                "status": "queued",
                "queue_position": position,
                "base_revision_id": body.base_revision_id,
            }

        result = await self.uow.write(write)
        if result["status"] == "queued":
            self.runtime.spawn(self.run(result["job_id"]))
        return result

    async def run(self, job_id: str):
        async with self.uow.read_sessions() as session:
            job = await session.get(Job, job_id)
            if job is None:
                return
            payload = json.loads(job.input_json)
            work_id = job.work_id
        executor = getattr(self.runtime, "revise_executor", None)
        await self.locks.wait_and_acquire(work_id, job_id)

        async def start(ctx):
            row = await ctx.session.get(Job, job_id)
            row.status, row.started_at, row.updated_at = "running", utcnow_iso(), utcnow_iso()
            row.attempt += 1
            candidate = await ctx.session.scalar(
                select(ChapterCandidate)
                .where(ChapterCandidate.job_id == job_id)
                .order_by(ChapterCandidate.created_at)
                .limit(1)
            )
            if candidate is None:
                candidate = ChapterCandidate(
                    id=new_id(),
                    work_id=work_id,
                    chapter_id=payload["chapter_id"],
                    chapter_no=payload["chapter_no"],
                    job_id=job_id,
                    kind="revise",
                    mode=payload["mode"],
                    base_revision_id=payload["base_revision_id"],
                    scope=json.dumps(payload["scope"]),
                    author_instruction=payload["instruction"],
                    content_json="{}",
                    plain_text="",
                    paragraphs_json="[]",
                    ops_json="[]",
                    status="streaming",
                    check_summary="{}",
                    accepted_paragraph_ids="[]",
                    created_at=utcnow_iso(),
                )
                ctx.session.add(candidate)
            else:
                candidate.status = "streaming"
            return candidate.id

        candidate_id = await self.uow.write(start)
        try:
            if executor is None:
                raise RuntimeError("P221 revise executor chưa được đăng ký")
            from writestory_be.infrastructure.ai.progress_adapter import ProgressCheckpointAdapter

            adapter = ProgressCheckpointAdapter(self.runtime, job_id, candidate_id)
            result = await executor.execute(payload, progress=adapter, checkpoint=adapter)
            value = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
            paragraphs = value.get("paragraphs", [])

            async def finish(ctx):
                job = await ctx.session.get(Job, job_id)
                candidate = await ctx.session.get(ChapterCandidate, candidate_id)
                candidate.paragraphs_json = json.dumps(paragraphs, ensure_ascii=False)
                candidate.plain_text = "\n\n".join(p.get("text", "") for p in paragraphs)
                candidate.ops_json = json.dumps(value.get("ops", []), ensure_ascii=False)
                candidate.content_json = json.dumps(value, ensure_ascii=False)
                candidate.status = "ready"
                candidate.ready_at = utcnow_iso()
                job.status, job.wait_reason = "waiting_user", "review_required"
                job.finished_at = job.updated_at = utcnow_iso()
                ctx.add_event(
                    "candidate.ready",
                    {
                        "candidate_id": candidate.id,
                        "chapter_id": candidate.chapter_id,
                        "kind": candidate.kind,
                        "check_summary": {},
                    },
                    work_id=work_id,
                    job_id=job_id,
                    chapter_no=candidate.chapter_no,
                )

            await self.uow.write(finish)
        except Exception as exc:
            failure_reason = str(exc)[:300]

            async def fail(ctx):
                job = await ctx.session.get(Job, job_id)
                candidate = await ctx.session.get(ChapterCandidate, candidate_id)
                job.status, job.error_code = "failed", "INTERNAL"
                job.error_json = json.dumps({"reason": failure_reason})
                job.finished_at = job.updated_at = utcnow_iso()
                if candidate.status == "streaming":
                    candidate.status = "partial"

            await self.uow.write(fail)
        finally:
            await self.locks.release(work_id, job_id)
