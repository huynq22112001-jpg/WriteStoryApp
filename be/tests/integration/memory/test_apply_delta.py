import asyncio

import pytest
from sqlalchemy import select

from writestory_ai.contracts.state import FactState, ParagraphEvidence, StateDelta, StoryState
from writestory_ai.state.apply import state_hash
from writestory_be.core.errors import AppError
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.longform_state import Fact, StoryStateRow
from writestory_be.modules.memory.service import MemoryService


@pytest.fixture
async def memory_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_apply_delta_writes_snapshot_and_ledger_atomically(client, runtime, memory_db):
    created = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "memory-state-work"},
        json={"title": "Sổ cái"},
    )
    work_id = created.json()["id"]
    state = StoryState(
        work_id=work_id,
        chapter_no=0,
        story_time={"label": "Mở đầu", "ordinal": 0},
        facts=[
            FactState(
                id="fact-1",
                subject="hero",
                predicate="identity",
                object="hidden",
                valid_from=0,
                is_secret=True,
                evidence=ParagraphEvidence(chapter_no=1, paragraph_id="para0001", quote="bí mật"),
            )
        ],
    )
    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            StoryStateRow(
                id=new_id(),
                work_id=work_id,
                chapter_no=0,
                schema_version=1,
                state_json=state.model_dump_json(),
                state_hash=state_hash(state),
                delta_json="{}",
                source="seed",
                is_current=True,
                created_at="2026-01-01T00:00:00Z",
            )
        )
        await session.commit()

    delta = StateDelta(
        work_id=work_id,
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="user",
        ops=[{"op": "fact.close", "fact_id": "fact-1"}],
    )
    result = await MemoryService(runtime).apply_delta(delta)
    assert result["state_hash"]
    async with runtime.ensure_database_services().read_sessions() as session:
        current = await session.scalar(
            select(StoryStateRow).where(
                StoryStateRow.work_id == work_id,
                StoryStateRow.chapter_no == 1,
                StoryStateRow.is_current.is_(True),
            )
        )
        fact = await session.get(Fact, "fact-1")
        assert current is not None
        assert StoryState.model_validate_json(current.state_json).facts[0].valid_until == 1
        assert fact.status == "closed"
        assert fact.closed_state_id == current.id

    invalid = StateDelta(
        work_id=work_id,
        chapter_no=2,
        base_state_chapter=1,
        base_state_hash=result["state_hash"],
        source="user",
        ops=[{"op": "fact.close", "fact_id": "missing"}],
    )
    with pytest.raises(AppError):
        await MemoryService(runtime).apply_delta(invalid)
    async with runtime.ensure_database_services().read_sessions() as session:
        assert (
            await session.scalar(
                select(StoryStateRow.id).where(
                    StoryStateRow.work_id == work_id,
                    StoryStateRow.chapter_no == 2,
                )
            )
            is None
        )
        assert await session.scalar(select(Fact.id).where(Fact.id == "fact-1")) == "fact-1"
