from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from writestory_be.infrastructure.db.models.system import Job


class JobSummaryPort(Protocol):
    async def summaries(
        self, session: AsyncSession, work_ids: list[str]
    ) -> dict[str, dict[str, Any]]: ...


class EmptyJobSummaryPort:
    async def summaries(
        self, session: AsyncSession, work_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        return {}


class DatabaseJobSummaryPort:
    async def summaries(
        self, session: AsyncSession, work_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        if not work_ids:
            return {}
        jobs = list(
            (
                await session.scalars(
                    select(Job)
                    .where(Job.work_id.in_(work_ids))
                    .order_by(Job.created_at.desc(), Job.id.desc())
                )
            ).all()
        )
        output: dict[str, dict[str, Any]] = {}
        for job in jobs:
            if job.work_id in output:
                continue
            output[job.work_id] = {
                "state": job.status,
                "waiting_reason": job.wait_reason,
                "queue_position": job.queue_position,
                "chapter_no": None,
                "step": job.stage,
            }
        return output
