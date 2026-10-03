import pytest

from writestory_ai.contracts.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
)
from writestory_ai.contracts.generation import GenerationRequest
from writestory_ai.policies.retry import is_retryable, retry_delay, with_retries
from writestory_ai.providers.collect import collect
from writestory_ai.providers.mock import MockFailure, MockScenario, MockTextProvider


def test_retry_classification_and_retry_after():
    assert not is_retryable(ProviderAuthError("bad key"))
    assert is_retryable(ProviderServerError("server"))
    assert retry_delay(1, ProviderRateLimitError(retry_after=2)) == 2


def test_backoff_is_exponential_with_full_jitter_and_cap():
    error = ProviderServerError("temporary")
    assert retry_delay(3, error, jitter=lambda: 0.25) == 2.0
    assert retry_delay(8, error, jitter=lambda: 1.0) == 30.0


@pytest.mark.asyncio
async def test_retry_retries_transient_failure_up_to_success_without_real_sleep():
    attempts = 0
    sleeps = []

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ProviderServerError("try again")
        return "ok"

    async def sleep(seconds):
        sleeps.append(seconds)

    assert await with_retries(operation, sleep=sleep) == "ok"
    assert attempts == 3 and len(sleeps) == 2


@pytest.mark.asyncio
async def test_mock_provider_fail_sequence_can_be_retried():
    provider = MockTextProvider(
        MockScenario(
            fail_sequence=[MockFailure("server"), MockFailure("rate_limit", retry_after=0)],
            text="ok",
        )
    )

    async def operation():
        return await collect(provider, GenerationRequest(model="mock", messages=[]))

    async def sleep(_seconds):
        return None

    result = await with_retries(operation, sleep=sleep)
    assert result.text == "ok" and provider.calls == 3
