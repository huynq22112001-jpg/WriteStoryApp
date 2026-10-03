import asyncio

import pytest
from sqlalchemy import select

from writestory_ai.contracts.state import StoryState
from writestory_ai.state.apply import state_hash
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_state import StoryStateRow
from writestory_be.modules.chapters.service import ChapterService


@pytest.fixture
async def longform_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_resync_dry_run_checks_snapshot_and_chapter_range(client, runtime, longform_db):
    work_response = await client.post(
        "/v1/works", headers={"Idempotency-Key": "resync-work-001"}, json={"title": "Resync"}
    )
    work_id = work_response.json()["id"]
    chapter_ids = []
    for no in (1, 2):
        response = await client.post(
            f"/v1/works/{work_id}/chapters", json={"title": f"Chương {no}"}
        )
        chapter_ids.append(response.json()["id"])
    seed = StoryState(work_id=work_id, chapter_no=0, story_time={"label": "Đầu", "ordinal": 0})

    async def setup(ctx):
        ctx.session.add(
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
                created_at="2026-10-03T00:00:00Z",
            )
        )
        for chapter_id in chapter_ids:
            chapter = await ctx.session.get(Chapter, chapter_id)
            revision = await ChapterService(runtime)._make_revision(
                ctx.session,
                chapter,
                {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "attrs": {"paragraph_id": f"para{chapter.chapter_no:04d}"},
                            "content": [{"type": "text", "text": "Nội dung đã lưu."}],
                        }
                    ],
                },
                source="manual",
                reason="test",
            )
            chapter.status = "committed"
        return revision.id

    await runtime.ensure_database_services().write(setup)
    response = await client.post(
        f"/v1/works/{work_id}/resync", json={"from_chapter": 1, "to_chapter": 2, "dry_run": True}
    )
    assert response.status_code == 200
    assert response.json()["range"] == [1, 2]
    assert response.json()["chapter_count"] == 2
    assert response.json()["estimated_ai_calls"] == 2
    assert await runtime.ensure_database_services().read(
        lambda session: _no_resync_job(session, work_id)
    )


async def _no_resync_job(session, work_id):
    from writestory_be.infrastructure.db.models.system import Job

    return (
        await session.scalar(select(Job.id).where(Job.work_id == work_id, Job.type == "resync"))
        is None
    )
