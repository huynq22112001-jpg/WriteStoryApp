import json
import sqlite3

import pytest

from writestory_be.bootstrap.context import Runtime
from writestory_be.main import create_app


def _init_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL, "
            "revision INTEGER NOT NULL, updated_at TEXT NOT NULL)"
        )
        connection.execute("CREATE TABLE works (id TEXT PRIMARY KEY)")


@pytest.mark.asyncio
async def test_onboarding_pending_step_revision_and_persistence(
    client, runtime, anon_client_factory
):
    db_path = runtime.data_root / "db" / "app.sqlite3"
    _init_db(db_path)

    initial = await client.get("/v1/onboarding")
    assert initial.status_code == 200
    assert initial.json()["status"] == "pending"
    assert initial.json()["steps"]["first_work"] == "pending"
    assert initial.json()["revision"] == 1

    updated = await client.put("/v1/onboarding", json={"step": "provider", "expected_revision": 1})
    assert updated.status_code == 200
    assert updated.json()["step"] == "provider"
    assert updated.json()["revision"] == 2
    stale = await client.put("/v1/onboarding", json={"step": "first_work", "expected_revision": 1})
    assert stale.status_code == 409

    restarted = Runtime(config=runtime.config)
    async with anon_client_factory(create_app(restarted)) as fresh_client:
        fresh_client.headers["Authorization"] = "Bearer test-token"
        persisted = await fresh_client.get("/v1/onboarding")
    assert persisted.json()["step"] == "provider"
    assert persisted.json()["revision"] == 2

    completed = await client.post("/v1/onboarding/complete", json={"skipped": True})
    assert completed.json()["status"] == "skipped"
    assert completed.json()["completed_at"]
    with sqlite3.connect(db_path) as connection:
        stored = json.loads(
            connection.execute(
                "SELECT value_json FROM settings WHERE key='onboarding.state'"
            ).fetchone()[0]
        )
    assert stored["status"] == "skipped"


@pytest.mark.asyncio
async def test_get_onboarding_auto_completes_when_work_exists(client, runtime):
    db_path = runtime.data_root / "db" / "app.sqlite3"
    _init_db(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO works(id) VALUES('work-1')")

    response = await client.get("/v1/onboarding")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["step"] is None
    assert response.json()["steps"]["first_work"] == "done"
    assert response.json()["completed_at"]
