from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from writestory_be.core.clock import utcnow_iso


@dataclass
class VaultSettingsState:
    mode: str = "undecided"
    revision: int = 1
    index: dict[str, dict] | None = None

    def __post_init__(self) -> None:
        if self.index is None:
            self.index = {}


class VaultSettingsStore:
    """Persist only vault mode and non-secret index metadata in F02 settings."""

    def __init__(self, db_path: Path, memory_state: VaultSettingsState | None = None) -> None:
        self.db_path = db_path
        self.memory_state = memory_state or VaultSettingsState()

    async def read(self) -> VaultSettingsState:
        return await asyncio.to_thread(self._read)

    async def waiting_jobs(self) -> int:
        return await asyncio.to_thread(self._waiting_jobs)

    def _waiting_jobs(self) -> int:
        if not self.db_path.is_file():
            return 0
        try:
            with sqlite3.connect(self.db_path) as connection:
                return int(
                    connection.execute(
                        "SELECT count(*) FROM jobs "
                        "WHERE status='waiting_slot' AND wait_reason='VAULT_LOCKED'"
                    ).fetchone()[0]
                )
        except sqlite3.Error:
            return 0

    def _read(self) -> VaultSettingsState:
        if not self.db_path.is_file():
            return self.memory_state
        try:
            with sqlite3.connect(self.db_path) as connection:
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'"
                ).fetchone()
                if not exists:
                    return self.memory_state
                rows = dict(connection.execute(
                    "SELECT key, value_json FROM settings WHERE key IN (?, ?)",
                    ("vault.mode", "secrets.index"),
                ).fetchall())
                mode_row = connection.execute(
                    "SELECT revision FROM settings WHERE key=?", ("vault.mode",)
                ).fetchone()
                mode = json.loads(rows.get("vault.mode", '"undecided"'))
                index = json.loads(rows.get("secrets.index", "{}"))
                if not isinstance(mode, str) or mode not in {"undecided", "vault", "session_only"}:
                    mode = "undecided"
                if not isinstance(index, dict):
                    index = {}
                state = VaultSettingsState(mode, int(mode_row[0]) if mode_row else 1, index)
                self.memory_state = state
                return state
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError):
            return self.memory_state

    async def set_mode(self, mode: str, expected_revision: int) -> bool:
        return await asyncio.to_thread(self._set_mode, mode, expected_revision)

    def _set_mode(self, mode: str, expected_revision: int) -> bool:
        if not self._has_settings_table():
            state = self.memory_state
            if expected_revision != state.revision:
                return False
            state.mode = mode
            state.revision += 1
            return True
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT value_json, revision FROM settings WHERE key='vault.mode'"
            ).fetchone()
            current_revision = int(row[1]) if row else 1
            if current_revision != expected_revision:
                connection.rollback()
                return False
            self._upsert(connection, "vault.mode", json.dumps(mode), current_revision + 1)
            connection.commit()
        self.memory_state.mode = mode
        self.memory_state.revision = current_revision + 1
        return True

    async def set_index(self, index: dict[str, dict]) -> None:
        await asyncio.to_thread(self._set_index, index)

    def _set_index(self, index: dict[str, dict]) -> None:
        serialized = json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if self._has_settings_table():
            with sqlite3.connect(self.db_path) as connection:
                row = connection.execute(
                    "SELECT revision FROM settings WHERE key='secrets.index'"
                ).fetchone()
                self._upsert(connection, "secrets.index", serialized, int(row[0]) + 1 if row else 1)
                connection.commit()
        self.memory_state.index = index

    async def set_mode_value(self, mode: str) -> None:
        state = await self.read()
        if self._has_settings_table():
            await asyncio.to_thread(
                self._set_mode_unchecked, mode, state.revision + 1
            )
        self.memory_state.mode = mode
        self.memory_state.revision = state.revision + 1

    def _set_mode_unchecked(self, mode: str, revision: int) -> None:
        with sqlite3.connect(self.db_path) as connection:
            self._upsert(connection, "vault.mode", json.dumps(mode), revision)
            connection.commit()

    def _has_settings_table(self) -> bool:
        if not self.db_path.is_file():
            return False
        try:
            with sqlite3.connect(self.db_path) as connection:
                return connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'"
                ).fetchone() is not None
        except sqlite3.Error:
            return False

    @staticmethod
    def _upsert(connection: sqlite3.Connection, key: str, value: str, revision: int) -> None:
        connection.execute(
            "INSERT INTO settings(key,value_json,revision,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, "
            "revision=excluded.revision, updated_at=excluded.updated_at",
            (key, value, revision, utcnow_iso()),
        )
