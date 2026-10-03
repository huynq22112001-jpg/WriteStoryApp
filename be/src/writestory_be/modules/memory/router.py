from __future__ import annotations

import json
import re

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.fts import search as fts_search
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_state import (
    ContextTrace,
    StoryStateRow,
    Summary,
)
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.modules.memory.service import MemoryService

router = APIRouter(tags=["memory"])
KINDS_QUERY = Query(default=None)
SEARCH_LIMIT_QUERY = Query(default=20, ge=1, le=100)


class SummaryUpdate(BaseModel):
    expected_source_hash: str
    text: str = Field(min_length=1, max_length=100_000)
    pinned_by_user: bool


def _summary_out(row: Summary):
    return {
        "id": row.id,
        "work_id": row.work_id,
        "level": row.level,
        "chapter_no": row.chapter_no,
        "arc_key": row.arc_key,
        "from_chapter": row.from_chapter,
        "to_chapter": row.to_chapter,
        "text": row.text,
        "key_points": json.loads(row.key_points),
        "source_hash": row.source_hash,
        "stale": row.stale,
        "pinned_by_user": row.pinned_by_user,
        "created_at": row.created_at,
    }


@router.get("/v1/works/{work_id}/state", name="get_work_state")
async def get_work_state(
    work_id: str, runtime: RuntimeDep, chapter: int | None = Query(default=None, ge=0)
):
    async def read(session):
        query = select(StoryStateRow).where(
            StoryStateRow.work_id == work_id, StoryStateRow.is_current.is_(True)
        )
        if chapter is not None:
            query = query.where(StoryStateRow.chapter_no <= chapter)
        row = await session.scalar(query.order_by(StoryStateRow.chapter_no.desc()).limit(1))
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        latest = await session.scalar(
            select(StoryStateRow.chapter_no)
            .where(StoryStateRow.work_id == work_id, StoryStateRow.is_current.is_(True))
            .order_by(StoryStateRow.chapter_no.desc())
            .limit(1)
        )
        return {
            "meta": {
                "state_id": row.id,
                "chapter_no": row.chapter_no,
                "source": row.source,
                "state_hash": row.state_hash,
                "revision_id": row.revision_id,
                "is_latest": row.chapter_no == latest,
                "created_at": row.created_at,
            },
            "state": json.loads(row.state_json),
        }

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/works/{work_id}/state/changes", name="get_work_state_changes")
async def get_state_changes(
    work_id: str,
    runtime: RuntimeDep,
    from_chapter: int = Query(alias="from", ge=0),
    to_chapter: int = Query(alias="to", ge=0),
    entity: str | None = None,
):
    if to_chapter < from_chapter:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "to"})

    async def read(session):
        rows = (
            await session.scalars(
                select(StoryStateRow)
                .where(
                    StoryStateRow.work_id == work_id,
                    StoryStateRow.chapter_no >= from_chapter,
                    StoryStateRow.chapter_no <= to_chapter,
                    StoryStateRow.is_current.is_(True),
                )
                .order_by(StoryStateRow.chapter_no)
            )
        ).all()
        changes = []
        for row in rows:
            delta = json.loads(row.delta_json)
            for op in delta.get("ops", []):
                kind = op.get("op", "")
                target = next(
                    (
                        op[key]
                        for key in ("character_id", "fact_id", "hook_id", "story_event_id")
                        if key in op
                    ),
                    None,
                )
                if entity and entity not in (target, f"{kind.split('.')[0]}:{target}"):
                    continue
                changes.append(
                    {
                        "chapter_no": row.chapter_no,
                        "op": kind,
                        "target": target,
                        "before": None,
                        "after": op,
                        "evidence": op.get("evidence"),
                    }
                )
        return changes

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/works/{work_id}/summaries", name="list_work_summaries")
async def list_summaries(
    work_id: str,
    runtime: RuntimeDep,
    level: str | None = None,
    from_chapter: int | None = Query(default=None, alias="from", ge=0),
    to_chapter: int | None = Query(default=None, alias="to", ge=0),
):
    async def read(session):
        query = select(Summary).where(Summary.work_id == work_id, Summary.is_current.is_(True))
        if level:
            query = query.where(Summary.level == level)
        if from_chapter is not None:
            query = query.where(Summary.to_chapter >= from_chapter)
        if to_chapter is not None:
            query = query.where(Summary.from_chapter <= to_chapter)
        rows = (await session.scalars(query.order_by(Summary.created_at))).all()
        return [_summary_out(row) for row in rows]

    return await runtime.ensure_database_services().read(read)


@router.put("/v1/summaries/{summary_id}", name="update_summary")
async def update_summary(summary_id: str, body: SummaryUpdate, runtime: RuntimeDep):
    async def write(ctx):
        row = await ctx.session.get(Summary, summary_id)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        if row.source_hash != body.expected_source_hash:
            raise AppError(
                ErrorCode.REVISION_CONFLICT, detail={"current_source_hash": row.source_hash}
            )
        row.text = body.text
        row.pinned_by_user = body.pinned_by_user
        await ctx.session.flush()
        return _summary_out(row)

    return await runtime.ensure_database_services().write(write)


@router.get("/v1/chapters/{chapter_id}/memory", name="get_chapter_memory")
async def chapter_memory(chapter_id: str, runtime: RuntimeDep):
    async def read(session):
        chapter = await session.get(Chapter, chapter_id)
        if chapter is None or chapter.deleted_at:
            raise AppError(ErrorCode.NOT_FOUND)
        state_row = await session.scalar(
            select(StoryStateRow).where(
                StoryStateRow.work_id == chapter.work_id,
                StoryStateRow.chapter_no == chapter.chapter_no,
                StoryStateRow.is_current.is_(True),
            )
        )
        state = json.loads(state_row.state_json) if state_row else {}
        facts = state.get("facts", [])
        hooks = state.get("hooks", [])
        return {
            "facts_active": [
                item
                for item in facts
                if item.get("valid_until") is None or item["valid_until"] >= chapter.chapter_no
            ],
            "hooks_due": [
                item
                for item in hooks
                if item.get("due_by") is not None
                and item["due_by"] <= chapter.chapter_no
                and item.get("status") not in {"resolved", "superseded"}
            ],
            "hooks_open": [
                item for item in hooks if item.get("status") not in {"resolved", "superseded"}
            ],
            "changes_in_chapter": json.loads(state_row.delta_json).get("ops", [])
            if state_row
            else [],
            "present_characters": [
                item for item in state.get("characters", []) if item.get("in_last_scene")
            ],
        }

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/chapters/{chapter_id}/trace", name="get_chapter_trace")
async def chapter_trace(
    chapter_id: str, runtime: RuntimeDep, job_id: str | None = None, step: str | None = None
):
    async def read(session):
        chapter = await session.get(Chapter, chapter_id)
        if chapter is None:
            raise AppError(ErrorCode.NOT_FOUND)
        query = select(ContextTrace).where(
            ContextTrace.work_id == chapter.work_id,
            ContextTrace.chapter_no == chapter.chapter_no,
        )
        if job_id:
            query = query.where(ContextTrace.job_id == job_id)
        if step:
            query = query.where(ContextTrace.step == step)
        rows = (await session.scalars(query.order_by(ContextTrace.created_at))).all()
        return {
            "traces": [
                {
                    "id": row.id,
                    "step": row.step,
                    "round": row.round,
                    "model_id": row.model_id,
                    "effort": row.effort,
                    "prompt_versions": json.loads(row.prompt_versions),
                    "items": json.loads(row.items),
                    "notes": json.loads(row.notes),
                    "compacted": row.compacted,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        }

    return await runtime.ensure_database_services().read(read)


@router.get("/v1/works/{work_id}/search", name="search_work_memory")
async def search_work(
    work_id: str,
    runtime: RuntimeDep,
    q: str = Query(min_length=1, max_length=200),
    kinds: list[str] | None = KINDS_QUERY,
    limit: int = SEARCH_LIMIT_QUERY,
    chapter_from: int | None = None,
    chapter_to: int | None = None,
    cursor: str | None = None,
):
    del cursor
    allowed = {"chapter", "fact", "hook", "summary", "character", "location"}
    if kinds and set(kinds) - allowed:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "kinds"})

    async def read(session):
        work = await session.get(Work, work_id)
        if work is None:
            raise AppError(ErrorCode.NOT_FOUND)
        rows = await fts_search(session, q, work_id=work_id, limit=limit * 3)
        items = []
        terms = [word.casefold() for word in re.findall(r"[^\W_]+", q, flags=re.UNICODE)]
        for row in rows:
            kind = "chapter" if row["source_type"] == "chapter_paragraph" else row["source_type"]
            if kinds and kind not in kinds:
                continue
            chapter_no = row["chapter_no"]
            if chapter_from is not None and (chapter_no is None or chapter_no < chapter_from):
                continue
            if chapter_to is not None and (chapter_no is None or chapter_no > chapter_to):
                continue
            body = row["body"]
            highlights = []
            folded = body.casefold()
            for term in terms:
                start = folded.find(term)
                if start >= 0:
                    highlights.append([start, start + len(term)])
            items.append(
                {
                    "kind": kind,
                    "source_id": row["source_id"],
                    "chapter_no": chapter_no,
                    "paragraph_id": row["paragraph_id"],
                    "revision_id": row["source_revision_id"],
                    "title": row["title"],
                    "snippet": {"text": body[:500], "highlights": highlights},
                    "score": row["score"],
                    "matched_via": "fts",
                }
            )
            if len(items) >= limit:
                break
        return {"items": items, "next_cursor": None}

    return await runtime.ensure_database_services().read(read)


@router.post("/v1/works/{work_id}/state/deltas", name="apply_state_delta")
async def apply_state_delta(work_id: str, body: dict, runtime: RuntimeDep):
    from writestory_ai.contracts.state import StateDelta

    try:
        delta = StateDelta.model_validate({**body, "work_id": work_id})
    except Exception as exc:
        raise AppError(ErrorCode.VALIDATION, detail={"reason": "invalid_state_delta"}) from exc
    return await MemoryService(runtime).apply_delta(delta)
