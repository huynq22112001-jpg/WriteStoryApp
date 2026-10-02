from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import delete, select

from writestory_be.core.clock import to_iso, utcnow
from writestory_be.infrastructure.db.models.system import WorkLock

LEASE_SECONDS = 60
LOCK_RECHECK_SECONDS = 30


class LockLost(RuntimeError):
    """Raised when a job no longer owns its work lease."""


class WorkLockManager:
    def __init__(self, uow, owner_id: str) -> None:
        self.uow = uow
        self.owner_id = owner_id
        self._waiters: dict[str, asyncio.Event] = {}

    async def acquire(self, work_id: str, job_id: str) -> bool:
        now = utcnow()
        now_iso = to_iso(now)
        lease_iso = to_iso(now + timedelta(seconds=LEASE_SECONDS))

        async def write(ctx):
            row = await ctx.session.get(WorkLock, work_id)
            if row is not None and row.lease_expires_at <= now_iso:
                await ctx.session.delete(row)
                row = None
            if row is None:
                ctx.session.add(
                    WorkLock(
                        work_id=work_id,
                        job_id=job_id,
                        owner_id=self.owner_id,
                        acquired_at=now_iso,
                        heartbeat_at=now_iso,
                        lease_expires_at=lease_iso,
                    )
                )
                return True
            if row.job_id == job_id and row.owner_id == self.owner_id:
                row.heartbeat_at = now_iso
                row.lease_expires_at = lease_iso
                return True
            return False

        return await self.uow.write(write)

    async def wait_and_acquire(self, work_id: str, job_id: str) -> None:
        """Wait without failing fast; callers persist the job's waiting_slot state."""
        event = self._waiters.setdefault(work_id, asyncio.Event())
        while True:
            event.clear()
            if await self.acquire(work_id, job_id):
                return
            try:
                await asyncio.wait_for(event.wait(), timeout=LOCK_RECHECK_SECONDS)
            except TimeoutError:
                pass

    async def heartbeat(self, work_id: str, job_id: str) -> None:
        now = utcnow()
        now_iso = to_iso(now)
        lease_iso = to_iso(now + timedelta(seconds=LEASE_SECONDS))

        async def write(ctx):
            row = await ctx.session.get(WorkLock, work_id)
            if row is None or row.job_id != job_id or row.owner_id != self.owner_id:
                raise LockLost(f"Job {job_id} không còn giữ khóa của truyện {work_id}")
            row.heartbeat_at = now_iso
            row.lease_expires_at = lease_iso

        await self.uow.write(write)

    async def release(self, work_id: str, job_id: str) -> None:
        async def write(ctx):
            await ctx.session.execute(
                delete(WorkLock).where(
                    WorkLock.work_id == work_id,
                    WorkLock.job_id == job_id,
                    WorkLock.owner_id == self.owner_id,
                )
            )

        await self.uow.write(write)
        event = self._waiters.get(work_id)
        if event is not None:
            event.set()

    async def assert_held(self, ctx, work_id: str, job_id: str) -> None:
        now_iso = to_iso(utcnow())
        row = await ctx.session.scalar(
            select(WorkLock).where(
                WorkLock.work_id == work_id,
                WorkLock.job_id == job_id,
                WorkLock.owner_id == self.owner_id,
                WorkLock.lease_expires_at > now_iso,
            )
        )
        if row is None:
            raise LockLost(f"Job {job_id} không còn giữ khóa của truyện {work_id}")

    async def release_after_restart(self) -> None:
        async def write(ctx):
            await ctx.session.execute(delete(WorkLock))

        await self.uow.write(write)

