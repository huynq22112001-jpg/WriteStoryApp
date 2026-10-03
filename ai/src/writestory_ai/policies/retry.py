from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from writestory_ai.contracts.errors import AIError

NON_RETRYABLE_CODES = frozenset({"PROVIDER_AUTH", "MODEL_NOT_FOUND", "CANCELLED"})


def is_retryable(error: BaseException, *, retry_model_not_found: bool = False) -> bool:
    """Classify provider failures without retrying permanent credential/model errors."""
    code = getattr(error, "code", None)
    if code in NON_RETRYABLE_CODES and not (retry_model_not_found and code == "MODEL_NOT_FOUND"):
        return False
    return isinstance(error, AIError) and error.retryable


def retry_after_seconds(error: BaseException) -> float | None:
    value = getattr(error, "retry_after", None)
    if value is None:
        value = getattr(error, "detail", {}).get("retry_after")
    try:
        parsed = float(value)
    except TypeError, ValueError:
        return None
    return max(0.0, parsed)


def retry_delay(
    attempt: int,
    error: BaseException,
    *,
    base: float = 2.0,
    maximum: float = 30.0,
    jitter: Callable[[], float] = random.random,
) -> float:
    """Return Retry-After when present, otherwise capped exponential backoff + jitter."""
    retry_after = retry_after_seconds(error)
    if retry_after is not None:
        return retry_after
    backoff = min(maximum, base * (2 ** max(0, attempt - 1)))
    return backoff * max(0.0, min(1.0, jitter()))


async def with_retries[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    on_retry: Callable[[BaseException, int, float], None] | None = None,
) -> T:
    """Run an async operation, retrying transient AI errors at most ``max_retries`` times."""
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as error:
            if attempt >= max_retries or not is_retryable(error):
                raise
            delay = retry_delay(attempt + 1, error)
            if on_retry:
                on_retry(error, attempt + 1, delay)
            await sleep(delay)
    raise AssertionError("unreachable")
