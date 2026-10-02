"""Engine SQLite (Plan §5, F02 be.md).

Baseline ưu tiên độ bền: WAL + `synchronous=FULL` (Plan §5 đã kiểm chứng sqlite.org/wal.html).
Migration (Alembic) và writer queue thêm ở bước F02 (R1).
"""

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

BUSY_TIMEOUT_MS = 5000

PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}",
    "PRAGMA synchronous=FULL",
)


def database_path(data_root: Path) -> Path:
    return data_root / "db" / "app.sqlite3"


def create_engine(db_path: Path) -> AsyncEngine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")

    @event.listens_for(engine.sync_engine, "connect")
    def _apply_pragmas(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            for pragma in PRAGMAS:
                cursor.execute(pragma)
        finally:
            cursor.close()

    return engine
