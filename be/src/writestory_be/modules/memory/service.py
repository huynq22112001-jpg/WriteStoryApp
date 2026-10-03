from __future__ import annotations

import json

from sqlalchemy import select

from writestory_ai.contracts.state import StateDelta, StoryState
from writestory_ai.state.apply import apply_delta
from writestory_ai.state.validate import validate_delta
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.fts import upsert_document
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_state import (
    Fact,
    Hook,
    StatePendingDelta,
    StoryEvent,
    StoryStateRow,
    TimelineEntry,
)
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.infrastructure.db.unit_of_work import WriteContext


def _load_state(row: StoryStateRow) -> StoryState:
    return StoryState.model_validate_json(row.state_json)


class MemoryService:
    def __init__(self, runtime):
        self.uow = runtime.ensure_database_services()

    async def apply_delta(self, delta: StateDelta, *, paragraphs=None, revision_id=None):
        async def write(ctx: WriteContext):
            return await self.apply_in_context(
                ctx, delta, paragraphs=paragraphs, revision_id=revision_id
            )

        return await self.uow.write(write)

    async def apply_in_context(
        self, ctx: WriteContext, delta: StateDelta, *, paragraphs=None, revision_id=None
    ):
        session = ctx.session
        work = await session.get(Work, delta.work_id)
        if work is None or work.deleted_at:
            raise AppError(ErrorCode.NOT_FOUND)
        base_row = await session.scalar(
            select(StoryStateRow).where(
                StoryStateRow.work_id == delta.work_id,
                StoryStateRow.chapter_no == delta.base_state_chapter,
                StoryStateRow.is_current.is_(True),
            )
        )
        if base_row is None:
            raise AppError(ErrorCode.VALIDATION, detail={"reason": "state_snapshot_missing"})
        base = _load_state(base_row)

        active_job = await session.scalar(
            select(Job.id)
            .where(
                Job.work_id == delta.work_id,
                Job.type.in_(("write", "revise", "resync")),
                Job.status.in_(("queued", "waiting_slot", "running")),
            )
            .limit(1)
        )
        if delta.source == "user" and active_job:
            pending = StatePendingDelta(
                id=new_id(),
                work_id=delta.work_id,
                base_chapter_no=delta.base_state_chapter,
                ops=json.dumps(
                    [op.model_dump(mode="json") for op in delta.ops], ensure_ascii=False
                ),
                note=None,
                status="pending",
                created_at=utcnow_iso(),
            )
            session.add(pending)
            return {"pending_delta_id": pending.id}

        validation = validate_delta(base, delta, paragraphs)
        if not validation.valid:
            raise AppError(
                ErrorCode.VALIDATION,
                detail={"validation_errors": [issue.model_dump() for issue in validation.errors]},
            )
        try:
            updated, digest = apply_delta(base, delta)
        except (ValueError, KeyError, StopIteration) as exc:
            raise AppError(ErrorCode.VALIDATION, detail={"reason": "delta_apply_failed"}) from exc

        old_current = await session.scalar(
            select(StoryStateRow).where(
                StoryStateRow.work_id == delta.work_id,
                StoryStateRow.chapter_no == delta.chapter_no,
                StoryStateRow.is_current.is_(True),
            )
        )
        if old_current:
            old_current.is_current = False
            await session.flush()
        state_id = new_id()
        row = StoryStateRow(
            id=state_id,
            work_id=delta.work_id,
            chapter_no=updated.chapter_no,
            revision_id=revision_id,
            schema_version=updated.schema_version,
            state_json=updated.model_dump_json(),
            state_hash=digest,
            delta_json=delta.model_dump_json(),
            parent_state_id=base_row.id,
            source={"pipeline": "pipeline", "user": "user_edit"}[delta.source],
            is_current=True,
            job_id=None,
            created_at=utcnow_iso(),
        )
        session.add(row)
        await self._project_ledger(ctx, work.id, state_id, updated, delta)
        chapter = await session.scalar(
            select(Chapter).where(
                Chapter.work_id == delta.work_id,
                Chapter.chapter_no == delta.chapter_no,
                Chapter.deleted_at.is_(None),
            )
        )
        if chapter:
            chapter.state_id = state_id
            chapter.state_applied = True
        latest = await session.scalar(
            select(StoryStateRow.chapter_no)
            .where(StoryStateRow.work_id == delta.work_id, StoryStateRow.is_current.is_(True))
            .order_by(StoryStateRow.chapter_no.desc())
            .limit(1)
        )
        if delta.source == "user" and latest is not None and delta.chapter_no < latest:
            stale_from = delta.chapter_no + 1
            if work.continuity_status != "stale_from" or work.continuity_chapter_no is None:
                work.continuity_status, work.continuity_chapter_no = "stale_from", stale_from
            else:
                work.continuity_chapter_no = min(work.continuity_chapter_no, stale_from)
        return {"state_id": state_id, "state_hash": digest, "findings": []}

    @staticmethod
    async def _project_ledger(
        ctx: WriteContext, work_id: str, state_id: str, state: StoryState, delta: StateDelta
    ):
        session = ctx.session
        for fact in state.facts:
            values = dict(
                work_id=work_id,
                subject=fact.subject,
                predicate=fact.predicate,
                object=fact.object,
                valid_from_chapter=fact.valid_from,
                valid_until_chapter=fact.valid_until,
                source_chapter=fact.valid_from,
                evidence=json.dumps(fact.evidence.model_dump(mode="json"), ensure_ascii=False),
                source=delta.source,
                is_secret=fact.is_secret,
                status="closed" if fact.valid_until is not None else "active",
                created_state_id=state_id,
                closed_state_id=state_id if fact.valid_until is not None else None,
            )
            existing = await session.get(Fact, fact.id)
            if existing is None:
                session.add(Fact(id=fact.id, **values))
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
            await upsert_document(
                ctx,
                source_type="fact",
                source_id=fact.id,
                body=f"{fact.subject} {fact.predicate} {fact.object}",
                title=fact.subject,
                work_id=work_id,
                chapter_no=fact.valid_from,
            )
        for hook in state.hooks:
            existing = await session.get(Hook, hook.id)
            history = json.loads(existing.history) if existing else []
            if (
                not existing
                or existing.status != hook.status
                or existing.due_by_chapter != hook.due_by
            ):
                history.append({"chapter_no": delta.chapter_no, "op": hook.status})
            values = dict(
                work_id=work_id,
                title=hook.title,
                status=hook.status,
                opened_at_chapter=hook.opened_at,
                due_by_chapter=hook.due_by,
                payoff_plan=hook.payoff_plan,
                priority=hook.priority,
                last_advanced_chapter=hook.last_advanced,
                resolved_at_chapter=delta.chapter_no
                if hook.status in {"resolved", "superseded"}
                else None,
                source=delta.source,
                history=json.dumps(history, ensure_ascii=False),
            )
            if existing is None:
                session.add(Hook(id=hook.id, **values))
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
            await upsert_document(
                ctx,
                source_type="hook",
                source_id=hook.id,
                body=f"{hook.title} {hook.payoff_plan}",
                title=hook.title,
                work_id=work_id,
                chapter_no=hook.opened_at,
            )
        for event in state.events:
            existing = await session.get(StoryEvent, event.story_event_id)
            values = dict(
                work_id=work_id,
                summary=event.story_event_id,
                planned_chapter=event.planned_chapter,
                status=event.status,
                done_in_chapter=event.done_chapter,
                depends_on=json.dumps(event.depends_on),
                source=delta.source,
            )
            if existing is None:
                session.add(StoryEvent(id=event.story_event_id, **values))
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
        session.add(
            TimelineEntry(
                id=new_id(),
                work_id=work_id,
                chapter_no=delta.chapter_no,
                story_time_label=state.story_time.label,
                story_time_order=state.story_time.ordinal,
                description="Cập nhật mốc thời gian truyện",
                source=delta.source,
                evidence="[]",
            )
        )
