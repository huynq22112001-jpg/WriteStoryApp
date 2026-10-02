"""Prepare and safely upgrade the user's SQLite database before serving requests."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from writestory_be.jobs.recovery import run_startup_reconcile


class DatabaseStartupError(RuntimeError):
    def __init__(self, code: str, message: str, detail: dict | None = None) -> None:
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


def _alembic_config(data_root: Path) -> Config:
    project_root = Path(__file__).resolve().parents[4]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.attributes["data_root"] = data_root
    return config


def _current_revision(database: Path) -> str | None:
    if not database.exists():
        return None
    with sqlite3.connect(database) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchone()
        if not exists:
            return None
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None


def _write_marker(marker_path: Path, data_id: str | None) -> None:
    marker = {}
    if marker_path.exists():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            marker = {}
    marker.setdefault("layout_version", 1)
    marker.setdefault("data_id", data_id)
    marker.setdefault("created_at", datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    marker.setdefault("created_by_app_version", "0.1.0")
    marker["db_initialized"] = True
    temp = marker_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(marker_path)


def _backup_database(database: Path, backup_root: Path, from_revision: str, head: str) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    name = f"{stamp}_{from_revision}_to_{head}.sqlite3"
    final_path = backup_root / name
    temp_path = final_path.with_suffix(final_path.suffix + ".tmp")
    with sqlite3.connect(database) as connection:
        escaped = str(temp_path.resolve()).replace("'", "''")
        connection.execute(f"VACUUM INTO '{escaped}'")
    temp_path.replace(final_path)
    backups = sorted(
        backup_root.glob("*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True
    )
    for old in backups[3:]:
        old.unlink(missing_ok=True)
    return final_path


def prepare_database(
    data_root: Path,
    progress_cb: Callable[[str], None] | None = None,
    *,
    data_id: str | None = None,
    reconcile_cb: Callable[[object], None] | None = None,
) -> str:
    root = data_root.expanduser().resolve()
    database = root / "db" / "app.sqlite3"
    marker = root / ".writestory-data.json"
    if marker.exists():
        try:
            marked_initialized = json.loads(marker.read_text(encoding="utf-8")).get(
                "db_initialized", False
            )
        except (OSError, json.JSONDecodeError):
            marked_initialized = False
        if marked_initialized and not database.is_file():
            raise DatabaseStartupError("DB_MISSING", "Data-root đã khởi tạo nhưng thiếu DB")

    database.parent.mkdir(parents=True, exist_ok=True)
    config = _alembic_config(root)
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if head is None:
        raise DatabaseStartupError("MIGRATION_FAILED", "Không tìm thấy migration head")
    current = _current_revision(database)
    if current is not None and current not in set(script.get_heads()):
        known_revisions = {revision.revision for revision in script.walk_revisions()}
        if current not in known_revisions:
            raise DatabaseStartupError(
                "SCHEMA_TOO_NEW", "Database được tạo bởi phiên bản mới hơn", {"revision": current}
            )

    backup_path = None
    if current != head and database.exists() and database.stat().st_size > 0:
        backup_path = _backup_database(
            database, root / "backups" / "pre-migrate", current or "base", head
        )
    if current != head:
        if progress_cb:
            progress_cb("migrating")
        try:
            command.upgrade(config, "head")
        except Exception as exc:
            raise DatabaseStartupError(
                "MIGRATION_FAILED",
                "Không thể cập nhật schema cơ sở dữ liệu",
                {
                    "from_revision": current,
                    "failed_revision": head,
                    "backup_path": str(backup_path) if backup_path else None,
                    "error": str(exc),
                },
            ) from exc
    _write_marker(marker, data_id)
    if progress_cb:
        progress_cb("reconciling")
    reconcile_result = asyncio.run(run_startup_reconcile(root))
    if reconcile_cb:
        reconcile_cb(reconcile_result)
    return head
