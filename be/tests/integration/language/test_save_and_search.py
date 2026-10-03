import asyncio
import json
import unicodedata

import pytest

from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.chapters import ChapterWorkingCopy


@pytest.fixture
async def language_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_saved_working_copy_is_nfc_via_language_pack(client, runtime, language_db):
    work = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "language-save-work"},
        json={"title": "NFC", "genre": "urban"},
    )
    chapter = await client.post(f"/v1/works/{work.json()['id']}/chapters", json={})
    chapter_id = chapter.json()["id"]
    decomposed = "Đường đi Nguyễn Văn Ộc"
    saved = await client.put(
        f"/v1/chapters/{chapter_id}/working-copy",
        json={
            "doc_json": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"paragraph_id": "para0001"},
                        "content": [{"type": "text", "text": decomposed}],
                    }
                ],
            },
            "client_seq": 1,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["doc_json"]["content"][0]["content"][0]["text"] == unicodedata.normalize(
        "NFC", decomposed
    )
    async with runtime.ensure_database_services().read_sessions() as session:
        stored = await session.get(ChapterWorkingCopy, chapter_id)
        document = json.loads(stored.doc_json)
    text = document["content"][0]["content"][0]["text"]
    assert text == unicodedata.normalize("NFC", text)
