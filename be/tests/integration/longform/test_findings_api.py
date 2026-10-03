import asyncio

import pytest

from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.longform_generation import Finding


@pytest.fixture
async def longform_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_findings_resolve_and_deterministic_finding_cannot_be_dismissed(
    client, runtime, longform_db
):
    work = await client.post(
        "/v1/works", headers={"Idempotency-Key": "findings-work-001"}, json={"title": "Findings"}
    )
    work_id = work.json()["id"]
    chapter = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Chương 1"})
    chapter_id = chapter.json()["id"]
    created = await client.post(
        f"/v1/chapters/{chapter_id}/findings",
        json={"kind": "craft", "severity": "minor", "message": "Xem lại nhịp đoạn."},
    )
    assert created.status_code == 200
    finding_id = created.json()["id"]
    listed = await client.get(f"/v1/works/{work_id}/findings", params={"status": "open"})
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == finding_id
    assert (
        await client.post(f"/v1/findings/{finding_id}/resolve", json={"note": "Đã sửa"})
    ).json()["status"] == "resolved"

    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            Finding(
                id=new_id(),
                work_id=work_id,
                chapter_id=chapter_id,
                chapter_no=1,
                source="validator",
                kind="fact",
                severity="blocker",
                message="State sai",
                evidence="[]",
                evidence_status="verified",
                refs="[]",
                params="{}",
                status="open",
                created_at="2026-10-03T00:00:00Z",
            )
        )
        await session.commit()
    async with runtime.ensure_database_services().read_sessions() as session:
        from sqlalchemy import select

        deterministic = await session.scalar(select(Finding).where(Finding.source == "validator"))
        deterministic_id = deterministic.id
    rejected = await client.post(
        f"/v1/findings/{deterministic_id}/dismiss", json={"note": "bỏ qua"}
    )
    assert rejected.status_code == 422
    resolved = await client.post(
        f"/v1/findings/{deterministic_id}/resolve", json={"note": "đã xử lý"}
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
