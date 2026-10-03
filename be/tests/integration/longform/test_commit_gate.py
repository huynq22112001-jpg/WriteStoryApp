import asyncio
import json

import pytest
from sqlalchemy import select

from writestory_ai.contracts.state import EndingState, StateDelta, StoryState, StoryTime
from writestory_ai.state.apply import state_hash
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_generation import (
    ChapterCandidate,
    ChapterHandoff,
)
from writestory_be.infrastructure.db.models.longform_state import StoryStateRow
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.modules.longform.commit import commit_chapter


@pytest.fixture
async def longform_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_commit_candidate_writes_revision_state_handoff_and_job_atomically(
    client, runtime, longform_db
):
    work_response = await client.post(
        "/v1/works", headers={"Idempotency-Key": "commit-work-001"}, json={"title": "Commit"}
    )
    work_id = work_response.json()["id"]
    chapter_response = await client.post(
        f"/v1/works/{work_id}/chapters", json={"title": "Chương 1"}
    )
    chapter_id = chapter_response.json()["id"]
    seed = StoryState(work_id=work_id, chapter_no=0, story_time={"label": "Đầu", "ordinal": 0})
    seed_hash = state_hash(seed)
    job_id, candidate_id = new_id(), new_id()
    ending = EndingState(
        story_time=StoryTime(label="Đầu", ordinal=0), last_scene_summary="Kết cảnh"
    )
    delta = StateDelta(
        work_id=work_id,
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=seed_hash,
        source="pipeline",
        candidate_id=candidate_id,
        ending_state=ending,
    )
    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            StoryStateRow(
                id=new_id(),
                work_id=work_id,
                chapter_no=0,
                schema_version=1,
                state_json=seed.model_dump_json(),
                state_hash=seed_hash,
                delta_json="{}",
                source="seed",
                is_current=True,
                created_at="2026-10-03T00:00:00Z",
            )
        )
        session.add(
            Job(
                id=job_id,
                idempotency_key="commit-job-001",
                type="write",
                work_id=work_id,
                status="waiting_user",
                input_json=json.dumps({"mode": "auto"}),
                attempt=1,
                created_at="2026-10-03T00:00:00Z",
                updated_at="2026-10-03T00:00:00Z",
                revision=1,
            )
        )
        session.add(
            ChapterCandidate(
                id=candidate_id,
                work_id=work_id,
                chapter_id=chapter_id,
                chapter_no=1,
                job_id=job_id,
                kind="draft",
                base_revision_id=None,
                status="ready",
                scope="{}",
                content_json="{}",
                plain_text="Bình minh lên.",
                paragraphs_json=json.dumps(
                    [{"paragraph_id": "para0001", "text": "Bình minh lên."}]
                ),
                ops_json="[]",
                check_summary="{}",
                proposed_delta=delta.model_dump_json(),
                ending_state=ending.model_dump_json(),
                accepted_paragraph_ids="[]",
                created_at="2026-10-03T00:00:00Z",
            )
        )
        await session.commit()
    result = await commit_chapter(
        runtime.ensure_database_services(), job_id=job_id, candidate_id=candidate_id
    )
    assert result["revision_id"]
    async with runtime.ensure_database_services().read_sessions() as session:
        chapter = await session.get(Chapter, chapter_id)
        job = await session.get(Job, job_id)
        handoff = await session.scalar(
            select(ChapterHandoff).where(
                ChapterHandoff.chapter_no == 1, ChapterHandoff.is_current.is_(True)
            )
        )
        state = await session.scalar(
            select(StoryStateRow).where(
                StoryStateRow.chapter_no == 1, StoryStateRow.is_current.is_(True)
            )
        )
        assert chapter.status == "committed" and chapter.state_applied is True
        assert job.status == "succeeded"
        assert handoff.revision_id == result["revision_id"]
        assert state.revision_id == result["revision_id"]
