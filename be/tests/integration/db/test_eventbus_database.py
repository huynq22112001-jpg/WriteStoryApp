import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from writestory_be.api.streams import stream_job_events
from writestory_be.bootstrap.context import Runtime
from writestory_be.bootstrap.protocol import BootstrapConfig
from writestory_be.infrastructure.db.engine import create_engine, database_path
from writestory_be.infrastructure.db.models.system import Job, JobEvent
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue
from writestory_be.jobs.events import EventBus


@pytest.mark.asyncio
async def test_event_bus_broadcasts_after_commit_and_replays_database_rows(tmp_path: Path) -> None:
    project_root = await asyncio.to_thread(lambda: Path(__file__).resolve().parents[3])
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.attributes["data_root"] = tmp_path
    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_engine(database_path(tmp_path))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    bus = EventBus(database_path=database_path(tmp_path))
    await bus.initialize()
    writer = WriterQueue(sessions, bus)
    uow = UnitOfWork(sessions, writer)
    subscriber = bus.subscribe()
    allow_commit = asyncio.Event()

    async def save_event(ctx):
        ctx.add_event("job.state", {"status": "running"}, job_id="job-a")
        await allow_commit.wait()

    pending = asyncio.create_task(uow.write(save_event))
    await asyncio.sleep(0.02)
    assert subscriber.queue.empty()
    allow_commit.set()
    await pending
    delivered = await asyncio.wait_for(subscriber.next(), timeout=1)
    assert delivered is not None and delivered.seq == 1

    async def rollback(ctx):
        ctx.add_event("job.state", {"status": "failed"}, job_id="job-b")
        raise ValueError("rollback")

    with pytest.raises(ValueError, match="rollback"):
        await uow.write(rollback)
    assert subscriber.queue.empty()
    async with sessions() as session:
        stored = list((await session.scalars(select(JobEvent))).all())
    assert len(stored) == 1

    async def save_other_job_event(ctx):
        ctx.add_event("job.state", {"status": "queued"}, job_id="job-b")

    await uow.write(save_other_job_event)

    restarted_bus = EventBus(database_path=database_path(tmp_path))
    await restarted_bus.initialize()
    replay = await restarted_bus.replay_async(0)
    assert replay is not None
    assert [(event.seq, event.payload["status"]) for event in replay] == [
        (1, "running"),
        (2, "queued"),
    ]

    async with sessions() as session, session.begin():
        session.add(
            Job(
                id="job-a",
                type="write",
                status="running",
                input_json="{}",
                created_at="2026-10-02T00:00:00.000Z",
                updated_at="2026-10-02T00:00:00.000Z",
            )
        )
        session.add(
            Job(
                id="job-b",
                type="write",
                status="running",
                input_json="{}",
                created_at="2026-10-02T00:00:00.000Z",
                updated_at="2026-10-02T00:00:00.000Z",
            )
        )

    await restarted_bus.initialize()
    runtime = Runtime(
        config=BootstrapConfig(protocol_version=1, token="test", data_root=tmp_path),
        event_bus=restarted_bus,
    )
    stream = stream_job_events("job-a", runtime, since=0)
    first_event = await anext(stream)
    assert first_event.id == "1"
    await stream.aclose()

    async with sessions() as session, session.begin():
        await session.execute(JobEvent.__table__.delete())
    gap = await restarted_bus.replay_async(0)
    assert gap is None

    bus.unsubscribe(subscriber)
    await writer.close()
    await engine.dispose()
