from __future__ import annotations

import threading

from writestory_be.bootstrap.logging_setup import register_secret


def register(value: str) -> None:
    """Make a secret available to the process-wide logging redaction filter."""
    register_secret(value)


class SecretRedactor:
    """Small facade kept injectable for callers that do not need logging internals."""

    def __init__(self) -> None:
        self._values: set[str] = set()
        self._lock = threading.Lock()

    def add(self, value: str) -> None:
        if not value:
            return
        with self._lock:
            self._values.add(value)
        register(value)

    def values(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._values)
