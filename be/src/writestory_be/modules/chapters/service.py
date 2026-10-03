from __future__ import annotations

import json
import unicodedata
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from writestory_ai.languages.registry import get_language_pack
from writestory_ai.languages.vi.length import count_syllables
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.chapters import (
    Chapter,
    ChapterRevision,
    ChapterWorkingCopy,
)
from writestory_be.infrastructure.db.models.system import Job, SearchDocument
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.infrastructure.db.unit_of_work import WriteContext
from writestory_be.modules.chapters.domain import align_paragraphs, project_doc, validate_doc

EMPTY_DOC = {
    "type": "doc",
    "content": [{"type": "paragraph", "attrs": {"paragraph_id": "00000000"}}],
}
_VI_PACK = get_language_pack("vi")


def _normalize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(doc, ensure_ascii=False))

    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "text" and isinstance(node.get("text"), str):
                node["text"] = _VI_PACK.normalize(node["text"])
            for child in node.get("content", []):
                visit(child)

    visit(value)
    return value


def _revision(row: ChapterRevision) -> dict[str, Any]:
    return {
        "id": row.id,
        "chapter_id": row.chapter_id,
        "revision_no": row.revision_no,
        "parent_revision_id": row.parent_revision_id,
        "source": row.source,
        "reason": row.reason,
        "doc_json": json.loads(row.doc_json),
        "plain_text": row.plain_text,
        "paragraphs": json.loads(row.paragraphs_json),
        "content_hash": row.content_hash,
        "syllable_count": row.syllable_count,
        "char_count": row.char_count,
        "created_at": row.created_at,
    }


class ChapterService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()

    async def list(self, work_id: str):
        async def read(session: AsyncSession):
            if await session.get(Work, work_id) is None:
                raise AppError(ErrorCode.NOT_FOUND)
            rows = (
                await session.scalars(
                    select(Chapter)
                    .where(Chapter.work_id == work_id, Chapter.deleted_at.is_(None))
                    .order_by(Chapter.chapter_no)
                )
            ).all()
            return [self._out(r) for r in rows]

        return await self.uow.read(read)

    async def get(self, chapter_id: str):
        async def read(session: AsyncSession):
            chapter = await session.get(Chapter, chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            value = self._out(chapter)
            value["is_base_locked"] = await self._chapter_locked(session, chapter)
            return value

        return await self.uow.read(read)

    async def create(self, work_id: str, body):
        async def write(ctx: WriteContext):
            session = ctx.session
            if await session.get(Work, work_id) is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if await self._work_busy(session, work_id):
                raise AppError(ErrorCode.CHAPTER_RANGE_CONFLICT)
            current = (
                await session.scalar(
                    select(func.max(Chapter.chapter_no)).where(
                        Chapter.work_id == work_id, Chapter.deleted_at.is_(None)
                    )
                )
                or 0
            )
            number = body.chapter_no or current + 1
            if number > current + 1:
                raise AppError(ErrorCode.VALIDATION, detail={"field": "chapter_no"})
            if number <= current:
                affected = list(
                    (
                        await session.scalars(
                            select(Chapter)
                            .where(
                                Chapter.work_id == work_id,
                                Chapter.chapter_no >= number,
                                Chapter.deleted_at.is_(None),
                            )
                            .order_by(Chapter.chapter_no.desc())
                        )
                    ).all()
                )
                for chapter in affected:
                    chapter.chapter_no = -chapter.chapter_no
                await session.flush()
                for chapter in affected:
                    chapter.chapter_no = -chapter.chapter_no + 1
                    chapter.updated_at = utcnow_iso()
            now = utcnow_iso()
            row = Chapter(
                id=new_id(),
                work_id=work_id,
                chapter_no=number,
                title=unicodedata.normalize("NFC", body.title),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.flush()
            return self._out(row)

        return await self.uow.write(write)

    async def delete(self, chapter_id: str):
        async def write(ctx: WriteContext):
            row = await ctx.session.get(Chapter, chapter_id)
            if row is None or row.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            if await self._work_busy(ctx.session, row.work_id):
                raise AppError(ErrorCode.CHAPTER_RANGE_CONFLICT)
            now = utcnow_iso()
            row.deleted_at = now
            row.updated_at = now
            affected = list(
                (
                    await ctx.session.scalars(
                        select(Chapter)
                        .where(
                            Chapter.work_id == row.work_id,
                            Chapter.chapter_no > row.chapter_no,
                            Chapter.deleted_at.is_(None),
                        )
                        .order_by(Chapter.chapter_no)
                    )
                ).all()
            )
            for chapter in affected:
                chapter.chapter_no = -chapter.chapter_no
            await ctx.session.flush()
            for chapter in affected:
                chapter.chapter_no = -chapter.chapter_no - 1
                chapter.updated_at = now

        await self.uow.write(write)

    async def reorder(self, work_id: str, chapter_ids: list[str]):
        async def write(ctx: WriteContext):
            if await self._work_busy(ctx.session, work_id):
                raise AppError(ErrorCode.CHAPTER_RANGE_CONFLICT)
            rows = list(
                (
                    await ctx.session.scalars(
                        select(Chapter)
                        .where(Chapter.work_id == work_id, Chapter.deleted_at.is_(None))
                        .order_by(Chapter.chapter_no)
                    )
                ).all()
            )
            if set(chapter_ids) != {r.id for r in rows} or len(chapter_ids) != len(rows):
                raise AppError(ErrorCode.VALIDATION, detail={"field": "chapter_ids"})
            by_id = {r.id: r for r in rows}
            for number, chapter_id in enumerate(chapter_ids, 1):
                by_id[chapter_id].chapter_no = -number
            await ctx.session.flush()
            for number, chapter_id in enumerate(chapter_ids, 1):
                by_id[chapter_id].chapter_no = number
            return [self._out(by_id[chapter_id]) for chapter_id in chapter_ids]

        return await self.uow.write(write)

    async def get_working_copy(self, chapter_id: str):
        async def read(session):
            chapter = await session.get(Chapter, chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            copy = await session.get(ChapterWorkingCopy, chapter_id)
            if copy:
                return {
                    "chapter_id": chapter_id,
                    "base_revision_id": copy.base_revision_id,
                    "doc_json": json.loads(copy.doc_json),
                    "has_changes": copy.has_changes,
                    "client_session_id": copy.client_session_id,
                    "client_seq": copy.client_seq,
                    "updated_at": copy.updated_at,
                }
            rev = (
                await session.get(ChapterRevision, chapter.current_revision_id)
                if chapter.current_revision_id
                else None
            )
            return {
                "chapter_id": chapter_id,
                "base_revision_id": chapter.current_revision_id,
                "doc_json": json.loads(rev.doc_json) if rev else EMPTY_DOC,
                "has_changes": False,
                "client_session_id": None,
                "client_seq": 0,
                "updated_at": chapter.updated_at,
            }

        return await self.uow.read(read)

    async def save_working_copy(self, chapter_id: str, body):
        try:
            validate_doc(body.doc_json)
        except ValueError as exc:
            raise AppError(ErrorCode.VALIDATION, detail={"reason": str(exc)}) from exc
        doc = _normalize_doc(body.doc_json)
        _, _plain, content_hash = project_doc(doc)

        async def write(ctx: WriteContext):
            chapter = await ctx.session.get(Chapter, chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            if await self._chapter_locked(ctx.session, chapter):
                raise AppError(ErrorCode.CHAPTER_READ_ONLY)
            current = (
                await ctx.session.get(ChapterRevision, chapter.current_revision_id)
                if chapter.current_revision_id
                else None
            )
            if (
                body.base_revision_id != chapter.current_revision_id
                and chapter.current_revision_id is not None
            ):
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={"current_revision": _revision(current) if current else None},
                )
            existing = await ctx.session.get(ChapterWorkingCopy, chapter_id)
            now = utcnow_iso()
            values = dict(
                base_revision_id=body.base_revision_id,
                doc_json=json.dumps(doc, ensure_ascii=False),
                content_hash=content_hash,
                has_changes=content_hash != (current.content_hash if current else ""),
                client_session_id=body.client_session_id,
                client_seq=body.client_seq,
                updated_at=now,
            )
            if existing:
                if (
                    body.client_session_id == existing.client_session_id
                    and body.client_seq <= existing.client_seq
                ):
                    return {
                        "chapter_id": chapter_id,
                        "base_revision_id": existing.base_revision_id,
                        "doc_json": json.loads(existing.doc_json),
                        "has_changes": existing.has_changes,
                        "client_session_id": existing.client_session_id,
                        "client_seq": existing.client_seq,
                        "updated_at": existing.updated_at,
                        "stale_write": True,
                    }
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                ctx.session.add(ChapterWorkingCopy(chapter_id=chapter_id, **values))
            return {"chapter_id": chapter_id, **values, "doc_json": doc, "stale_write": False}

        return await self.uow.write(write)

    async def snapshot(self, chapter_id: str, reason: str, expected_revision: int | None = None):
        async def write(ctx: WriteContext):
            chapter = await ctx.session.get(Chapter, chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            if expected_revision is not None and expected_revision != chapter.revision_count:
                current = (
                    await ctx.session.get(ChapterRevision, chapter.current_revision_id)
                    if chapter.current_revision_id
                    else None
                )
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={"current_revision": _revision(current) if current else None},
                )
            if await self._chapter_locked(ctx.session, chapter):
                raise AppError(ErrorCode.CHAPTER_READ_ONLY)
            copy = await ctx.session.get(ChapterWorkingCopy, chapter_id)
            doc = (
                json.loads(copy.doc_json)
                if copy
                else (
                    json.loads(
                        (
                            await ctx.session.get(ChapterRevision, chapter.current_revision_id)
                        ).doc_json
                    )
                    if chapter.current_revision_id
                    else EMPTY_DOC
                )
            )
            if not copy or not copy.has_changes:
                return (
                    _revision(await ctx.session.get(ChapterRevision, chapter.current_revision_id))
                    if chapter.current_revision_id
                    else None
                )
            revision = await self._make_revision(
                ctx.session, chapter, doc, source="manual", reason=reason
            )
            if copy:
                copy.base_revision_id = revision.id
                copy.has_changes = False
            return _revision(revision)

        return await self.uow.write(write)

    async def replace(self, chapter_id: str, body):
        if body.doc_json is not None:
            try:
                validate_doc(body.doc_json)
            except ValueError as exc:
                raise AppError(ErrorCode.VALIDATION, detail={"reason": str(exc)}) from exc

        async def write(ctx: WriteContext):
            chapter = await ctx.session.get(Chapter, chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            if body.expected_revision != chapter.revision_count:
                current = (
                    await ctx.session.get(ChapterRevision, chapter.current_revision_id)
                    if chapter.current_revision_id
                    else None
                )
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={"current_revision": _revision(current) if current else None},
                )
            if body.title is not None:
                chapter.title = unicodedata.normalize("NFC", body.title)
            if body.doc_json is not None:
                return _revision(
                    await self._make_revision(
                        ctx.session, chapter, body.doc_json, source="manual", reason="full_replace"
                    )
                )
            chapter.updated_at = utcnow_iso()
            return self._out(chapter)

        return await self.uow.write(write)

    async def revisions(self, chapter_id: str):
        async def read(session):
            if await session.get(Chapter, chapter_id) is None:
                raise AppError(ErrorCode.NOT_FOUND)
            rows = (
                await session.scalars(
                    select(ChapterRevision)
                    .where(ChapterRevision.chapter_id == chapter_id)
                    .order_by(ChapterRevision.revision_no.desc())
                )
            ).all()
            return [_revision(r) for r in rows]

        return await self.uow.read(read)

    async def diff(self, chapter_id: str, before_id: str, after_id: str):
        async def read(session):
            before = await session.get(ChapterRevision, before_id)
            after = None if after_id == "working" else await session.get(ChapterRevision, after_id)
            if (
                before is None
                or before.chapter_id != chapter_id
                or (after_id != "working" and (after is None or after.chapter_id != chapter_id))
            ):
                raise AppError(ErrorCode.NOT_FOUND)
            if after_id == "working":
                copy = await session.get(ChapterWorkingCopy, chapter_id)
                if copy is None:
                    raise AppError(ErrorCode.NOT_FOUND)
                after_paragraphs, _, _ = project_doc(json.loads(copy.doc_json))
                after_value = {"id": "working", "paragraphs": after_paragraphs}
            else:
                after_value = _revision(after)
            return {
                "before": _revision(before),
                "after": after_value,
                "changes": align_paragraphs(
                    json.loads(before.paragraphs_json), after_value["paragraphs"]
                ),
            }

        return await self.uow.read(read)

    async def restore(self, chapter_id: str, revision_id: str, expected_revision: int):
        async def write(ctx: WriteContext):
            chapter = await ctx.session.get(Chapter, chapter_id)
            source = await ctx.session.get(ChapterRevision, revision_id)
            if chapter is None or source is None or source.chapter_id != chapter_id:
                raise AppError(ErrorCode.NOT_FOUND)
            if chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            if chapter.revision_count != expected_revision:
                current = (
                    await ctx.session.get(ChapterRevision, chapter.current_revision_id)
                    if chapter.current_revision_id
                    else None
                )
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={"current_revision": _revision(current) if current else None},
                )
            if await self._chapter_locked(ctx.session, chapter):
                raise AppError(ErrorCode.CHAPTER_READ_ONLY)
            working = await ctx.session.get(ChapterWorkingCopy, chapter_id)
            if working and working.has_changes:
                await self._make_revision(
                    ctx.session,
                    chapter,
                    json.loads(working.doc_json),
                    source="manual",
                    reason="before_restore",
                )
            return _revision(
                await self._make_revision(
                    ctx.session,
                    chapter,
                    json.loads(source.doc_json),
                    source="restore",
                    reason="restore",
                    restored_from_revision_id=source.id,
                )
            )

        return await self.uow.write(write)

    async def _make_revision(
        self, session, chapter, doc, *, source, reason, restored_from_revision_id=None
    ):
        normalized = _normalize_doc(doc)
        paragraphs, plain, digest = project_doc(normalized)
        plain = unicodedata.normalize("NFC", plain)
        revision = ChapterRevision(
            id=new_id(),
            chapter_id=chapter.id,
            revision_no=chapter.revision_count + 1,
            parent_revision_id=chapter.current_revision_id,
            source=source,
            reason=reason,
            doc_json=json.dumps(normalized, ensure_ascii=False),
            plain_text=plain,
            paragraphs_json=json.dumps(paragraphs, ensure_ascii=False),
            content_hash=digest,
            syllable_count=count_syllables(plain),
            char_count=len(plain),
            restored_from_revision_id=restored_from_revision_id,
            created_at=utcnow_iso(),
        )
        session.add(revision)
        chapter.current_revision_id = revision.id
        chapter.revision_count = revision.revision_no
        chapter.syllable_count = revision.syllable_count
        chapter.char_count = revision.char_count
        chapter.updated_at = revision.created_at
        await session.flush()
        await session.execute(
            __import__("sqlalchemy")
            .delete(SearchDocument)
            .where(
                SearchDocument.source_type == "chapter",
                SearchDocument.source_id == chapter.id,
            )
        )
        from writestory_be.core.text_fold import fold_text

        for paragraph in paragraphs:
            session.add(
                SearchDocument(
                    work_id=chapter.work_id,
                    source_type="chapter",
                    source_id=chapter.id,
                    paragraph_id=paragraph["id"],
                    chapter_no=chapter.chapter_no,
                    source_revision_id=revision.id,
                    language="vi",
                    title=chapter.title,
                    title_norm=fold_text(chapter.title),
                    body=paragraph["text"],
                    body_norm=fold_text(paragraph["text"]),
                    updated_at=revision.created_at,
                )
            )
        await session.flush()
        return revision

    @staticmethod
    async def _work_busy(session, work_id):
        return bool(
            await session.scalar(
                select(Job.id).where(Job.work_id == work_id, Job.status == "running").limit(1)
            )
        )

    @staticmethod
    async def _chapter_locked(session, chapter):
        jobs = (
            await session.scalars(
                select(Job).where(
                    Job.work_id == chapter.work_id, Job.status.in_(("running", "waiting_slot"))
                )
            )
        ).all()
        return any(
            json.loads(job.input_json or "{}").get("base_chapter_no") == chapter.chapter_no
            for job in jobs
        )

    @staticmethod
    def _out(row):
        return {
            "id": row.id,
            "work_id": row.work_id,
            "chapter_no": row.chapter_no,
            "title": row.title,
            "status": row.status,
            "state_applied": row.state_applied,
            "revision_count": row.revision_count,
            "current_revision_id": row.current_revision_id,
            "syllable_count": row.syllable_count,
            "char_count": row.char_count,
        }
