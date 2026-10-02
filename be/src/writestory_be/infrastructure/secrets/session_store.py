from __future__ import annotations

from typing import Any


class SessionSecretStore:
    """Secrets that intentionally live only for the current backend process."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    def get(self, ref: str) -> dict[str, Any] | None:
        return self._entries.get(ref)

    def put(self, ref: str, value: str, label: str | None = None) -> None:
        self._entries[ref] = {"value": value, "label": label}

    def delete(self, ref: str) -> None:
        self._entries.pop(ref, None)

    def refs(self) -> tuple[str, ...]:
        return tuple(self._entries)

    def clear(self) -> None:
        self._entries.clear()
