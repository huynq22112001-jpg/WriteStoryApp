import asyncio

import pytest

from writestory_be.infrastructure.db.migrations import prepare_database


@pytest.fixture
async def chapters_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_chapter_working_copy_snapshot_diff_and_restore(client, chapters_db):
    work = await client.post(
        "/v1/works", headers={"Idempotency-Key": "chapter-work"}, json={"title": "Bản thảo"}
    )
    work_id = work.json()["id"]
    created = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Mở đầu"})
    assert created.status_code == 201
    chapter_id = created.json()["id"]
    doc1 = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"paragraph_id": "abcdef01"},
                "content": [{"type": "text", "text": "Ngày đầu."}],
            }
        ],
    }
    saved = await client.put(
        f"/v1/chapters/{chapter_id}/working-copy",
        json={
            "doc_json": doc1,
            "base_revision_id": None,
            "client_session_id": "tab-a",
            "client_seq": 1,
        },
    )
    assert saved.status_code == 200
    first = await client.post(
        f"/v1/chapters/{chapter_id}/snapshot", json={"reason": "manual_snapshot"}
    )
    assert first.status_code == 200
    revision1 = first.json()
    assert revision1["plain_text"] == "Ngày đầu."
    doc2 = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"paragraph_id": "abcdef01"},
                "content": [{"type": "text", "text": "Ngày thứ hai."}],
            }
        ],
    }
    saved = await client.put(
        f"/v1/chapters/{chapter_id}/working-copy",
        json={
            "doc_json": doc2,
            "base_revision_id": revision1["id"],
            "client_session_id": "tab-a",
            "client_seq": 2,
        },
    )
    assert saved.status_code == 200
    diff = await client.get(f"/v1/chapters/{chapter_id}/revisions/{revision1['id']}/diff/working")
    assert diff.status_code == 200
    assert diff.json()["changes"][0]["op"] == "replace"
    second = await client.post(f"/v1/chapters/{chapter_id}/snapshot", json={"reason": "idle"})
    assert second.status_code == 200
    restored = await client.post(
        f"/v1/chapters/{chapter_id}/revisions/{revision1['id']}/restore",
        json={"expected_revision": 2},
    )
    assert restored.status_code == 200
    assert restored.json()["revision_no"] == 3


@pytest.mark.asyncio
async def test_chapter_reorder_requires_exact_active_chapter_set(client, chapters_db):
    work = await client.post(
        "/v1/works", headers={"Idempotency-Key": "chapter-reorder-work"}, json={"title": "Thứ tự"}
    )
    work_id = work.json()["id"]
    one = (await client.post(f"/v1/works/{work_id}/chapters", json={})).json()
    two = (await client.post(f"/v1/works/{work_id}/chapters", json={})).json()
    response = await client.post(
        f"/v1/works/{work_id}/chapters/reorder", json={"chapter_ids": [two["id"], one["id"]]}
    )
    assert response.status_code == 200
    assert response.json()[0]["id"] == two["id"]


@pytest.mark.asyncio
async def test_inserting_and_deleting_middle_chapter_keeps_contiguous_numbers(client, chapters_db):
    work = await client.post(
        "/v1/works", headers={"Idempotency-Key": "chapter-shift-work"}, json={"title": "Chèn"}
    )
    work_id = work.json()["id"]
    chapters = [
        (await client.post(f"/v1/works/{work_id}/chapters", json={"title": f"Chương {i}"})).json()
        for i in range(1, 4)
    ]

    inserted = await client.post(
        f"/v1/works/{work_id}/chapters", json={"chapter_no": 2, "title": "Chèn giữa"}
    )
    assert inserted.status_code == 201
    listing = (await client.get(f"/v1/works/{work_id}/chapters")).json()
    assert [chapter["chapter_no"] for chapter in listing] == [1, 2, 3, 4]

    removed = await client.delete(f"/v1/chapters/{inserted.json()['id']}")
    assert removed.status_code == 204
    listing = (await client.get(f"/v1/works/{work_id}/chapters")).json()
    assert [chapter["chapter_no"] for chapter in listing] == [1, 2, 3]
    assert [chapter["id"] for chapter in listing] == [
        chapters[0]["id"],
        chapters[1]["id"],
        chapters[2]["id"],
    ]


@pytest.mark.asyncio
async def test_snapshot_and_restore_reject_stale_revision(client, chapters_db):
    work = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "chapter-conflict-work"},
        json={"title": "Xung đột"},
    )
    work_id = work.json()["id"]
    chapter = (await client.post(f"/v1/works/{work_id}/chapters", json={})).json()
    chapter_id = chapter["id"]
    saved = await client.put(
        f"/v1/chapters/{chapter_id}/working-copy",
        json={
            "doc_json": {
                "type": "doc",
                "content": [{"type": "paragraph", "attrs": {"paragraph_id": "abcdef01"}}],
            },
            "base_revision_id": None,
        },
    )
    assert saved.status_code == 200
    snapshot = await client.post(
        f"/v1/chapters/{chapter_id}/snapshot", json={"expected_revision": 0}
    )
    assert snapshot.status_code == 200
    stale_snapshot = await client.post(
        f"/v1/chapters/{chapter_id}/snapshot", json={"expected_revision": 0}
    )
    assert stale_snapshot.status_code == 409
    stale_restore = await client.post(
        f"/v1/chapters/{chapter_id}/revisions/{snapshot.json()['id']}/restore",
        json={"expected_revision": 0},
    )
    assert stale_restore.status_code == 409
