import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from writestory_be.infrastructure.db.base import Base
from writestory_be.infrastructure.db.guards import assert_not_in_write_txn
from writestory_be.infrastructure.db.models.system import JobEvent
from writestory_be.infrastructure.db.writer import WriterQueue


@pytest.mark.asyncio
async def test_concurrent_writes_are_serialized_and_rollback_events(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'writer.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)

    async def save_event(ctx, index: int) -> int:
        ctx.add_event("job.step", {"index": index})
        return index

    results = await asyncio.gather(
        *(writer.submit(lambda ctx, i=i: save_event(ctx, i)) for i in range(20))
    )
    assert sorted(results) == list(range(20))

    async def rollback(ctx):
        ctx.add_event("job.step", {"index": "rolled-back"})
        raise ValueError("rollback")

    with pytest.raises(ValueError, match="rollback"):
        await writer.submit(rollback)

    async with sessions() as session:
        count = await session.scalar(select(func.count()).select_from(JobEvent))
    assert count == 20
    await writer.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_external_call_guard_only_rejects_inside_write_callback(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'guard.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)

    def external_call() -> None:
        assert_not_in_write_txn()

    external_call()

    async def invalid_write(_ctx):
        external_call()

    with pytest.raises(RuntimeError, match="transaction"):
        await writer.submit(invalid_write)

    await writer.close()
    await engine.dispose()
