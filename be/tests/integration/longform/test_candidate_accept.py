import asyncio
import json

import pytest

from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_generation import ChapterCandidate
from writestory_be.modules.chapters.service import ChapterService


@pytest.fixture
async def longform_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


def _doc(text):
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"paragraph_id": "para0001"},
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


@pytest.mark.asyncio
async def test_accept_returns_three_way_conflict_without_closing_candidate(
    client, runtime, longform_db
):
    work = await client.post(
        "/v1/works", headers={"Idempotency-Key": "candidate-work-001"}, json={"title": "Candidate"}
    )
    work_id = work.json()["id"]
    chapter_response = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Chương"})
    chapter_id = chapter_response.json()["id"]
    candidate_id = new_id()

    async def setup(ctx):
        chapter = await ctx.session.get(Chapter, chapter_id)
        base = await ChapterService(runtime)._make_revision(
            ctx.session, chapter, _doc("Bản gốc"), source="manual", reason="test"
        )
        current = await ChapterService(runtime)._make_revision(
            ctx.session, chapter, _doc("Bản hiện tại"), source="manual", reason="test"
        )
        ctx.session.add(
            ChapterCandidate(
                id=candidate_id,
                work_id=work_id,
                chapter_id=chapter_id,
                chapter_no=1,
                job_id=None,
                kind="revise",
                mode="spot_fix",
                base_revision_id=base.id,
                scope="{}",
                author_instruction="Sửa",
                content_json="{}",
                plain_text="Bản AI",
                paragraphs_json=json.dumps([{"paragraph_id": "para0001", "text": "Bản AI"}]),
                ops_json="[]",
                status="ready",
                check_summary="{}",
                accepted_paragraph_ids="[]",
                created_at="2026-10-03T00:00:00Z",
                ready_at="2026-10-03T00:00:00Z",
            )
        )
        return current.id

    current_id = await runtime.ensure_database_services().write(setup)
    response = await client.post(
        f"/v1/candidates/{candidate_id}/accept", json={"expected_revision_id": current_id}
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["base"][0]["text"] == "Bản gốc"
    assert detail["current"][0]["text"] == "Bản hiện tại"
    assert detail["candidate"][0]["text"] == "Bản AI"
    assert detail["conflicts"][0]["kind"] == "both_modified"
    candidate = await client.get(f"/v1/candidates/{candidate_id}")
    assert candidate.json()["status"] == "ready"
