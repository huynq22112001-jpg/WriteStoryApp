import asyncio

import pytest

from writestory_ai.contracts.models import ProviderModel
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.modules.providers.service import ProviderService


@pytest.fixture
async def providers_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_provider_crud_models_and_limits_never_return_key(client, providers_db):
    created = await client.post(
        "/v1/providers",
        json={
            "name": "Local test",
            "protocol": "ollama_lmstudio",
            "base_url": "http://localhost:11434/v1/",
            "key_storage": "none",
            "auto_discover": False,
        },
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    assert provider["base_url"] == "http://localhost:11434/v1"
    assert "api_key" not in provider
    assert provider["has_key"] is False
    provider_id = provider["id"]

    models = await client.put(
        f"/v1/providers/{provider_id}/models",
        json={
            "expected_revision": 1,
            "items": [{"model_id": "local-model", "display_name": "Local"}],
        },
    )
    assert models.status_code == 200, models.text
    assert models.json()["default_model_id"] == "local-model"
    assert models.json()["effective"][0]["display_name"] == "Local"

    limits = await client.put(
        f"/v1/providers/{provider_id}/limits",
        json={"max_concurrent_requests": 2, "rpm": 20, "tpm": 10000, "max_retries": 2},
    )
    assert limits.status_code == 200
    assert limits.json()["max_concurrent_requests"] == 2

    updated = await client.patch(
        f"/v1/providers/{provider_id}", json={"expected_revision": 2, "enabled": False}
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    settings = await client.put(
        "/v1/settings/limits",
        json={
            "worker_pool": 3,
            "app_daily_usd": 12.5,
            "app_daily_tokens": 100000,
            "work_daily_usd_default": 4,
            "timezone": "Asia/Bangkok",
        },
    )
    assert settings.status_code == 200, settings.text
    assert (await client.get("/v1/settings/limits")).json() == settings.json()


@pytest.mark.asyncio
async def test_discovery_keeps_user_edits_and_tracks_missing_models(
    client, runtime, providers_db, monkeypatch
):
    response = await client.post(
        "/v1/providers",
        json={
            "name": "Discovery test",
            "protocol": "openai_compatible",
            "base_url": "http://localhost:1234/v1",
            "key_storage": "none",
            "auto_discover": False,
        },
    )
    provider_id = response.json()["id"]
    batches = [
        [ProviderModel(id="m1", display_name="First"), ProviderModel(id="m2")],
        [ProviderModel(id="m1", display_name="Renamed by server"), ProviderModel(id="m3")],
        [
            ProviderModel(id="m1", display_name="Renamed by server"),
            ProviderModel(id="m2"),
            ProviderModel(id="m3"),
        ],
    ]

    class Adapter:
        async def list_models(self):
            return batches.pop(0)

    async def fake_adapter(_self, _provider, _key):
        return Adapter()

    monkeypatch.setattr(ProviderService, "_adapter", fake_adapter)
    first = await client.post(f"/v1/providers/{provider_id}/discover", json={})
    assert first.json()["added"] == ["m1", "m2"]
    configured = await client.put(
        f"/v1/providers/{provider_id}/models",
        json={"expected_revision": 1, "items": [{"model_id": "m1", "display_name": "My name"}]},
    )
    assert configured.status_code == 200
    missing = await client.post(f"/v1/providers/{provider_id}/discover", json={})
    assert missing.json()["added"] == ["m3"]
    assert missing.json()["missing"] == ["m2"]
    assert missing.json()["status"] == "ok"
    listing = (await client.get(f"/v1/providers/{provider_id}/models")).json()
    assert listing["effective"][0]["display_name"] == "My name"
    assert any(item["model_id"] == "m2" and item["missing_since"] for item in listing["others"])
    reappeared = await client.post(f"/v1/providers/{provider_id}/discover", json={})
    assert reappeared.json()["reappeared"] == ["m2"]
