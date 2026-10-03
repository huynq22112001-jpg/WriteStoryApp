from __future__ import annotations

from typing import Any, Protocol


class Permit(Protocol):
    """A provider request permit held for one request."""


class ProviderLimiterPort(Protocol):
    """Boundary implemented by BE; the AI package stays independent of persistence."""

    async def acquire(
        self,
        provider_id: str,
        model_id: str,
        *,
        est_input_tokens: int = 0,
        max_tokens: int = 0,
    ) -> Permit: ...

    async def release(self, permit: Permit, usage: Any | None = None) -> None: ...

    async def report(
        self, provider_id: str, outcome: str, retry_after_s: float | None = None
    ) -> None: ...
