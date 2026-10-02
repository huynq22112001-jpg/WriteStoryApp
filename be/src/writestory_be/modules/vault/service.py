from __future__ import annotations

import time

from writestory_be.core.errors import AppError, ErrorCode


class VaultApiService:
    """Request-level policy shared by the vault API handlers."""

    def __init__(self, runtime) -> None:
        self.runtime = runtime

    def check_throttle(self) -> None:
        remaining = getattr(self.runtime, "vault_retry_at", 0.0) - time.monotonic()
        if remaining <= 0:
            return
        milliseconds = int(remaining * 1000)
        raise AppError(
            ErrorCode.VAULT_UNLOCK_THROTTLED,
            detail={"retry_after_ms": milliseconds},
            headers={"Retry-After": str(max(1, (milliseconds + 999) // 1000))},
        )

    def record_password_failure(self) -> None:
        failures = getattr(self.runtime, "vault_failures", 0) + 1
        self.runtime.vault_failures = failures
        if failures >= 3:
            self.runtime.vault_retry_at = time.monotonic() + min(2 ** (failures - 3), 30)

    def clear_password_failures(self) -> None:
        self.runtime.vault_failures = 0
        self.runtime.vault_retry_at = 0.0
