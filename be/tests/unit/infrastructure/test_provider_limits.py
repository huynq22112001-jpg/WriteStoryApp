import asyncio
import time

import pytest

from writestory_be.infrastructure.ai.limits import ProviderLimiter


@pytest.mark.asyncio
async def test_provider_semaphore_caps_concurrent_permits():
    limiter = ProviderLimiter()
    await limiter.configure("cloud", max_concurrent_requests=2)
    active = 0
    peak = 0

    async def request():
        nonlocal active, peak
        permit = await limiter.acquire("cloud", "model")
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        await limiter.release(permit)

    await asyncio.gather(*(request() for _ in range(8)))
    assert peak == 2


@pytest.mark.asyncio
async def test_retry_after_cooldown_is_shared_by_provider():
    limiter = ProviderLimiter()
    await limiter.report("cloud", "rate_limited", 0.03)
    started = time.monotonic()
    permit = await limiter.acquire("cloud", "model")
    elapsed = time.monotonic() - started
    await limiter.release(permit)
    assert elapsed >= 0.02
