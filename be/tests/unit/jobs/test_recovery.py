import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from writestory_be.infrastructure.db.base import Base
from writestory_be.infrastructure.db.models.system import Job, JobStep, WorkLock
from writestory_be.jobs.recovery import run_startup_reconcile


@pytest.mark.asyncio
async def test_startup_reconcile_marks_running_jobs_interrupted_and_clears_ephemeral_state(
    tmp_path,
) -> None:
    database_path = tmp_path / "db" / "app.sqlite3"
    database_path.parent.mkdir(parents=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session, session.begin():
        session.add(
            Job(
                id="job-1",
                type="write",
                status="running",
                input_json="{}",
                created_at="2026-10-02T00:00:00.000Z",
                updated_at="2026-10-02T00:00:00.000Z",
                stage="writer",
                checkpoint_json=json.dumps({"checkpoint": 1}),
            )
        )
        session.add(
            JobStep(
                id="step-1",
                job_id="job-1",
                step="writer",
                attempt=1,
                status="running",
                started_at="2026-10-02T00:00:00.000Z",
            )
        )
        session.add(
            WorkLock(
                work_id="work-1",
                job_id="job-1",
                owner_id="old-backend",
                acquired_at="2026-10-02T00:00:00.000Z",
                heartbeat_at="2026-10-02T00:00:00.000Z",
                lease_expires_at="2026-10-02T00:01:00.000Z",
            )
        )
    (tmp_path / "tmp").mkdir()
    (tmp_path / "tmp" / "stale.part").write_text("temporary", encoding="utf-8")
    await engine.dispose()

    result = await run_startup_reconcile(tmp_path)

    assert result.interrupted_count == 1
    assert result.interrupted_job_ids == ["job-1"]
    assert not (tmp_path / "tmp" / "stale.part").exists()
    async with sessions() as session:
        job = await session.get(Job, "job-1")
        step = await session.get(JobStep, "step-1")
        locks = list((await session.scalars(select(WorkLock))).all())
    assert job.status == "interrupted"
    assert job.stage == "writer"
    assert job.checkpoint_json == '{"checkpoint": 1}'
    assert step.status == "interrupted"
    assert locks == []
    await engine.dispose()
