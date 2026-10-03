from __future__ import annotations

import json

from sqlalchemy import select

from writestory_be.infrastructure.db.models.chapters import Chapter, ChapterRevision
from writestory_be.infrastructure.db.models.longform_state import StoryStateRow, Summary
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork


class DatabaseContextAdapter:
    """Read-only composer port. Each call closes its DB session before returning to AI."""

    def __init__(self, uow: UnitOfWork, job_id: str | None = None):
        self.uow = uow
        self.job_id = job_id

    async def get_context(self, work_id: str, chapter_no: int) -> dict:
        async def read(session):
            state = await session.scalar(
                select(StoryStateRow)
                .where(
                    StoryStateRow.work_id == work_id,
                    StoryStateRow.chapter_no < chapter_no,
                    StoryStateRow.is_current.is_(True),
                )
                .order_by(StoryStateRow.chapter_no.desc())
                .limit(1)
            )
            summaries = list(
                (
                    await session.scalars(
                        select(Summary)
                        .where(
                            Summary.work_id == work_id,
                            Summary.is_current.is_(True),
                            Summary.stale.is_(False),
                            Summary.to_chapter.is_(None) | (Summary.to_chapter < chapter_no),
                        )
                        .order_by(Summary.created_at.desc())
                        .limit(20)
                    )
                ).all()
            )
            chapters = list(
                (
                    await session.scalars(
                        select(Chapter)
                        .where(
                            Chapter.work_id == work_id,
                            Chapter.chapter_no < chapter_no,
                            Chapter.deleted_at.is_(None),
                            Chapter.current_revision_id.is_not(None),
                        )
                        .order_by(Chapter.chapter_no.desc())
                        .limit(3)
                    )
                ).all()
            )
            recent = []
            for chapter in chapters:
                revision = await session.get(ChapterRevision, chapter.current_revision_id)
                if revision:
                    recent.append(
                        {
                            "chapter_no": chapter.chapter_no,
                            "paragraphs": json.loads(revision.paragraphs_json),
                        }
                    )
            return {
                "work_id": work_id,
                "chapter_no": chapter_no,
                "state": json.loads(state.state_json) if state else None,
                "summaries": [
                    {
                        "level": item.level,
                        "text": item.text,
                        "from_chapter": item.from_chapter,
                        "to_chapter": item.to_chapter,
                    }
                    for item in summaries
                ],
                "recent_chapters": list(reversed(recent)),
                "handoff": None,
                "pending_deltas": [],
            }

        return await self.uow.read(read)

    async def load_checkpoint(self, work_id: str, chapter_no: int, step: str) -> dict:
        from writestory_be.infrastructure.db.models.system import Job, JobStep

        async def read(session):
            query = (
                select(JobStep)
                .join(Job, Job.id == JobStep.job_id)
                .where(
                    Job.work_id == work_id,
                    JobStep.step == step,
                    JobStep.status == "succeeded",
                )
            )
            if self.job_id:
                query = query.where(JobStep.job_id == self.job_id)
            row = await session.scalar(query.order_by(JobStep.finished_at.desc()).limit(1))
            return json.loads(row.checkpoint_json or "{}") if row else {}

        return await self.uow.read(read)
