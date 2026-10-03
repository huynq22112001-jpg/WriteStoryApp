from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.chapters import Chapter, ChapterRevision
from writestory_be.infrastructure.db.models.longform_generation import ChapterHandoff
from writestory_be.infrastructure.db.models.longform_state import StoryStateRow
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.jobs.locks import WorkLockManager
from writestory_be.modules.longform.continuity import clear_continuity, mark_blocked
from writestory_be.modules.memory.service import MemoryService


class ResyncRequest(BaseModel):
    from_chapter: int = Field(ge=1)
    to_chapter: int | None = Field(default=None, ge=1)
    dry_run: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class ResyncJobService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()
        self.locks = WorkLockManager(self.uow, f"backend:{runtime.pid}")

    async def create(self, work_id: str, body: ResyncRequest):
        async def validate(session):
            work = await session.get(Work, work_id)
            if work is None:
                raise AppError(ErrorCode.NOT_FOUND)
            latest = int(
                await session.scalar(
                    select(func.max(Chapter.chapter_no)).where(
                        Chapter.work_id == work_id,
                        Chapter.status == "committed",
                        Chapter.deleted_at.is_(None),
                    )
                )
                or 0
            )
            end = body.to_chapter or latest
            if body.from_chapter > end or end > latest:
                raise AppError(ErrorCode.VALIDATION, detail={"range": [body.from_chapter, end]})
            state = await session.scalar(
                select(StoryStateRow).where(
                    StoryStateRow.work_id == work_id,
                    StoryStateRow.chapter_no == body.from_chapter - 1,
                    StoryStateRow.is_current.is_(True),
                )
            )
            if state is None:
                raise AppError(ErrorCode.STATE_SNAPSHOT_MISSING)
            chapters = (
                await session.scalars(
                    select(Chapter)
                    .where(
                        Chapter.work_id == work_id,
                        Chapter.chapter_no.between(body.from_chapter, end),
                        Chapter.status == "committed",
                        Chapter.deleted_at.is_(None),
                    )
                    .order_by(Chapter.chapter_no)
                )
            ).all()
            if len(chapters) != end - body.from_chapter + 1:
                raise AppError(ErrorCode.CHAPTER_EMPTY)
            if any(not x.current_revision_id for x in chapters):
                raise AppError(ErrorCode.CHAPTER_EMPTY)
            return {
                "range": [body.from_chapter, end],
                "chapter_count": len(chapters),
                "estimated_ai_calls": len(chapters),
            }

        estimate = await self.uow.read(validate)
        if body.dry_run:
            return estimate
        job_id, now = new_id(), utcnow_iso()

        async def write(ctx):
            idem = body.idempotency_key
            if idem:
                existing = await ctx.session.scalar(select(Job).where(Job.idempotency_key == idem))
                if existing:
                    return {"job_id": existing.id, "status": existing.status}
            end = estimate["range"][1]
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
                    idempotency_key=idem,
                    type="resync",
                    work_id=work_id,
                    status="queued",
                    priority=0,
                    queue_position=position,
                    input_json=json.dumps(
                        {"from_chapter": body.from_chapter, "to_chapter": end}, ensure_ascii=False
                    ),
                    attempt=0,
                    created_at=now,
                    updated_at=now,
                    revision=1,
                )
            )
            ctx.add_event(
                "job.queued",
                {"job_type": "resync", "queue_position": position},
                work_id=work_id,
                job_id=job_id,
            )
            return {"job_id": job_id, "status": "queued", "range": estimate["range"]}

        result = await self.uow.write(write)
        if result["status"] == "queued":
            self.runtime.spawn(self.run(result["job_id"]))
        return result

    async def run(self, job_id: str):
        executor = getattr(self.runtime, "resync_executor", None)
        async with self.uow.read_sessions() as session:
            job = await session.get(Job, job_id)
            if job is None:
                return
            payload = json.loads(job.input_json)
            work_id = job.work_id
            resume_after = (
                int(job.stage.split(":", 1)[1])
                if job.stage and job.stage.startswith("resettle:")
                else payload["from_chapter"] - 1
            )
        await self.locks.wait_and_acquire(work_id, job_id)
        try:
            if executor is None:
                raise RuntimeError("Resettle executor chưa được đăng ký")

            async def start(ctx):
                job = await ctx.session.get(Job, job_id)
                job.status, job.started_at, job.updated_at = "running", utcnow_iso(), utcnow_iso()
                job.attempt += 1

            await self.uow.write(start)
            for chapter_no in range(
                max(payload["from_chapter"], resume_after + 1), payload["to_chapter"] + 1
            ):
                async with self.uow.read_sessions() as session:
                    chapter = await session.scalar(
                        select(Chapter).where(
                            Chapter.work_id == work_id,
                            Chapter.chapter_no == chapter_no,
                            Chapter.deleted_at.is_(None),
                        )
                    )
                    revision = await session.get(ChapterRevision, chapter.current_revision_id)
                    paragraphs = json.loads(revision.paragraphs_json)
                    handoff = await session.scalar(
                        select(ChapterHandoff).where(
                            ChapterHandoff.work_id == work_id,
                            ChapterHandoff.chapter_no == chapter_no - 1,
                            ChapterHandoff.is_current.is_(True),
                        )
                    )
                    state = await session.scalar(
                        select(StoryStateRow).where(
                            StoryStateRow.work_id == work_id,
                            StoryStateRow.chapter_no == chapter_no - 1,
                            StoryStateRow.is_current.is_(True),
                        )
                    )
                    if state is None:
                        raise AppError(ErrorCode.STATE_SNAPSHOT_MISSING)
                result = await executor.resettle(
                    {
                        "work_id": work_id,
                        "chapter_no": chapter_no,
                        "paragraphs": paragraphs,
                        "state": json.loads(state.state_json),
                        "handoff": json.loads(handoff.ending_state) if handoff else {},
                    }
                )
                value = result.model_dump(mode="json") if hasattr(result, "model_dump") else result

                async def commit(
                    ctx,
                    *,
                    _value=value,
                    _paragraphs=paragraphs,
                    _revision=revision,
                    _chapter_no=chapter_no,
                ):
                    from writestory_ai.contracts.state import StateDelta

                    delta = StateDelta.model_validate(_value["delta"])
                    await MemoryService(self.runtime).apply_in_context(
                        ctx, delta, paragraphs=_paragraphs, revision_id=_revision.id
                    )
                    prev = await ctx.session.scalar(
                        select(ChapterHandoff).where(
                            ChapterHandoff.work_id == work_id,
                            ChapterHandoff.chapter_no == _chapter_no,
                            ChapterHandoff.is_current.is_(True),
                        )
                    )
                    if prev:
                        prev.is_current, prev.superseded_at = False, utcnow_iso()
                    ctx.session.add(
                        ChapterHandoff(
                            id=new_id(),
                            work_id=work_id,
                            chapter_no=_chapter_no,
                            revision_id=_revision.id,
                            handoff_revision=(prev.handoff_revision + 1 if prev else 1),
                            ending_state=json.dumps(
                                _value.get("ending_state", {}), ensure_ascii=False
                            ),
                            tail_text="\n\n".join(x.get("text", "") for x in _paragraphs)[-4000:],
                            tail_paragraph_ids=json.dumps([x.get("id") for x in _paragraphs[-12:]]),
                            tail_tokens=0,
                            open_threads="[]",
                            next_opening_requirements="[]",
                            source="pipeline",
                            is_current=True,
                            created_at=utcnow_iso(),
                        )
                    )
                    job = await ctx.session.get(Job, job_id)
                    job.stage = f"resettle:{_chapter_no}"
                    job.checkpoint_json = json.dumps({"last_completed_chapter": _chapter_no})
                    job.updated_at = utcnow_iso()

                await self.uow.write(commit)

            async def finish(ctx):
                job = await ctx.session.get(Job, job_id)
                work = await ctx.session.get(Work, work_id)
                clear_continuity(work)
                job.status, job.finished_at, job.updated_at = (
                    "succeeded",
                    utcnow_iso(),
                    utcnow_iso(),
                )
                ctx.add_event(
                    "work.continuity", {"status": "ok", "chapter_no": None}, work_id=work_id
                )

            await self.uow.write(finish)
        except Exception as exc:
            failure_reason = str(exc)[:200]

            async def fail(ctx):
                job = await ctx.session.get(Job, job_id)
                work = await ctx.session.get(Work, work_id)
                chapter_no = (
                    int(job.stage.split(":")[-1]) + 1
                    if job.stage and ":" in job.stage
                    else payload["from_chapter"]
                )
                mark_blocked(work, chapter_no, failure_reason)
                job.status, job.wait_reason = "waiting_user", "blocked_needs_resync"
                job.finished_at = job.updated_at = utcnow_iso()
                ctx.add_event(
                    "work.continuity",
                    {
                        "status": work.continuity_status,
                        "chapter_no": work.continuity_chapter_no,
                        "reason": json.loads(work.continuity_reason),
                    },
                    work_id=work_id,
                    job_id=job_id,
                )

            await self.uow.write(fail)
        finally:
            await self.locks.release(work_id, job_id)
