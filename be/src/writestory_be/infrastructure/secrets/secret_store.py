from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any

from writestory_be.infrastructure.secrets.redaction import SecretRedactor
from writestory_be.infrastructure.secrets.session_store import SessionSecretStore
from writestory_be.infrastructure.secrets.vault import VaultService

SECRET_REF_PATTERN = re.compile(r"^[a-z0-9_.:-]{1,128}$")


class VaultLockedError(PermissionError):
    code = "VAULT_LOCKED"


class SecretMissingError(LookupError):
    code = "SECRET_MISSING"


class SecretStore:
    """Resolve session secrets before encrypted vault entries."""

    def __init__(
        self,
        vault: VaultService,
        session: SessionSecretStore | None = None,
        *,
        redactor: SecretRedactor | None = None,
    ) -> None:
        self.vault = vault
        self.session = session or SessionSecretStore()
        self.redactor = redactor or SecretRedactor()
        self._vault_refs: set[str] = set()
        self._callbacks: list[Callable[[], Any]] = []

    def on_change(self, callback: Callable[[], Any]) -> None:
        self._callbacks.append(callback)

    def remember_vault_refs(self, refs: set[str]) -> None:
        self._vault_refs.update(refs)

    async def _changed(self) -> None:
        for callback in tuple(self._callbacks):
            result = callback()
            if inspect.isawaitable(result):
                await result

    async def availability(self, ref: str) -> str:
        if self.session.get(ref) is not None:
            return "session"
        if ref in self._vault_refs:
            return "vault" if self.vault.state == "unlocked" else "vault_locked"
        if self.vault.state == "unlocked" and await self.vault.get(ref) is not None:
            self._vault_refs.add(ref)
            return "vault"
        return "missing"

    async def get(self, ref: str) -> str:
        session_entry = self.session.get(ref)
        if session_entry is not None:
            return str(session_entry["value"])
        if ref in self._vault_refs and self.vault.state != "unlocked":
            raise VaultLockedError("Vault đang khóa")
        if self.vault.state == "unlocked":
            entry = await self.vault.get(ref)
            if entry is not None:
                self._vault_refs.add(ref)
                return str(entry["value"])
        raise SecretMissingError(ref)

    async def put(
        self, ref: str, value: str, storage: str, label: str | None = None
    ) -> None:
        if not SECRET_REF_PATTERN.fullmatch(ref):
            raise ValueError("secret_ref không hợp lệ")
        if storage == "session":
            self.session.put(ref, value, label)
        elif storage == "vault":
            if self.vault.state != "unlocked":
                raise VaultLockedError("Vault đang khóa")
            await self.vault.put(ref, value, label)
            self._vault_refs.add(ref)
        else:
            raise ValueError("storage phải là vault hoặc session")
        self.redactor.add(value)
        await self._changed()

    async def delete(self, ref: str) -> None:
        if self.session.get(ref) is not None:
            self.session.delete(ref)
        elif ref in self._vault_refs:
            if self.vault.state != "unlocked":
                raise VaultLockedError("Vault đang khóa")
            await self.vault.delete(ref)
            self._vault_refs.discard(ref)
        await self._changed()

    async def vault_unlocked(self) -> None:
        for ref in await self.vault.refs():
            entry = await self.vault.get(ref)
            if entry is not None:
                self._vault_refs.add(ref)
                self.redactor.add(str(entry["value"]))
        await self._changed()

    async def vault_locked(self) -> None:
        await self._changed()
