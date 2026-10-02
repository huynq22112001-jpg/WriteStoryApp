from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select, text, tuple_
from sqlalchemy.ext.asyncio import async_sessionmaker

from writestory_be.core.clock import to_iso, utcnow
from writestory_be.infrastructure.db.engine import create_engine, database_path
from writestory_be.infrastructure.db.models.system import IdempotencyRecord, JobEvent
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue

RETENTION_DAYS = 90
DELETE_BATCH = 1000
log = logging.getLogger(__name__)


async def run_retention_once(data_root: Path) -> dict[str, int]:
    root = await asyncio.to_thread(lambda: data_root.expanduser().resolve())
    engine = create_engine(database_path(root))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)
    uow = UnitOfWork(sessions, writer)
    cutoff = to_iso(utcnow() - timedelta(days=RETENTION_DAYS))
    now = to_iso(utcnow())
    totals = {"job_events": 0, "idempotency_records": 0}

    async def clean_batch(ctx):
        event_ids = (
            select(JobEvent.seq)
            .where(JobEvent.ts < cutoff)
            .order_by(JobEvent.seq)
            .limit(DELETE_BATCH)
        )
        idem_keys = (
            select(
                IdempotencyRecord.key,
                IdempotencyRecord.method,
                IdempotencyRecord.path,
            )
            .where(IdempotencyRecord.expires_at < now)
            .order_by(IdempotencyRecord.expires_at)
            .limit(DELETE_BATCH)
        )
        event_result = await ctx.session.execute(
            delete(JobEvent).where(JobEvent.seq.in_(event_ids))
        )
        idem_result = await ctx.session.execute(
            delete(IdempotencyRecord).where(
                tuple_(
                    IdempotencyRecord.key,
                    IdempotencyRecord.method,
                    IdempotencyRecord.path,
                ).in_(idem_keys)
            )
        )
        return event_result.rowcount or 0, idem_result.rowcount or 0

    try:
        while True:
            removed = await uow.write(clean_batch)
            totals["job_events"] += removed[0]
            totals["idempotency_records"] += removed[1]
            if removed == (0, 0):
                break
        backups = sorted(
            (root / "backups" / "pre-migrate").glob("*.sqlite3"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old in backups[3:]:
            old.unlink(missing_ok=True)
        async with engine.connect() as connection:
            await connection.execute(text("PRAGMA wal_checkpoint(PASSIVE)"))
        return totals
    finally:
        await writer.close()
        await engine.dispose()


async def retention_loop(data_root: Path) -> None:
    await asyncio.sleep(60)
    while True:
        try:
            await run_retention_once(data_root)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Maintenance errors are diagnostic only; the next scheduled pass retries.
            log.exception("DB retention pass failed")
        await asyncio.sleep(24 * 60 * 60)
