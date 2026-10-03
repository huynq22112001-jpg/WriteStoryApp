import asyncio

import pytest

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.system import Job


@pytest.fixture
async def works_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_create_patch_open_and_soft_delete_work(client, runtime, works_db):
    created = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "work-create-1"},
        json={"title": "Câu chuyện Đường Mây", "language": "vi", "genre": "xianxia"},
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["title"] == "Câu chuyện Đường Mây"
    assert item["status"] == "draft"
    assert item["style_profile"]["vocab_register"] == "han_viet"

    fetched = await client.get(f"/v1/works/{item['id']}")
    assert fetched.json()["revision"] == 1

    patched = await client.patch(
        f"/v1/works/{item['id']}",
        json={"expected_revision": 1, "brief": "Một hành trình."},
    )
    assert patched.status_code == 200
    assert patched.json()["revision"] == 2
    stale = await client.patch(
        f"/v1/works/{item['id']}",
        json={"expected_revision": 1, "brief": "Stale"},
    )
    assert stale.status_code == 409

    opened = await client.post(
        f"/v1/works/{item['id']}/open", headers={"Idempotency-Key": "work-open-1"}
    )
    assert opened.status_code == 204
    assert (await client.get(f"/v1/works/{item['id']}")).json()["last_opened_at"]

    deleted = await client.delete(f"/v1/works/{item['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/v1/works/{item['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_list_works_search_cursor_filter_and_ready_validation(client, works_db):
    for index, title in enumerate(("Nguyễn Du", "Đường về", "Mây trắng")):
        response = await client.post(
            "/v1/works",
            headers={"Idempotency-Key": f"work-list-{index}"},
            json={"title": title, "genre": "urban"},
        )
        assert response.status_code == 201, response.text
    page = await client.get("/v1/works?sort=title&limit=2")
    assert page.status_code == 200
    assert len(page.json()["items"]) == 2
    assert page.json()["next_cursor"]
    next_page = await client.get(
        "/v1/works", params={"sort": "title", "limit": 2, "cursor": page.json()["next_cursor"]}
    )
    assert len(next_page.json()["items"]) == 1
    found = await client.get("/v1/works?q=duong&genre=urban")
    assert [item["title"] for item in found.json()["items"]] == ["Đường về"]

    work_id = page.json()["items"][0]["id"]
    ready = await client.patch(
        f"/v1/works/{work_id}",
        json={"expected_revision": 1, "status": "ready"},
    )
    assert ready.status_code == 422
    assert "foundation" in ready.json()["detail"]["missing"]


@pytest.mark.asyncio
async def test_delete_work_rejects_active_job(client, runtime, works_db):
    created = await client.post(
        "/v1/works", headers={"Idempotency-Key": "work-active"}, json={"title": "Đang viết"}
    )
    work_id = created.json()["id"]
    now = utcnow_iso()
    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            Job(
                id=new_id(),
                idempotency_key="active-job",
                type="write",
                work_id=work_id,
                status="running",
                priority=0,
                input_json="{}",
                attempt=1,
                created_at=now,
                updated_at=now,
                revision=1,
            )
        )
        await session.commit()
    deleted = await client.delete(f"/v1/works/{work_id}")
    assert deleted.status_code == 409
    assert deleted.json()["code"] == "WORK_ACTIVE_JOB"


@pytest.mark.asyncio
async def test_invalid_language_and_idempotency(client, works_db):
    invalid = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "invalid-language"},
        json={"title": "bad", "language": "en"},
    )
    assert invalid.status_code == 422

    first = await client.post(
        "/v1/works", headers={"Idempotency-Key": "replay"}, json={"title": "A"}
    )
    replay = await client.post(
        "/v1/works", headers={"Idempotency-Key": "replay"}, json={"title": "A"}
    )
    assert first.json()["id"] == replay.json()["id"]
    conflict = await client.post(
        "/v1/works", headers={"Idempotency-Key": "replay"}, json={"title": "B"}
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_style_profile_get_put_revision_and_validation(client, works_db):
    created = await client.post(
        "/v1/works", headers={"Idempotency-Key": "style-profile-work"}, json={"title": "Giọng kể"}
    )
    work_id = created.json()["id"]
    first = await client.get(f"/v1/works/{work_id}/style-profile")
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    payload = {
        "expected_revision": 1,
        "vocab_register": "thuan_viet",
        "dialogue_style": "quotes",
        "tone_mark_style": "old",
        "punctuation_rules": {"ellipsis": "…"},
        "banned_phrases": ["cụm sáo"],
        "voice": "Điềm tĩnh, giàu hình ảnh.",
        "voice_samples": ["Mẫu giọng thứ nhất.", "Mẫu giọng thứ hai."],
    }
    saved = await client.put(f"/v1/works/{work_id}/style-profile", json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 2
    assert saved.json()["dialogue_dash_char"] is None
    assert saved.json()["punctuation_rules"] == {"ellipsis": "…"}
    assert saved.json()["voice_samples"] == payload["voice_samples"]

    stale = await client.put(f"/v1/works/{work_id}/style-profile", json=payload)
    assert stale.status_code == 409

    too_many = {**payload, "expected_revision": 2, "voice_samples": ["a", "b", "c"]}
    assert (
        await client.put(f"/v1/works/{work_id}/style-profile", json=too_many)
    ).status_code == 422
    too_long = {**payload, "expected_revision": 2, "voice_samples": ["x" * 2001]}
    assert (
        await client.put(f"/v1/works/{work_id}/style-profile", json=too_long)
    ).status_code == 422


@pytest.mark.asyncio
async def test_language_genres_are_loaded_from_ai_package(client, works_db):
    languages = await client.get("/v1/languages")
    assert languages.json() == [{"code": "vi", "label": "Tiếng Việt", "enabled": True}]
    genres = await client.get("/v1/languages/vi/genres")
    assert genres.status_code == 200
    assert {genre["key"] for genre in genres.json()} == {
        "xianxia",
        "wuxia",
        "fantasy",
        "palace",
        "transmigration",
        "detective",
        "urban",
        "romance",
    }
    assert (await client.get("/v1/languages/en/genres")).status_code == 404
