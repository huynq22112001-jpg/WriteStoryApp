"""Async Alembic environment. Database path is anchored at data-root."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import URL, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from writestory_be.infrastructure.db.base import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    root = config.attributes.get("data_root") or os.environ.get("WRITESTORY_DATA_ROOT")
    if root is None:
        raise RuntimeError("Alembic cần data_root (config.attributes['data_root'])")
    db_path = Path(root).expanduser().resolve() / "db" / "app.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return URL.create("sqlite+aiosqlite", database=str(db_path)).render_as_string(
        hide_password=False
    )


def include_object(obj, name, type_, reflected, compare_to):
    # FTS virtual tables and triggers are managed explicitly in SQL migrations.
    if type_ == "table" and name.startswith("search_") and name != "search_documents":
        return False
    return True


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        include_object=include_object,
        compare_type=True,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise RuntimeError("Offline migration không được hỗ trợ; cần data-root thực")
else:
    run_migrations_online()
