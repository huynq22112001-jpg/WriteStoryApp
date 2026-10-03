from __future__ import annotations

import hashlib
import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.longform_generation import ChapterCandidate
from writestory_be.infrastructure.db.models.system import Job, JobStep


def _json(value):
    return jsonable_encoder(value, custom_encoder={})


class ProgressCheckpointAdapter:
    def __init__(self, runtime, job_id: str, candidate_id: str):
        self.runtime, self.job_id, self.candidate_id = runtime, job_id, candidate_id

    async def save(self, step: str, payload: dict):
        packed = _json(payload)
        encoded = json.dumps(packed, ensure_ascii=False)
        now = utcnow_iso()

        async def write(ctx):
            job = await ctx.session.get(Job, self.job_id)
            if job is None:
                return
            job.stage = step
            job.checkpoint_json = encoded
            job.updated_at = now
            query = (
                select(JobStep)
                .where(
                    JobStep.job_id == self.job_id,
                    JobStep.step == step,
                    JobStep.attempt == job.attempt + 1,
                )
                .limit(1)
            )
            row = await ctx.session.scalar(query)
            if row is None:
                ctx.session.add(
                    JobStep(
                        id=new_id(),
                        job_id=self.job_id,
                        step=step,
                        attempt=job.attempt,
                        round=0,
                        status="succeeded",
                        checkpoint_json=encoded,
                        output_hash=hashlib.sha256(encoded.encode()).hexdigest(),
                        started_at=now,
                        finished_at=now,
                    )
                )
            else:
                row.status, row.checkpoint_json, row.finished_at = "succeeded", encoded, now
            candidate = await ctx.session.get(ChapterCandidate, self.candidate_id)
            if candidate and step == "write":
                result = packed.get("write") if isinstance(packed, dict) else None
                if isinstance(result, dict):
                    draft = result.get("candidate") or result
                    paragraphs = draft.get("paragraphs", []) if isinstance(draft, dict) else []
                    candidate.paragraphs_json = json.dumps(paragraphs, ensure_ascii=False)
                    candidate.plain_text = "\n\n".join(p.get("text", "") for p in paragraphs)
                    candidate.content_json = json.dumps(
                        {"paragraphs": paragraphs}, ensure_ascii=False
                    )
                    candidate.status = "partial"

        await self.runtime.ensure_database_services().write(write)

    async def on_step(self, progress):
        payload = {
            "step": progress.step,
            "attempt": 1,
            "round": progress.round,
            "max_rounds": progress.max_rounds,
            "progress": progress.progress,
        }
        self.runtime.event_bus.publish("job.step", payload, job_id=self.job_id)

    async def on_token(self, token):
        self.runtime.event_bus.publish(
            "token.delta",
            {
                "candidate_id": self.candidate_id,
                "step": token.step,
                "mode": "full",
                "offset": token.offset,
                "text": token.text,
            },
            job_id=self.job_id,
        )

    async def load_checkpoint(self, work_id: str, chapter_no: int, step: str):
        from writestory_be.infrastructure.db.models.system import JobStep

        async def read(session):
            row = await session.scalar(
                select(JobStep)
                .where(
                    JobStep.job_id == self.job_id,
                    JobStep.step == step,
                    JobStep.status == "succeeded",
                )
                .order_by(JobStep.attempt.desc(), JobStep.finished_at.desc())
                .limit(1)
            )
            return json.loads(row.checkpoint_json or "{}") if row else {}

        return await self.runtime.ensure_database_services().read(read)
