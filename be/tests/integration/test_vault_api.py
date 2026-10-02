import json
import sqlite3

import pytest

from writestory_be.bootstrap.context import Runtime
from writestory_be.main import create_app


@pytest.mark.asyncio
async def test_vault_lifecycle_and_secret_response_never_contains_value(client, runtime) -> None:
    created = await client.post(
        "/v1/vault",
        json={
            "password": "a sufficiently long password",
            "password_confirm": "a sufficiently long password",
        },
    )
    assert created.status_code == 201
    assert created.json()["state"] == "unlocked"

    secret = "sk-api-super-secret"
    stored = await client.put(
        "/v1/secrets/provider:test:api_key",
        json={"value": secret, "storage": "vault", "label": "Test"},
    )
    assert stored.status_code == 200
    assert secret not in stored.text

    locked = await client.post("/v1/vault/lock")
    assert locked.json()["state"] == "locked"
    wrong = await client.post("/v1/vault/unlock", json={"password": "wrong password"})
    assert wrong.status_code == 422
    assert wrong.json()["code"] == "VAULT_PASSWORD_INVALID"

    opened = await client.post(
        "/v1/vault/unlock", json={"password": "a sufficiently long password"}
    )
    assert opened.status_code == 200
    assert opened.json()["state"] == "unlocked"
    events = runtime.event_bus.replay(0)
    assert events and any(event.type == "vault.status" for event in events)


@pytest.mark.asyncio
async def test_vault_validation_error_does_not_echo_secret(client) -> None:
    secret = "sk-should-never-echo"
    response = await client.post(
        "/v1/vault",
        json={"password": secret, "password_confirm": "different", "import_session_secrets": True},
    )
    assert response.status_code == 422
    assert secret not in response.text


@pytest.mark.asyncio
async def test_mode_and_secret_index_persist_without_secret_values(
    client, runtime, anon_client_factory
) -> None:
    db_path = runtime.data_root / "db" / "app.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL, "
            "revision INTEGER NOT NULL, updated_at TEXT NOT NULL)"
        )

    created = await client.post(
        "/v1/vault",
        json={
            "password": "a sufficiently long password",
            "password_confirm": "a sufficiently long password",
        },
    )
    assert created.status_code == 201
    value = "sk-persistent-secret"
    stored = await client.put(
        "/v1/secrets/provider:persist:api_key",
        json={"value": value, "storage": "vault", "label": "Provider"},
    )
    assert stored.status_code == 200

    mode = await client.put(
        "/v1/vault/mode", json={"mode": "session_only", "expected_revision": 2}
    )
    assert mode.status_code == 200
    with sqlite3.connect(db_path) as connection:
        rows = dict(connection.execute("SELECT key, value_json FROM settings").fetchall())
    assert value not in json.dumps(rows)
    assert json.loads(rows["vault.mode"]) == "session_only"
    assert json.loads(rows["secrets.index"])["provider:persist:api_key"]["storage"] == "vault"

    restarted = Runtime(config=runtime.config)
    async with anon_client_factory(create_app(restarted)) as fresh_client:
        fresh_client.headers["Authorization"] = "Bearer test-token"
        listing = await fresh_client.get("/v1/secrets")
        assert listing.status_code == 200
        secret_info = listing.json()[0]
        assert secret_info["ref"] == "provider:persist:api_key"
        assert secret_info["storage"] == "vault"
        assert secret_info["available"] is False
        assert secret_info["label"] == "Provider"
        assert value not in listing.text


@pytest.mark.asyncio
async def test_reset_requires_idempotency_key_and_confirm_phrase(client) -> None:
    missing_key = await client.post("/v1/vault/reset", json={"confirm": "XÓA VAULT"})
    assert missing_key.status_code == 422
    response = await client.post(
        "/v1/vault/reset",
        headers={"Idempotency-Key": "reset-test"},
        json={"confirm": "sai"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unlock_throttle_and_vault_locked_error_codes(client) -> None:
    absent_secret = await client.put(
        "/v1/secrets/provider:missing:api_key",
        json={"value": "key", "storage": "vault"},
    )
    assert absent_secret.status_code == 422
    assert absent_secret.json()["detail"]["reason"] == "vault_absent"

    await client.post(
        "/v1/vault",
        json={
            "password": "a sufficiently long password",
            "password_confirm": "a sufficiently long password",
        },
    )
    await client.post("/v1/vault/lock")
    for _ in range(3):
        invalid = await client.post("/v1/vault/unlock", json={"password": "wrong password"})
        assert invalid.status_code == 422
    throttled = await client.post(
        "/v1/vault/unlock", json={"password": "a sufficiently long password"}
    )
    assert throttled.status_code == 429
    assert throttled.json()["code"] == "VAULT_UNLOCK_THROTTLED"
    assert throttled.headers["Retry-After"]

