import asyncio

import pytest

from writestory_be.infrastructure.db.migrations import prepare_database


@pytest.fixture
async def language_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_language_presets_slop_list_and_revision_guard(client, language_db):
    presets = await client.get("/v1/languages/vi/genre-presets")
    assert presets.status_code == 200
    assert {preset["key"] for preset in presets.json()} == {
        "xianxia",
        "wuxia",
        "fantasy",
        "romance",
        "urban",
        "palace",
        "transmigration",
        "detective",
    }
    assert (await client.get("/v1/languages/en/genre-presets")).status_code == 422

    current = await client.get("/v1/languages/vi/slop-list")
    assert current.status_code == 200
    assert current.json()["version"] == 1
    assert any(entry["id"] == "opening.moment" for entry in current.json()["builtin"])
    saved = await client.put(
        "/v1/languages/vi/slop-list",
        json={
            "expected_version": 1,
            "additions": [{"id": "user.test", "pattern": "quả thật", "note": "test"}],
            "disabled": ["opening.moment"],
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"version": 2}
    stale = await client.put(
        "/v1/languages/vi/slop-list", json={"expected_version": 1, "additions": [], "disabled": []}
    )
    assert stale.status_code == 409
    invalid_regex = await client.put(
        "/v1/languages/vi/slop-list",
        json={
            "expected_version": 2,
            "additions": [{"id": "bad", "pattern": "(", "is_regex": True}],
        },
    )
    assert invalid_regex.status_code == 422


@pytest.mark.asyncio
async def test_normalize_and_text_check_include_stable_finding_metadata(client, language_db):
    normalized = await client.post(
        "/v1/languages/vi/normalize",
        json={"text": "Ca\u0302u\u200b  ", "mode": "paste"},
    )
    assert normalized.status_code == 200
    assert normalized.json()["text"] == "Câu"
    assert normalized.json()["changes"]
    too_large = await client.post(
        "/v1/languages/vi/normalize", json={"text": "á" * 600_000, "mode": "save"}
    )
    assert too_large.status_code == 422

    created = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "language-check-work"},
        json={"title": "Kiểm tra", "genre": "xianxia"},
    )
    work_id = created.json()["id"]
    checked = await client.post(
        f"/v1/works/{work_id}/text/check",
        json={
            "paragraphs": [{"paragraph_id": "para0001", "text": "Trong khoảnh khắc ấy, Đường về."}]
        },
    )
    assert checked.status_code == 200, checked.text
    finding = next(item for item in checked.json()["findings"] if item["check_id"] == "vi.slop")
    assert finding["paragraph_id"] == "para0001"
    assert finding["confidence"] == "high"
    assert finding["message_key"] == "vi.slop.density"
    assert finding["params"]["entry_id"] == "opening.moment"
    assert checked.json()["length"]["units"] > 0


@pytest.mark.asyncio
async def test_text_check_can_read_chapter_and_reject_unknown_checks(client, language_db):
    work = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "language-chapter-work"},
        json={"title": "Chương", "genre": "urban"},
    )
    work_id = work.json()["id"]
    chapter = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Một"})
    chapter_id = chapter.json()["id"]
    saved = await client.put(
        f"/v1/chapters/{chapter_id}/working-copy",
        json={
            "doc_json": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"paragraph_id": "para0001"},
                        "content": [{"type": "text", "text": "Trong khoảnh khắc ấy."}],
                    }
                ],
            },
            "client_seq": 1,
        },
    )
    assert saved.status_code == 200
    checked = await client.post(f"/v1/works/{work_id}/text/check", json={"chapter_id": chapter_id})
    assert checked.status_code == 200
    assert checked.json()["findings"][0]["paragraph_id"] == "para0001"
    invalid = await client.post(
        f"/v1/works/{work_id}/text/check",
        json={"paragraphs": [{"paragraph_id": "para0002", "text": "text"}], "checks": ["unknown"]},
    )
    assert invalid.status_code == 422
