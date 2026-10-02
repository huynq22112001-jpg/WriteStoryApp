import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from writestory_be.api.idempotency import IdempotencyService, request_hash
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.base import Base
from writestory_be.infrastructure.db.models.system import IdempotencyRecord
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue


@pytest.mark.asyncio
async def test_idempotency_replays_response_and_rejects_changed_body(tmp_path) -> None:
    database_path = tmp_path / "idempotency.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)
    service = IdempotencyService(UnitOfWork(sessions, writer))
    calls = 0

    async def create(_ctx):
        nonlocal calls
        calls += 1
        return 201, {"id": "created", "title": "Đêm mưa"}

    first = await service.execute(
        key="key-1", method="post", path="/v1/works", body={"b": 2, "a": 1}, operation=create
    )
    repeated = await service.execute(
        key="key-1", method="POST", path="/v1/works", body={"a": 1, "b": 2}, operation=create
    )
    assert first.status_code == repeated.status_code == 201
    assert first.body == repeated.body
    assert repeated.replayed is True
    assert calls == 1

    with pytest.raises(AppError) as conflict:
        await service.execute(
            key="key-1", method="POST", path="/v1/works", body={"a": 99}, operation=create
        )
    assert conflict.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert request_hash("post", "/v1/works", {"a": 1, "b": 2}) == request_hash(
        "POST", "/v1/works", {"b": 2, "a": 1}
    )
    await writer.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_same_key_runs_operation_once(tmp_path) -> None:
    database_path = tmp_path / "concurrent-idempotency.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)
    service = IdempotencyService(UnitOfWork(sessions, writer))
    calls = 0

    async def create(_ctx):
        nonlocal calls
        calls += 1
        return 202, {"job_id": "job-1", "status": "queued"}

    results = await asyncio.gather(
        *(
            service.execute(
                key="same-key",
                method="POST",
                path="/v1/jobs",
                body={"type": "write"},
                operation=create,
            )
            for _ in range(2)
        )
    )
    assert calls == 1
    assert sum(result.replayed for result in results) == 1
    async with sessions() as session:
        count = await session.scalar(select(func.count()).select_from(IdempotencyRecord))
    assert count == 1
    await writer.close()
    await engine.dispose()
