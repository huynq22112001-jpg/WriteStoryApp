import json

import httpx
import pytest

from writestory_ai.contracts.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderUnreachableError,
)
from writestory_ai.contracts.generation import GenerationRequest, Message, StreamDone, TextDelta
from writestory_ai.providers.anthropic import AnthropicTextProvider


def _sse(*events: dict) -> bytes:
    return "\n\n".join(f"data: {json.dumps(event)}" for event in events).encode() + b"\n\n"


def _request(*, effort="high") -> GenerationRequest:
    return GenerationRequest(
        model="claude-test",
        messages=[Message(role="user", content="Viết tiếp")],
        system="Bạn là tác giả.",
        max_tokens=321,
        effort=effort,
    )


async def test_anthropic_stream_maps_text_stop_reason_usage_and_effort():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(
                {
                    "type": "message_start",
                    "message": {
                        "usage": {
                            "input_tokens": 13,
                            "cache_read_input_tokens": 5,
                            "cache_creation_input_tokens": 2,
                        }
                    },
                },
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Chào "}},
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "bạn"}},
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "max_tokens"},
                    "usage": {"output_tokens": 9},
                },
            ),
        )

    provider = AnthropicTextProvider(
        "test-secret", base_url="https://api.example/v1/", transport=httpx.MockTransport(handler)
    )
    events = [event async for event in provider.stream(_request())]
    assert captured["url"] == "https://api.example/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-secret"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["json"]["output_config"] == {"effort": "high"}
    assert captured["json"]["system"] == "Bạn là tác giả."
    assert captured["json"]["stream"] is True
    assert [event.text for event in events if isinstance(event, TextDelta)] == ["Chào ", "bạn"]
    done = events[-1]
    assert isinstance(done, StreamDone)
    assert done.stop_reason == "max_tokens"
    assert done.usage.input_tokens == 13
    assert done.usage.output_tokens == 9
    assert done.usage.cache_read_tokens == 5
    assert done.usage.cache_write_tokens == 2
    assert done.usage.reported is True


async def test_anthropic_does_not_send_empty_effort_and_maps_refusal():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(
                {"type": "message_delta", "delta": {"stop_reason": "refusal"}, "usage": {}}
            ),
        )

    provider = AnthropicTextProvider("key", transport=httpx.MockTransport(handler))
    events = [event async for event in provider.stream(_request(effort=None))]
    assert "output_config" not in captured["json"]
    assert events[-1].stop_reason == "refusal"


@pytest.mark.parametrize(
    ("status", "headers", "error_type", "code"),
    [
        (401, {}, ProviderAuthError, "PROVIDER_AUTH"),
        (403, {}, ProviderAuthError, "PROVIDER_AUTH"),
        (404, {}, ProviderUnreachableError, "PROVIDER_UNREACHABLE"),
        (429, {"retry-after": "2.5"}, ProviderRateLimitError, "PROVIDER_RATE_LIMIT"),
        (503, {}, ProviderServerError, "PROVIDER_SERVER_ERROR"),
    ],
)
async def test_anthropic_maps_http_errors(status, headers, error_type, code):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers=headers, json={"error": "ignored"})

    provider = AnthropicTextProvider("key", transport=httpx.MockTransport(handler))
    with pytest.raises(error_type) as caught:
        _ = [event async for event in provider.stream(_request())]
    assert caught.value.code == code
    if status == 429:
        assert caught.value.retry_after == 2.5
    if status == 404:
        assert caught.value.detail["reason"] == "endpoint_not_found"


async def test_anthropic_maps_malformed_sse():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b"data: {not-json}\n\n",
        )

    provider = AnthropicTextProvider("key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderUnreachableError) as caught:
        _ = [event async for event in provider.stream(_request())]
    assert caught.value.detail["reason"] == "bad_response"
