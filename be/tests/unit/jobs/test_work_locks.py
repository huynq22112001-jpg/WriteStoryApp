import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from writestory_be.core.clock import to_iso, utcnow
from writestory_be.infrastructure.db.base import Base
from writestory_be.infrastructure.db.models.system import WorkLock
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue
from writestory_be.jobs.locks import LockLost, WorkLockManager


@pytest.mark.asyncio
async def test_work_lock_waits_for_release_and_expired_lease_can_be_stolen(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'locks.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    uow = UnitOfWork(sessions, WriterQueue(sessions))
    manager = WorkLockManager(uow, "backend-a")

    assert await manager.acquire("work", "job-a") is True
    waiting = asyncio.create_task(manager.wait_and_acquire("work", "job-b"))
    await asyncio.sleep(0.01)
    await manager.release("work", "job-a")
    await asyncio.wait_for(waiting, timeout=1)
    await manager.release("work", "job-b")

    assert await manager.acquire("work", "job-c") is True
    async with sessions() as session, session.begin():
        await session.execute(
            update(WorkLock)
            .where(WorkLock.work_id == "work")
            .values(lease_expires_at=to_iso(utcnow() - timedelta(seconds=1)))
        )
    other_backend = WorkLockManager(uow, "backend-b")
    assert await other_backend.acquire("work", "job-d") is True
    await other_backend.release("work", "job-d")
    await engine.dispose()


@pytest.mark.asyncio
async def test_lock_heartbeat_and_fencing_raise_when_lease_is_lost(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'lock-loss.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)
    uow = UnitOfWork(sessions, writer)
    manager = WorkLockManager(uow, "backend")
    assert await manager.acquire("work", "job") is True
    await manager.heartbeat("work", "job")

    async def assert_fenced(ctx):
        await manager.assert_held(ctx, "work", "job")

    await uow.write(assert_fenced)
    await manager.release("work", "job")
    with pytest.raises(LockLost):
        await manager.heartbeat("work", "job")
    await writer.close()
    await engine.dispose()
