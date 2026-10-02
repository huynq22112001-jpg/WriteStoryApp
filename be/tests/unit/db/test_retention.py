import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from writestory_be.infrastructure.db.base import Base
from writestory_be.infrastructure.db.models.system import IdempotencyRecord, JobEvent
from writestory_be.infrastructure.db.retention import run_retention_once


@pytest.mark.asyncio
async def test_retention_removes_expired_events_and_idempotency_records(tmp_path) -> None:
    database_path = tmp_path / "db" / "app.sqlite3"
    database_path.parent.mkdir()
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session, session.begin():
        session.add(
            JobEvent(
                v=1,
                ts="2020-01-01T00:00:00.000Z",
                type="job.state",
                payload_json=json.dumps({"status": "done"}),
            )
        )
        session.add(
            IdempotencyRecord(
                key="old-key",
                method="POST",
                path="/v1/things",
                request_hash="hash",
                status_code=202,
                response_json="{}",
                created_at="2020-01-01T00:00:00.000Z",
                expires_at="2020-01-02T00:00:00.000Z",
            )
        )
    await engine.dispose()

    removed = await run_retention_once(tmp_path)

    assert removed == {"job_events": 1, "idempotency_records": 1}
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(JobEvent)) == 0
        assert await session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0
    await engine.dispose()
