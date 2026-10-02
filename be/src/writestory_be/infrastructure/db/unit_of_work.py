from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from writestory_be.core.clock import utcnow_iso
from writestory_be.infrastructure.db.models.system import JobEvent

T = TypeVar("T")
AfterCommit = Callable[[], Any | Awaitable[Any]]


@dataclass
class PendingEvent:
    type: str
    payload: dict[str, Any]
    work_id: str | None = None
    job_id: str | None = None
    chapter_no: int | None = None


@dataclass
class WriteContext:
    session: AsyncSession
    events: list[PendingEvent] = field(default_factory=list)
    callbacks: list[AfterCommit] = field(default_factory=list)
    persisted_rows: list[JobEvent] = field(default_factory=list)

    def add_event(
        self,
        type: str,
        payload: dict[str, Any],
        *,
        work_id: str | None = None,
        job_id: str | None = None,
        chapter_no: int | None = None,
    ) -> None:
        self.events.append(PendingEvent(type, payload, work_id, job_id, chapter_no))

    def after_commit(self, callback: AfterCommit) -> None:
        self.callbacks.append(callback)


class UnitOfWork:
    def __init__(self, read_sessions: async_sessionmaker[AsyncSession], writer_queue) -> None:
        self.read_sessions = read_sessions
        self.writer_queue = writer_queue

    async def read(self, fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
        async with self.read_sessions() as session:
            return await fn(session)

    async def write(
        self, fn: Callable[[WriteContext], Awaitable[T]], *, timeout_s: float = 10
    ) -> T:
        return await self.writer_queue.submit(fn, timeout_s=timeout_s)


async def persist_events(ctx: WriteContext) -> None:
    for event in ctx.events:
        row = JobEvent(
                v=1,
                ts=utcnow_iso(),
                type=event.type,
                work_id=event.work_id,
                job_id=event.job_id,
                chapter_no=event.chapter_no,
                payload_json=json.dumps(event.payload, ensure_ascii=False, separators=(",", ":")),
            )
        ctx.session.add(row)
        ctx.persisted_rows.append(row)
    await ctx.session.flush()
