from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from writestory_ai.languages.registry import get_language_pack
from writestory_be.core.clock import utcnow_iso
from writestory_be.infrastructure.db.models.system import SearchDocument
from writestory_be.infrastructure.db.unit_of_work import WriteContext

FTS_INDEX_VERSION = 1
SEARCH_LIMIT_MAX = 200
Indexer = Callable[[WriteContext], Awaitable[None]]
_indexers: dict[str, Indexer] = {}


def normalize_for_search(value: str, language: str = "vi") -> str:
    return get_language_pack(language).search_fold(value)


def build_match_query(user_query: str, *, prefix_last: bool = False) -> str:
    folded = normalize_for_search(user_query)
    words = re.findall(r"[^\W_]+", folded, flags=re.UNICODE)
    if not words:
        return ""
    terms = [f'"{word}"' for word in words]
    if prefix_last:
        terms[-1] = f'"{words[-1]}"*'
    return " AND ".join(terms)


def register_search_indexer(source_type: str, fn: Indexer) -> None:
    if source_type in _indexers:
        raise ValueError(f"Search indexer đã đăng ký: {source_type}")
    _indexers[source_type] = fn


async def upsert_document(
    ctx: WriteContext,
    *,
    source_type: str,
    source_id: str,
    body: str,
    title: str | None = None,
    work_id: str | None = None,
    paragraph_id: str | None = None,
    chapter_no: int | None = None,
    source_revision_id: str | None = None,
    language: str = "vi",
) -> SearchDocument:
    conditions = [
        SearchDocument.source_type == source_type,
        SearchDocument.source_id == source_id,
        func.ifnull(SearchDocument.paragraph_id, "") == (paragraph_id or ""),
    ]
    document = await ctx.session.scalar(select(SearchDocument).where(*conditions))
    values = {
        "work_id": work_id,
        "source_type": source_type,
        "source_id": source_id,
        "paragraph_id": paragraph_id,
        "chapter_no": chapter_no,
        "source_revision_id": source_revision_id,
        "language": language,
        "title": title,
        "title_norm": normalize_for_search(title, language) if title else None,
        "body": body,
        "body_norm": normalize_for_search(body, language),
        "updated_at": utcnow_iso(),
    }
    if document is None:
        document = SearchDocument(**values)
        ctx.session.add(document)
    else:
        for key, value in values.items():
            setattr(document, key, value)
    return document


async def delete_document(
    ctx: WriteContext,
    *,
    source_type: str,
    source_id: str,
    paragraph_id: str | None = None,
) -> None:
    await ctx.session.execute(
        delete(SearchDocument).where(
            SearchDocument.source_type == source_type,
            SearchDocument.source_id == source_id,
            func.ifnull(SearchDocument.paragraph_id, "") == (paragraph_id or ""),
        )
    )


async def search(
    session: AsyncSession,
    user_query: str,
    *,
    work_id: str | None = None,
    limit: int = 50,
    prefix_last: bool = False,
) -> list[dict[str, Any]]:
    match_query = build_match_query(user_query, prefix_last=prefix_last)
    if not match_query:
        return []
    limit = min(max(limit, 1), SEARCH_LIMIT_MAX)
    predicates = [text("search_fts MATCH :match_query")]
    params: dict[str, Any] = {"match_query": match_query, "limit": limit}
    if work_id is not None:
        predicates.append(text("d.work_id = :work_id"))
        params["work_id"] = work_id
    statement = text(
        "SELECT d.id, d.work_id, d.source_type, d.source_id, d.paragraph_id, "
        "d.chapter_no, d.source_revision_id, d.title, d.body, "
        "bm25(search_fts, 5.0, 1.0) AS score "
        "FROM search_fts JOIN search_documents AS d ON d.id = search_fts.rowid "
        f"WHERE {' AND '.join(str(predicate) for predicate in predicates)} "
        "ORDER BY score LIMIT :limit"
    )
    rows = (await session.execute(statement, params)).mappings().all()
    return [dict(row) for row in rows]


async def rebuild_fts(session: AsyncSession) -> None:
    await session.execute(text("INSERT INTO search_fts(search_fts) VALUES ('rebuild')"))
    await session.execute(text("INSERT INTO search_trigram(search_trigram) VALUES ('delete-all')"))
    await session.execute(
        text(
            "INSERT INTO search_trigram(rowid, title_norm) "
            "SELECT id, title_norm FROM search_documents "
            "WHERE source_type IN ('character','location') AND title_norm IS NOT NULL"
        )
    )


async def rebuild_documents(ctx: WriteContext) -> None:
    for source_type in sorted(_indexers):
        await _indexers[source_type](ctx)
