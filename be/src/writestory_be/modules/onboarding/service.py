from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

from writestory_be.core.clock import utcnow_iso
from writestory_be.modules.onboarding.schemas import OnboardingState, OnboardingSteps

_KEY = "onboarding.state"
_DEFAULT: dict[str, Any] = {"status": "pending", "step": "security", "completed_at": None}


class OnboardingService:
    """Persist onboarding progress in the shared F02 settings table."""

    def __init__(self, db_path: Path, vault_settings) -> None:
        self.db_path = db_path
        self.vault_settings = vault_settings

    async def get(self) -> OnboardingState:
        return await asyncio.to_thread(self._get)

    def _get(self) -> OnboardingState:
        with closing(self._connect()) as connection:
            if not self._has_table(connection, "settings"):
                state, revision = dict(_DEFAULT), 1
            else:
                row = connection.execute(
                    "SELECT value_json, revision FROM settings WHERE key=?", (_KEY,)
                ).fetchone()
                state, revision = (json.loads(row[0]), int(row[1])) if row else (dict(_DEFAULT), 1)
                if not isinstance(state, dict):
                    state = dict(_DEFAULT)
            works_exist = self._has_table(connection, "works")
            has_work = (
                works_exist
                and connection.execute("SELECT 1 FROM works LIMIT 1").fetchone() is not None
            )
            providers_exist = self._has_table(connection, "providers")
            has_provider = (
                providers_exist
                and connection.execute("SELECT 1 FROM providers LIMIT 1").fetchone() is not None
            )
            if state.get("status", "pending") == "pending" and has_work:
                state = {"status": "completed", "step": None, "completed_at": utcnow_iso()}
                revision += 1
                self._save(connection, state, revision)

        return OnboardingState(
            **state,
            revision=revision,
            steps=OnboardingSteps(
                data_root="done" if sys.platform == "darwin" else "not_applicable",
                security="done" if self._vault_mode() != "undecided" else "pending",
                provider=(
                    "done"
                    if has_provider
                    else "skipped"
                    if state.get("step") == "first_work" or state.get("status") == "skipped"
                    else "pending"
                ),
                first_work="done" if has_work else "pending",
            ),
            platform=sys.platform,
        )

    def _vault_mode(self) -> str:
        # VaultSettingsStore keeps its last read in memory and is the source of this setting.
        return self.vault_settings.memory_state.mode

    async def update_step(self, step: str, expected_revision: int) -> bool:
        return await asyncio.to_thread(self._update_step, step, expected_revision)

    def _update_step(self, step: str, expected_revision: int) -> bool:
        with closing(self._connect()) as connection:
            if not self._has_table(connection, "settings"):
                return False
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT value_json, revision FROM settings WHERE key=?", (_KEY,)
            ).fetchone()
            state, revision = (json.loads(row[0]), int(row[1])) if row else (dict(_DEFAULT), 1)
            if revision != expected_revision:
                connection.rollback()
                return False
            if state.get("status", "pending") != "pending":
                connection.rollback()
                return False
            state["step"] = step
            self._save(connection, state, revision + 1)
            return True

    async def complete(self, skipped: bool) -> None:
        await asyncio.to_thread(self._complete, skipped)

    def _complete(self, skipped: bool) -> None:
        with closing(self._connect()) as connection:
            if not self._has_table(connection, "settings"):
                return
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision FROM settings WHERE key=?", (_KEY,)
            ).fetchone()
            revision = int(row[0]) if row else 1
            state = {
                "status": "skipped" if skipped else "completed",
                "step": None,
                "completed_at": utcnow_iso(),
            }
            self._save(connection, state, revision + 1)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _has_table(connection: sqlite3.Connection, table: str) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            is not None
        )

    @staticmethod
    def _save(connection: sqlite3.Connection, state: dict[str, Any], revision: int) -> None:
        connection.execute(
            "INSERT INTO settings(key,value_json,revision,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, "
            "revision=excluded.revision, updated_at=excluded.updated_at",
            (_KEY, json.dumps(state, ensure_ascii=False, sort_keys=True), revision, utcnow_iso()),
        )
        connection.commit()
