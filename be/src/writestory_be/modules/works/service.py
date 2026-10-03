from __future__ import annotations

import base64
import json
from importlib.resources import files
from types import SimpleNamespace
from typing import Any, Literal

from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, bindparam, func, inspect, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from writestory_be.api.idempotency import IdempotencyService
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.core.text_fold import fold_text
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.models.works import StyleProfile, Work
from writestory_be.infrastructure.db.unit_of_work import WriteContext
from writestory_be.modules.works.domain import (
    FoundationReadinessPort,
    compute_library_badge,
    validate_length_range,
    validate_ready_transition,
)
from writestory_be.modules.works.ports import DatabaseJobSummaryPort
from writestory_be.modules.works.repository import WorkRepository
from writestory_be.modules.works.schemas import (
    GenrePresetOut,
    StyleProfileIn,
    StyleProfileOut,
    WorkCreate,
    WorkListItem,
    WorkListResponse,
    WorkOut,
    WorkPatch,
    WorkStatus,
)

_ACTIVE_JOB_STATES = ("queued", "waiting_slot", "running", "waiting_user")
_WIZARD_STEPS = {
    "basics",
    "brief",
    "foundation",
    "address_rules",
    "event_outline",
    "writing_config",
    "review",
}


def load_genres() -> list[dict[str, Any]]:
    return json.loads(
        files("writestory_ai.languages.vi").joinpath("genres.json").read_text("utf-8")
    )


def _genre_map() -> dict[str, dict[str, Any]]:
    return {item["key"]: item for item in load_genres()}


def _decode_cursor(cursor: str | None, sort: str) -> tuple[str, str] | None:
    if not cursor:
        return None
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        if (
            value["sort"] != sort
            or not isinstance(value["value"], str)
            or not isinstance(value["id"], str)
        ):
            raise ValueError
        return value["value"], value["id"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "cursor"}) from exc


def _encode_cursor(sort: str, value: str, work_id: str) -> str:
    raw = json.dumps({"sort": sort, "value": value, "id": work_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _reason(value: str | None) -> dict[str, Any] | None:
    return json.loads(value) if value else None


def _json_list(value: str) -> list[str]:
    return json.loads(value or "[]")


def _style_out(profile: StyleProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "vocab_register": profile.vocab_register,
        "dialogue_style": profile.dialogue_style,
        "dialogue_dash_char": profile.dialogue_dash_char,
        "tone_mark_style": profile.tone_mark_style,
        "punctuation_rules": json.loads(profile.punctuation_rules),
        "banned_phrases": _json_list(profile.banned_phrases),
        "voice": profile.voice,
        "voice_samples": _json_list(profile.voice_samples),
        "revision": profile.revision,
    }


def _work_out(work: Work, profile: StyleProfile | None = None) -> WorkOut:
    return WorkOut(
        id=work.id,
        project_id=work.project_id,
        title=work.title,
        language=work.language,
        genre=work.genre,
        genre_label_custom=work.genre_label_custom,
        status=work.status,
        brief=work.brief,
        target_chapters=work.target_chapters,
        chapter_length_min=work.chapter_length_min,
        chapter_length_max=work.chapter_length_max,
        autowrite_mode_default=work.autowrite_mode_default,
        review_every_k=work.review_every_k,
        max_repair_rounds=work.max_repair_rounds,
        budget_daily_usd=work.budget_daily_usd,
        budget_daily_tokens=work.budget_daily_tokens,
        continuity_status=work.continuity_status,
        continuity_chapter_no=work.continuity_chapter_no,
        continuity_reason=_reason(work.continuity_reason),
        cover_asset_id=work.cover_asset_id,
        wizard_step=work.wizard_step,
        wizard_completed_steps=_json_list(work.wizard_completed_steps),
        last_opened_at=work.last_opened_at,
        revision=work.revision,
        created_at=work.created_at,
        updated_at=work.updated_at,
        style_profile=_style_out(profile),
    )


class WorkService:
    def __init__(self, runtime) -> None:
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()
        self.foundation = FoundationReadinessPort()
        self.job_summary_port = DatabaseJobSummaryPort()

    async def list_works(
        self,
        *,
        q: str | None,
        genre: str | None,
        status: WorkStatus | None,
        continuity: str | None,
        sort: Literal["updated", "opened", "title"],
        cursor: str | None,
        limit: int,
    ) -> WorkListResponse:
        cursor_key = _decode_cursor(cursor, sort)
        folded = fold_text(q.strip()) if q and q.strip() else None

        async def read(session: AsyncSession):
            query = select(Work).where(Work.deleted_at.is_(None))
            if folded:
                query = query.where(Work.title_search.contains(folded, autoescape=True))
            if genre:
                query = query.where(Work.genre == genre)
            if status:
                query = query.where(Work.status == status)
            if continuity:
                query = query.where(Work.continuity_status == continuity)

            if sort == "title":
                sort_col = Work.title_search
                query = query.order_by(sort_col.asc(), Work.id.asc())
            elif sort == "opened":
                sort_col = func.coalesce(Work.last_opened_at, Work.created_at)
                query = query.order_by(sort_col.desc(), Work.id.desc())
            else:
                sort_col = Work.updated_at
                query = query.order_by(sort_col.desc(), Work.id.desc())
            if cursor_key:
                value, work_id = cursor_key
                if sort == "title":
                    query = query.where(
                        or_(sort_col > value, and_(sort_col == value, Work.id > work_id))
                    )
                else:
                    query = query.where(
                        or_(sort_col < value, and_(sort_col == value, Work.id < work_id))
                    )
            works = list((await session.scalars(query.limit(limit + 1))).all())
            more = len(works) > limit
            works = works[:limit]
            jobs = await self.job_summary_port.summaries(session, [item.id for item in works])
            committed = await self._committed_counts(session, [item.id for item in works])
            presets = _genre_map()
            items = [
                WorkListItem(
                    id=work.id,
                    title=work.title,
                    genre=work.genre,
                    genre_label=(presets.get(work.genre or "") or {}).get("label")
                    or work.genre_label_custom,
                    status=work.status,
                    continuity_status=work.continuity_status,
                    continuity_chapter_no=work.continuity_chapter_no,
                    continuity_reason=_reason(work.continuity_reason),
                    committed_chapters=committed.get(work.id, 0),
                    target_chapters=work.target_chapters,
                    job=jobs.get(work.id),
                    badge=compute_library_badge(
                        continuity_status=work.continuity_status,
                        status=work.status,
                        wizard_step=work.wizard_step,
                        target_chapters=work.target_chapters,
                        committed_chapters=committed.get(work.id, 0),
                        job=jobs.get(work.id),
                        continuity_chapter_no=work.continuity_chapter_no,
                    ),
                    last_opened_at=work.last_opened_at,
                    updated_at=work.updated_at,
                )
                for work in works
            ]
            next_cursor = None
            if more and works:
                last = works[-1]
                sort_value = (
                    last.title_search
                    if sort == "title"
                    else (last.last_opened_at or last.created_at)
                    if sort == "opened"
                    else last.updated_at
                )
                next_cursor = _encode_cursor(sort, sort_value, last.id)
            return WorkListResponse(items=items, next_cursor=next_cursor)

        return await self.uow.read(read)

    async def get(self, work_id: str) -> WorkOut:
        async def read(session: AsyncSession):
            repo = WorkRepository(session)
            work = await repo.get(work_id)
            if work is None:
                raise AppError(ErrorCode.NOT_FOUND)
            return _work_out(work, await repo.get_style(work_id))

        return await self.uow.read(read)

    async def get_style_profile(self, work_id: str) -> StyleProfileOut:
        async def read(session: AsyncSession):
            repo = WorkRepository(session)
            work = await repo.get(work_id)
            profile = await repo.get_style(work_id) if work is not None else None
            if profile is None:
                raise AppError(ErrorCode.NOT_FOUND)
            return StyleProfileOut.model_validate(_style_out(profile))

        return await self.uow.read(read)

    async def put_style_profile(self, work_id: str, body: StyleProfileIn) -> StyleProfileOut:
        async def write(ctx: WriteContext):
            repo = WorkRepository(ctx.session)
            work = await repo.get(work_id)
            profile = await repo.get_style(work_id) if work is not None else None
            if profile is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if profile.revision != body.expected_revision:
                raise AppError(ErrorCode.REVISION_CONFLICT)
            profile.vocab_register = body.vocab_register
            profile.dialogue_style = body.dialogue_style
            profile.dialogue_dash_char = (
                body.dialogue_dash_char if body.dialogue_style == "dash" else None
            )
            profile.tone_mark_style = body.tone_mark_style
            profile.punctuation_rules = json.dumps(
                body.punctuation_rules, ensure_ascii=False, separators=(",", ":")
            )
            profile.banned_phrases = json.dumps(
                body.banned_phrases, ensure_ascii=False, separators=(",", ":")
            )
            profile.voice = body.voice
            profile.voice_samples = json.dumps(
                body.voice_samples, ensure_ascii=False, separators=(",", ":")
            )
            profile.revision += 1
            profile.updated_at = utcnow_iso()
            await ctx.session.flush()
            return StyleProfileOut.model_validate(_style_out(profile))

        return await self.uow.write(write)

    async def create(self, body: WorkCreate, key: str) -> tuple[int, WorkOut]:
        presets = _genre_map()
        preset = presets.get(body.genre or "")
        now = utcnow_iso()
        work_id = new_id()
        style_id = new_id()

        async def operation(ctx: WriteContext):
            repo = WorkRepository(ctx.session)
            project_id = await repo.default_project_id()
            work = Work(
                id=work_id,
                project_id=project_id,
                title=body.title,
                title_search=fold_text(body.title),
                language=body.language,
                genre=body.genre if preset else None,
                genre_label_custom=body.genre_label_custom,
                status="draft",
                wizard_step=body.wizard_step,
                wizard_completed_steps="[]",
                created_at=now,
                updated_at=now,
                revision=1,
            )
            defaults = (preset or {}).get("defaults", {})
            profile = StyleProfile(
                id=style_id,
                work_id=work_id,
                vocab_register=defaults.get("vocab_register", "balanced"),
                dialogue_style=defaults.get("dialogue_style", "dash"),
                dialogue_dash_char="\u2013"
                if defaults.get("dialogue_style", "dash") == "dash"
                else None,
                tone_mark_style=defaults.get("tone_mark_style", "new"),
                punctuation_rules="{}",
                banned_phrases="[]",
                voice_samples="[]",
                revision=1,
                updated_at=now,
            )
            ctx.session.add(work)
            await ctx.session.flush()
            ctx.session.add(profile)
            await ctx.session.flush()
            return 201, jsonable_encoder(_work_out(work, profile))

        result = await IdempotencyService(self.uow).execute(
            key=key,
            method="POST",
            path="/v1/works",
            body=body,
            operation=operation,
        )
        return result.status_code, WorkOut.model_validate(result.body)

    async def patch(self, work_id: str, body: WorkPatch) -> WorkOut:
        fields = body.model_dump(exclude={"expected_revision"}, exclude_unset=True)
        non_nullable = {
            "title",
            "chapter_length_min",
            "chapter_length_max",
            "autowrite_mode_default",
            "status",
            "wizard_completed_steps",
        }
        if any(name in fields and fields[name] is None for name in non_nullable):
            raise AppError(ErrorCode.VALIDATION, detail={"reason": "null_not_allowed"})

        async def write(ctx: WriteContext):
            repo = WorkRepository(ctx.session)
            work = await repo.get(work_id)
            if work is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if work.revision != body.expected_revision:
                raise AppError(ErrorCode.REVISION_CONFLICT)
            committed = (await self._committed_counts(ctx.session, [work_id])).get(work_id, 0)
            if (
                "target_chapters" in fields
                and fields["target_chapters"] is not None
                and fields["target_chapters"] < committed
            ):
                raise AppError(
                    ErrorCode.VALIDATION, detail={"field": "target_chapters", "minimum": committed}
                )
            min_length = fields.get("chapter_length_min", work.chapter_length_min)
            max_length = fields.get("chapter_length_max", work.chapter_length_max)
            if not validate_length_range(min_length, max_length):
                raise AppError(ErrorCode.VALIDATION, detail={"field": "chapter_length"})
            requested_status = fields.get("status")
            if requested_status == "ready":
                candidate_values = {
                    field: getattr(work, field)
                    for field in (
                        "id",
                        "title",
                        "genre",
                        "genre_label_custom",
                        "brief",
                        "target_chapters",
                        "chapter_length_min",
                        "chapter_length_max",
                    )
                }
                candidate_values.update(fields)
                if "genre" in fields and fields["genre"] not in _genre_map():
                    candidate_values["genre"] = None
                missing = await validate_ready_transition(
                    SimpleNamespace(**candidate_values), self.foundation
                )
                if missing:
                    raise AppError(
                        ErrorCode.VALIDATION, detail={"missing": list(dict.fromkeys(missing))}
                    )
                fields["wizard_step"] = None
            if work.status == "ready" and requested_status == "draft" and committed:
                raise AppError(ErrorCode.VALIDATION, detail={"reason": "committed_chapters"})
            if (
                fields.get("autowrite_mode_default", work.autowrite_mode_default)
                == "review_every_k"
            ):
                k = fields.get("review_every_k", work.review_every_k)
                if not k:
                    raise AppError(ErrorCode.VALIDATION, detail={"field": "review_every_k"})
            if "genre" in fields:
                preset = _genre_map().get(fields["genre"] or "")
                fields["genre"] = fields["genre"] if preset else None
            if "wizard_completed_steps" in fields and fields["wizard_completed_steps"] is not None:
                fields["wizard_completed_steps"] = json.dumps(fields["wizard_completed_steps"])
            for name, value in fields.items():
                if name == "title" and value is not None:
                    work.title_search = fold_text(value)
                if name == "continuity_reason" and value is not None:
                    value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                setattr(work, name, value)
            work.revision += 1
            work.updated_at = utcnow_iso()
            await ctx.session.flush()
            return _work_out(work, await repo.get_style(work_id))

        return await self.uow.write(write)

    async def delete(self, work_id: str) -> None:
        async def write(ctx: WriteContext):
            repo = WorkRepository(ctx.session)
            work = await repo.get(work_id)
            if work is None:
                raise AppError(ErrorCode.NOT_FOUND)
            active_job = await ctx.session.scalar(
                select(Job.id)
                .where(Job.work_id == work_id, Job.status.in_(_ACTIVE_JOB_STATES))
                .limit(1)
            )
            if active_job:
                raise AppError(ErrorCode.WORK_ACTIVE_JOB)
            work.deleted_at = utcnow_iso()
            work.updated_at = work.deleted_at
            work.revision += 1
            await ctx.session.flush()

        await self.uow.write(write)

    async def open(self, work_id: str, key: str) -> None:
        async def operation(ctx: WriteContext):
            work = await WorkRepository(ctx.session).get(work_id)
            if work is None:
                raise AppError(ErrorCode.NOT_FOUND)
            work.last_opened_at = utcnow_iso()
            work.updated_at = work.last_opened_at
            work.revision += 1
            await ctx.session.flush()
            return 204, {}

        await IdempotencyService(self.uow).execute(
            key=key,
            method="POST",
            path=f"/v1/works/{work_id}/open",
            body={},
            operation=operation,
        )

    async def _committed_counts(self, session: AsyncSession, work_ids: list[str]) -> dict[str, int]:
        if not work_ids:
            return {}
        exists = await session.run_sync(
            lambda sync_session: inspect(sync_session.bind).has_table("chapters")
        )
        if not exists:
            return {}
        rows = await session.execute(
            text(
                "SELECT work_id, COALESCE(MAX(chapter_no), 0) AS chapter_no "
                "FROM chapters WHERE work_id IN :work_ids AND status='committed' GROUP BY work_id"
            ).bindparams(bindparam("work_ids", expanding=True)),
            {"work_ids": work_ids},
        )
        return {row.work_id: int(row.chapter_no) for row in rows}


async def genres() -> list[GenrePresetOut]:
    return [GenrePresetOut.model_validate(item) for item in load_genres()]
