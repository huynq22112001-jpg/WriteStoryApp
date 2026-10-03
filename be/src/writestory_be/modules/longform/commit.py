from __future__ import annotations

import json

from sqlalchemy import select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_generation import (
    ChapterCandidate,
    ChapterHandoff,
    ChapterMeasurement,
)
from writestory_be.infrastructure.db.models.longform_state import Summary
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.modules.chapters.service import ChapterService
from writestory_be.modules.memory.service import MemoryService


async def commit_chapter(uow, *, job_id: str, candidate_id: str):
    async def write(ctx):
        session = ctx.session
        job = await session.get(Job, job_id)
        candidate = await session.get(ChapterCandidate, candidate_id)
        if not job or not candidate:
            raise AppError(ErrorCode.NOT_FOUND)
        chapter = await session.get(Chapter, candidate.chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        if chapter.status == "committed" and candidate.status == "accepted":
            return {"revision_id": chapter.current_revision_id, "idempotent": True}
        if chapter.current_revision_id != candidate.base_revision_id:
            raise AppError(
                ErrorCode.REVISION_CONFLICT,
                detail={
                    "current_revision_id": chapter.current_revision_id,
                    "candidate_base_revision_id": candidate.base_revision_id,
                },
            )
        proposed = json.loads(candidate.proposed_delta or "null")
        if proposed is None:
            raise AppError(ErrorCode.WORK_BLOCKED, detail={"reason": "STATE_INVALID"})
        paragraphs = json.loads(candidate.paragraphs_json)
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"paragraph_id": p["paragraph_id"]},
                    "content": [{"type": "text", "text": p.get("text", "")}]
                    if p.get("text")
                    else [],
                }
                for p in paragraphs
            ],
        }
        revision = await ChapterService.__new__(ChapterService)._make_revision(
            session, chapter, doc, source="agent", reason="pipeline_commit"
        )
        from writestory_ai.contracts.state import StateDelta

        delta = StateDelta.model_validate(proposed)
        paragraph_text = {
            paragraph.get("paragraph_id", paragraph.get("id")): paragraph.get("text", "")
            for paragraph in paragraphs
        }
        await MemoryService.__new__(MemoryService).apply_in_context(
            ctx, delta, paragraphs=paragraph_text, revision_id=revision.id
        )
        handoff = await session.scalar(
            select(ChapterHandoff).where(
                ChapterHandoff.work_id == job.work_id,
                ChapterHandoff.chapter_no == candidate.chapter_no,
                ChapterHandoff.is_current.is_(True),
            )
        )
        if handoff:
            handoff.is_current = False
            handoff.superseded_at = utcnow_iso()
        ending = json.loads(candidate.ending_state or "{}")
        session.add(
            ChapterHandoff(
                id=new_id(),
                work_id=job.work_id,
                chapter_no=candidate.chapter_no,
                revision_id=revision.id,
                handoff_revision=(handoff.handoff_revision + 1 if handoff else 1),
                ending_state=json.dumps(ending, ensure_ascii=False),
                tail_text=candidate.plain_text[-4000:],
                tail_paragraph_ids=json.dumps([p["paragraph_id"] for p in paragraphs[-12:]]),
                tail_tokens=0,
                open_threads="[]",
                next_opening_requirements="[]",
                source="pipeline",
                is_current=True,
                created_at=utcnow_iso(),
            )
        )
        if candidate.summary_json:
            summary = json.loads(candidate.summary_json)
            if isinstance(summary, dict):
                session.add(
                    Summary(
                        id=new_id(),
                        work_id=job.work_id,
                        level="chapter",
                        chapter_no=candidate.chapter_no,
                        text=summary.get("text", ""),
                        key_points=json.dumps(summary.get("key_points", []), ensure_ascii=False),
                        token_estimate=int(summary.get("token_estimate", 0)),
                        source_hash=revision.content_hash,
                        is_current=True,
                        stale=False,
                        job_id=job.id,
                        created_at=utcnow_iso(),
                    )
                )
        metrics = json.loads(candidate.check_summary or "{}")
        session.add(
            ChapterMeasurement(
                id=new_id(),
                work_id=job.work_id,
                chapter_id=chapter.id,
                chapter_no=chapter.chapter_no,
                revision_id=revision.id,
                candidate_id=candidate.id,
                metrics_json=json.dumps({**metrics, "state_applied": True}, ensure_ascii=False),
                created_at=utcnow_iso(),
            )
        )
        chapter.status = "committed"
        chapter.state_applied = True
        candidate.status = "accepted"
        candidate.accepted_revision_id = revision.id
        candidate.decided_at = utcnow_iso()
        job.status, job.finished_at, job.updated_at = "succeeded", utcnow_iso(), utcnow_iso()
        job.wait_reason = None
        ctx.add_event(
            "chapter.committed",
            {"chapter_id": chapter.id, "revision_id": revision.id, "source": "agent"},
            work_id=job.work_id,
            job_id=job.id,
            chapter_no=chapter.chapter_no,
        )
        return {"revision_id": revision.id, "idempotent": False}

    return await uow.write(write)
