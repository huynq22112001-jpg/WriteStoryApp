from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.models.chapters import Chapter, ChapterWorkingCopy
from writestory_be.infrastructure.db.models.longform_state import StoryStateRow
from writestory_be.infrastructure.db.models.works import Work


@dataclass(frozen=True)
class GateResult:
    chapter: Chapter
    previous_state: StoryStateRow | None


async def entry_gate(session, work_id: str, chapter_no: int) -> GateResult:
    work = await session.get(Work, work_id)
    if work is None or work.deleted_at:
        raise AppError(ErrorCode.NOT_FOUND)
    if work.continuity_status != "ok":
        raise AppError(
            ErrorCode.WORK_BLOCKED,
            detail={"status": work.continuity_status, "chapter_no": work.continuity_chapter_no},
        )
    committed = (
        await session.scalars(
            select(Chapter)
            .where(
                Chapter.work_id == work_id,
                Chapter.deleted_at.is_(None),
                Chapter.status == "committed",
            )
            .order_by(Chapter.chapter_no)
        )
    ).all()
    next_no = 1
    for row in committed:
        if row.chapter_no != next_no:
            break
        next_no += 1
    if chapter_no != next_no:
        raise AppError(
            ErrorCode.CHAPTER_RANGE_CONFLICT,
            detail={"expected_chapter_no": next_no, "chapter_no": chapter_no},
        )
    previous = None
    if chapter_no > 1:
        prior = await session.scalar(
            select(Chapter).where(
                Chapter.work_id == work_id,
                Chapter.chapter_no == chapter_no - 1,
                Chapter.deleted_at.is_(None),
            )
        )
        if prior is None or prior.status != "committed" or not prior.state_applied:
            raise AppError(ErrorCode.WORK_BLOCKED, detail={"reason": "PREV_CHAPTER_DIRTY"})
        wc = await session.get(ChapterWorkingCopy, prior.id)
        if wc and wc.has_changes:
            raise AppError(ErrorCode.WORK_BLOCKED, detail={"reason": "PREV_CHAPTER_DIRTY"})
        previous = await session.scalar(
            select(StoryStateRow).where(
                StoryStateRow.work_id == work_id,
                StoryStateRow.chapter_no == chapter_no - 1,
                StoryStateRow.is_current.is_(True),
            )
        )
        if previous is None:
            raise AppError(ErrorCode.WORK_BLOCKED, detail={"reason": "STATE_SNAPSHOT_MISSING"})
    chapter = await session.scalar(
        select(Chapter).where(
            Chapter.work_id == work_id,
            Chapter.chapter_no == chapter_no,
            Chapter.deleted_at.is_(None),
        )
    )
    if chapter is None:
        raise AppError(ErrorCode.NOT_FOUND)
    return GateResult(chapter, previous)
