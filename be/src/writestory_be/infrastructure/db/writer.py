from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.guards import in_write_txn
from writestory_be.infrastructure.db.unit_of_work import WriteContext, persist_events

log = logging.getLogger(__name__)
T = TypeVar("T")
WriteFn = Callable[[WriteContext], Awaitable[T]]


@dataclass
class _Command:
    fn: WriteFn[Any]
    future: asyncio.Future[Any]


class WriterQueue:
    """Một consumer tuần tự hóa toàn bộ transaction ghi SQLite."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], event_bus=None, *, maxsize: int = 256
    ) -> None:
        self.sessions = sessions
        self.event_bus = event_bus
        self.queue: asyncio.Queue[_Command | None] = asyncio.Queue(maxsize=maxsize)
        self._task: asyncio.Task[None] | None = None
        self._accepting = True

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="db-writer")

    async def submit(self, fn: WriteFn[T], *, timeout_s: float = 10) -> T:
        if not self._accepting:
            raise AppError(ErrorCode.BACKEND_SHUTTING_DOWN)
        self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()
        try:
            await asyncio.wait_for(self.queue.put(_Command(fn, future)), timeout=timeout_s)
        except TimeoutError as exc:
            raise AppError(ErrorCode.DB_BUSY) from exc
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout_s)
        except TimeoutError as exc:
            raise AppError(ErrorCode.DB_BUSY) from exc

    async def close(self, *, timeout_s: float = 10) -> None:
        if self._task is None:
            self._accepting = False
            return
        self._accepting = False
        await asyncio.wait_for(self.queue.put(None), timeout=timeout_s)
        await asyncio.wait_for(self._task, timeout=timeout_s)
        self._task = None

    async def _run(self) -> None:
        while True:
            command = await self.queue.get()
            if command is None:
                return
            started = asyncio.get_running_loop().time()
            try:
                async with self.sessions() as session:
                    async with session.begin():
                        ctx = WriteContext(session)
                        token = in_write_txn.set(True)
                        try:
                            result = await command.fn(ctx)
                            await persist_events(ctx)
                        finally:
                            in_write_txn.reset(token)
                if self.event_bus is not None:
                    for event, row in zip(ctx.events, ctx.persisted_rows, strict=True):
                        self.event_bus.publish(
                            event.type,
                            event.payload,
                            work_id=event.work_id,
                            job_id=event.job_id,
                            chapter_no=event.chapter_no,
                            seq=row.seq,
                            ts=row.ts,
                        )
                for callback in ctx.callbacks:
                    value = callback()
                    if asyncio.iscoroutine(value):
                        await value
                if asyncio.get_running_loop().time() - started > 0.2:
                    log.warning("DB write command exceeded 200 ms")
                if not command.future.done():
                    command.future.set_result(result)
            except OperationalError as exc:
                if not command.future.done():
                    if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                        command.future.set_exception(AppError(ErrorCode.DB_BUSY))
                    else:
                        command.future.set_exception(exc)
            except BaseException as exc:
                if not command.future.done():
                    command.future.set_exception(exc)
