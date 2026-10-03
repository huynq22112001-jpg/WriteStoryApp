from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.ai.model_resolver import ModelResolver
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.models.works import Work


class WriteJobRequest(BaseModel):
    chapter_no: int = Field(ge=1)
    mode: str = "review_each"
    idempotency_key: str = Field(min_length=8, max_length=200)
    instruction: str | None = None


class WriteJobService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()

    async def enqueue(self, work_id: str, body: WriteJobRequest):
        if body.mode not in {"auto", "review_each", "review_every_k"}:
            raise AppError(ErrorCode.VALIDATION, detail={"field": "mode"})
        resolver = ModelResolver(self.runtime)
        pinned = {
            role: await resolver.resolve(work_id, role)
            for role in ("planner", "writer", "checker", "reviewer", "summary")
        }
        now, job_id = utcnow_iso(), new_id()

        async def write(ctx):
            existing = await ctx.session.scalar(
                select(Job).where(Job.idempotency_key == body.idempotency_key)
            )
            if existing:
                if (
                    existing.work_id != work_id
                    or json.loads(existing.input_json).get("chapter_no") != body.chapter_no
                ):
                    raise AppError(ErrorCode.IDEMPOTENCY_CONFLICT)
                return {
                    "job_id": existing.id,
                    "status": existing.status,
                    "queue_position": existing.queue_position,
                }
            work = await ctx.session.get(Work, work_id)
            if work is None or work.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            from writestory_be.modules.longform.gate import entry_gate

            gate = await entry_gate(ctx.session, work_id, body.chapter_no)
            chapter = gate.chapter
            position = (
                int(
                    await ctx.session.scalar(
                        select(func.max(Job.queue_position)).where(
                            Job.work_id == work_id,
                            Job.status.in_(("queued", "waiting_slot")),
                        )
                    )
                    or 0
                )
                + 1
            )
            input_value = {
                "chapter_no": body.chapter_no,
                "chapter_id": chapter.id,
                "mode": body.mode,
                "instruction": body.instruction,
                "pinned": pinned,
                "settings": {
                    "length_min": work.chapter_length_min,
                    "length_max": work.chapter_length_max,
                    "max_repair_rounds": work.max_repair_rounds or 2,
                },
            }
            ctx.session.add(
                Job(
                    id=job_id,
                    idempotency_key=body.idempotency_key,
                    type="write",
                    work_id=work_id,
                    status="queued",
                    priority=0,
                    queue_position=position,
                    input_json=json.dumps(input_value, ensure_ascii=False),
                    base_revision_id=chapter.current_revision_id,
                    attempt=0,
                    created_at=now,
                    updated_at=now,
                    revision=1,
                )
            )
            chapter.status = "drafting"
            ctx.add_event(
                "job.queued",
                {"job_type": "write", "priority": 0, "queue_position": position},
                work_id=work_id,
                job_id=job_id,
                chapter_no=body.chapter_no,
            )
            return {"job_id": job_id, "status": "queued", "queue_position": position}

        result = await self.uow.write(write)
        if result["status"] == "queued":
            from writestory_be.jobs.handlers.chapter_write import ChapterWriteRunner

            runner = getattr(self.runtime, "chapter_write_runner", None)
            if runner is None:
                runner = ChapterWriteRunner(self.runtime)
                self.runtime.chapter_write_runner = runner
            self.runtime.spawn(runner.run(result["job_id"]))
        return result
