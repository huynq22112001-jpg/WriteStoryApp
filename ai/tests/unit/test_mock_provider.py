import pytest

from writestory_ai.contracts.errors import (
    OutputEmptyError,
    ProviderRateLimitError,
    ProviderUnreachableError,
)
from writestory_ai.contracts.generation import GenerationRequest, Message, StreamDone, TextDelta
from writestory_ai.providers.collect import collect
from writestory_ai.providers.mock import MockFailure, MockScenario, MockTextProvider


def make_request() -> GenerationRequest:
    return GenerationRequest(model="mock", messages=[Message(role="user", content="Viết tiếp")])


async def test_streams_text_then_done():
    provider = MockTextProvider(MockScenario(text="Một hai ba bốn", chunk_chars=4))
    events = [e async for e in provider.stream(make_request())]
    assert all(isinstance(e, TextDelta) for e in events[:-1])
    assert isinstance(events[-1], StreamDone)
    assert "".join(e.text for e in events[:-1]) == "Một hai ba bốn"
    assert events[-1].stop_reason == "end_turn"


async def test_collect_returns_result_with_usage():
    result = await collect(MockTextProvider(), make_request())
    assert result.text.startswith("Mưa đêm")
    assert result.stop_reason == "end_turn"
    assert result.usage.output_tokens > 0


async def test_fail_sequence_then_success():
    provider = MockTextProvider(
        MockScenario(fail_sequence=[MockFailure("rate_limit", retry_after=2.0)])
    )
    with pytest.raises(ProviderRateLimitError) as exc:
        await collect(provider, make_request())
    assert exc.value.retry_after == 2.0
    assert exc.value.code == "PROVIDER_RATE_LIMIT"
    result = await collect(provider, make_request())
    assert result.stop_reason == "end_turn"


async def test_refusal_is_reported_not_raised():
    result = await collect(MockTextProvider(MockScenario(refusal=True)), make_request())
    assert result.stop_reason == "refusal"
    assert result.text == ""


async def test_truncation_sets_max_tokens():
    provider = MockTextProvider(MockScenario(text="abcdefghij", truncate_at_chars=4, chunk_chars=2))
    result = await collect(provider, make_request())
    assert result.text == "abcd"
    assert result.stop_reason == "max_tokens"


async def test_disconnect_mid_stream():
    scenario = MockScenario(text="x" * 40, chunk_chars=8, disconnect_after_chars=16)
    provider = MockTextProvider(scenario)
    with pytest.raises(ProviderUnreachableError):
        await collect(provider, make_request())


async def test_empty_output_raises():
    with pytest.raises(OutputEmptyError):
        await collect(MockTextProvider(MockScenario(text="   ")), make_request())
