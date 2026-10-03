from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from writestory_ai.ports.limiter import Permit


@dataclass
class _Bucket:
    rate_per_second: float
    capacity: float
    tokens: float = field(init=False)
    updated_at: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        self.tokens = self.capacity

    def consume(self, amount: float, now: float) -> float:
        wait = self.wait_for(amount, now)
        if wait <= 0:
            self.tokens -= min(max(amount, 0), self.capacity)
        return wait

    def wait_for(self, amount: float, now: float) -> float:
        self.tokens = min(
            self.capacity, self.tokens + (now - self.updated_at) * self.rate_per_second
        )
        self.updated_at = now
        amount = min(max(amount, 0), self.capacity)
        if self.tokens >= amount:
            return 0
        return (amount - self.tokens) / self.rate_per_second if self.rate_per_second > 0 else 0


@dataclass
class _ProviderState:
    maximum: int = 4
    rpm: int | None = None
    tpm: int | None = None
    semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(4))
    request_bucket: _Bucket | None = None
    token_bucket: _Bucket | None = None
    cooldown_until: float = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class _Permit:
    def __init__(self, state: _ProviderState, provider_id: str, model_id: str):
        self.state = state
        self.provider_id = provider_id
        self.model_id = model_id
        self.released = False

    async def release(self, usage=None):
        if not self.released:
            self.released = True
            self.state.semaphore.release()


class ProviderLimiter:
    """Per-provider concurrency, RPM/TPM token buckets, and shared Retry-After cooldown."""

    def __init__(self):
        self._providers: dict[str, _ProviderState] = {}
        self._guard = asyncio.Lock()

    async def configure(self, provider_id: str, *, max_concurrent_requests=4, rpm=None, tpm=None):
        if max_concurrent_requests < 1:
            raise ValueError("max_concurrent_requests must be at least one")
        async with self._guard:
            state = self._providers.get(provider_id)
            if state is None:
                state = _ProviderState()
                self._providers[provider_id] = state
            state.maximum = max_concurrent_requests
            state.rpm = rpm
            state.tpm = tpm
            state.semaphore = asyncio.Semaphore(max_concurrent_requests)
            state.request_bucket = _Bucket(rpm / 60, max(1, rpm)) if rpm else None
            state.token_bucket = _Bucket(tpm / 60, max(1, tpm)) if tpm else None

    async def _state(self, provider_id: str):
        async with self._guard:
            return self._providers.setdefault(provider_id, _ProviderState())

    async def acquire(
        self, provider_id: str, model_id: str, *, est_input_tokens=0, max_tokens=0
    ) -> Permit:
        state = await self._state(provider_id)
        while True:
            wait = max(0.0, state.cooldown_until - time.monotonic())
            if wait:
                await asyncio.sleep(wait)
            async with state.lock:
                now = time.monotonic()
                cooldown = max(0.0, state.cooldown_until - now)
                rpm_wait = state.request_bucket.wait_for(1, now) if state.request_bucket else 0
                tpm_wait = (
                    state.token_bucket.wait_for(est_input_tokens + max_tokens, now)
                    if state.token_bucket
                    else 0
                )
                if not cooldown and not rpm_wait and not tpm_wait:
                    if state.request_bucket:
                        state.request_bucket.tokens -= 1
                    if state.token_bucket:
                        state.token_bucket.tokens -= min(
                            est_input_tokens + max_tokens, state.token_bucket.capacity
                        )
            wait = max(cooldown, rpm_wait, tpm_wait)
            if wait:
                await asyncio.sleep(wait)
                continue
            await state.semaphore.acquire()
            if state.cooldown_until > time.monotonic():
                state.semaphore.release()
                continue
            return _Permit(state, provider_id, model_id)

    async def release(self, permit: Permit, usage=None):
        release = getattr(permit, "release", None)
        if release:
            await release(usage)

    async def report(self, provider_id: str, outcome: str, retry_after_s: float | None = None):
        state = await self._state(provider_id)
        if outcome == "rate_limited" and retry_after_s is not None:
            state.cooldown_until = max(
                state.cooldown_until, time.monotonic() + max(0, retry_after_s)
            )
