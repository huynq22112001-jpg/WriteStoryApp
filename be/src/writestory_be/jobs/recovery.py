from __future__ import annotations

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from writestory_be.core.clock import utcnow_iso
from writestory_be.infrastructure.db.engine import create_engine, database_path
from writestory_be.infrastructure.db.models.system import Job, JobStep, WorkLock
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue

Reconciler = Callable[[Any, Path], Awaitable[dict[str, Any] | None]]
_reconcilers: list[tuple[int, str, Reconciler]] = []


def register_reconciler(name: str, fn: Reconciler, order: int = 100) -> None:
    if any(existing_name == name for _, existing_name, _ in _reconcilers):
        raise ValueError(f"Reconciler đã đăng ký: {name}")
    _reconcilers.append((order, name, fn))
    _reconcilers.sort(key=lambda item: (item[0], item[1]))


async def _core_reconciler(ctx, data_root: Path) -> dict[str, Any]:
    jobs = list(
        (
            await ctx.session.scalars(
                select(Job).where(Job.status == "running").order_by(Job.created_at, Job.id)
            )
        ).all()
    )
    now = utcnow_iso()
    for job in jobs:
        job.status = "interrupted"
        job.interrupted_at = now
        job.updated_at = now
        job.revision += 1
    await ctx.session.execute(
        update(JobStep)
        .where(JobStep.status == "running")
        .values(status="interrupted", finished_at=now)
    )
    await ctx.session.execute(delete(WorkLock))
    return {"count": len(jobs), "job_ids": [job.id for job in jobs[:50]]}


register_reconciler("core", _core_reconciler, order=0)


@dataclass(frozen=True)
class ReconcileResult:
    interrupted_count: int
    interrupted_job_ids: list[str]


async def _run_reconcilers(data_root: Path, uow: UnitOfWork) -> ReconcileResult:
    aggregate = {"count": 0, "job_ids": []}

    async def reconcile(ctx):
        for _, _, fn in _reconcilers:
            result = await fn(ctx, data_root)
            if result:
                aggregate["count"] += int(result.get("count", 0))
                aggregate["job_ids"].extend(result.get("job_ids", []))

    await uow.write(reconcile)
    return ReconcileResult(
        interrupted_count=aggregate["count"], interrupted_job_ids=aggregate["job_ids"][:50]
    )


async def _remove_temporary_files(root: Path) -> None:
    temp_root = root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    for child in temp_root.iterdir():
        if child.is_dir() and not child.is_symlink():
            await asyncio.to_thread(shutil.rmtree, child)
        else:
            child.unlink(missing_ok=True)


async def run_startup_reconcile(data_root: Path) -> ReconcileResult:
    """Recover interrupted jobs and clear ephemeral files before the API binds."""
    root = await asyncio.to_thread(lambda: data_root.expanduser().resolve())
    engine = create_engine(database_path(root))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)
    uow = UnitOfWork(sessions, writer)

    try:
        result = await _run_reconcilers(root, uow)
        await _remove_temporary_files(root)
        return result
    finally:
        await writer.close()
        await engine.dispose()
