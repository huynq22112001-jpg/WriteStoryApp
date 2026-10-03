import asyncio
from datetime import UTC, datetime

import pytest

from writestory_ai.contracts.state import StateDelta, StoryState
from writestory_ai.state.apply import state_hash
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.ai.context_adapter import DatabaseContextAdapter
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.longform_state import (
    ContextTrace,
    StoryStateRow,
    Summary,
)
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
async def test_memory_apis_search_summary_trace_and_context(client, runtime, memory_db):
    created = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "memory-api-work"},
        json={"title": "Bộ nhớ"},
    )
    work_id = created.json()["id"]
    chapter = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Gặp gỡ"})
    chapter_id = chapter.json()["id"]
    seed = StoryState(work_id=work_id, chapter_no=0, story_time={"label": "Đầu", "ordinal": 0})
    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            StoryStateRow(
                id=new_id(),
                work_id=work_id,
                chapter_no=0,
                schema_version=1,
                state_json=seed.model_dump_json(),
                state_hash=state_hash(seed),
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
        base_state_hash=state_hash(seed),
        source="user",
        ops=[
            {
                "op": "fact.add",
                "fact": {
                    "id": "fact-moon",
                    "subject": "Mặt trăng",
                    "predicate": "ẩn",
                    "object": "dưới đáy hồ",
                    "evidence": {
                        "kind": "user",
                        "note": "Tác giả xác nhận",
                        "at": datetime.now(UTC).isoformat(),
                    },
                },
            }
        ],
    )
    await MemoryService(runtime).apply_delta(delta)
    state_response = await client.get(f"/v1/works/{work_id}/state?chapter=1")
    assert state_response.status_code == 200
    assert state_response.json()["state"]["facts"][0]["id"] == "fact-moon"
    changes = await client.get(f"/v1/works/{work_id}/state/changes", params={"from": 0, "to": 1})
    assert changes.status_code == 200
    assert changes.json()[0]["op"] == "fact.add"
    memory = await client.get(f"/v1/chapters/{chapter_id}/memory")
    assert memory.status_code == 200
    assert memory.json()["facts_active"][0]["id"] == "fact-moon"
    search = await client.get(f"/v1/works/{work_id}/search?q=trăng")
    assert search.status_code == 200
    assert search.json()["items"][0]["kind"] == "fact"

    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            Summary(
                id="sum-1",
                work_id=work_id,
                level="chapter",
                chapter_no=1,
                from_chapter=1,
                to_chapter=1,
                text="Mặt trăng ẩn dưới hồ.",
                key_points="[]",
                token_estimate=5,
                source_hash="source-a",
                is_current=True,
                stale=False,
                pinned_by_user=False,
                created_at="2026-01-01T00:00:00Z",
            )
        )
        session.add(
            ContextTrace(
                id="trace-1",
                work_id=work_id,
                chapter_no=1,
                step="write",
                round=0,
                prompt_versions="{}",
                items="[]",
                notes="[]",
                size_bytes=0,
                compacted=False,
                created_at="2026-01-01T00:00:00Z",
            )
        )
        await session.commit()
    summaries = await client.get(f"/v1/works/{work_id}/summaries")
    assert summaries.json()[0]["source_hash"] == "source-a"
    updated = await client.put(
        "/v1/summaries/sum-1",
        json={
            "expected_source_hash": "source-a",
            "text": "Tác giả sửa tóm tắt.",
            "pinned_by_user": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["pinned_by_user"] is True
    trace = await client.get(f"/v1/chapters/{chapter_id}/trace?step=write")
    assert trace.json()["traces"][0]["id"] == "trace-1"

    context = await DatabaseContextAdapter(runtime.ensure_database_services()).get_context(
        work_id, 2
    )
    assert context["state"]["chapter_no"] == 1
    assert context["summaries"][0]["text"] == "Tác giả sửa tóm tắt."
