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
from writestory_ai.providers.openai_compatible import (
    OllamaTextProvider,
    OpenAICompatibleTextProvider,
)


def _sse(*events: dict | str) -> bytes:
    lines = []
    for event in events:
        data = event if isinstance(event, str) else json.dumps(event)
        lines.append(f"data: {data}\n\n")
    return "".join(lines).encode()


def _request(effort="high") -> GenerationRequest:
    return GenerationRequest(
        model="gpt-test",
        messages=[Message(role="user", content="Tiếp tục")],
        system="Viết tiếng Việt.",
        max_tokens=512,
        effort=effort,
    )


async def test_openai_compatible_stream_maps_delta_usage_finish_reason_and_effort():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(
                {"choices": [{"delta": {"content": "Xin "}, "finish_reason": None}]},
                {"choices": [{"delta": {"content": "chào"}, "finish_reason": None}]},
                {
                    "choices": [{"delta": {}, "finish_reason": "length"}],
                    "usage": {
                        "prompt_tokens": 20,
                        "completion_tokens": 7,
                        "prompt_tokens_details": {"cached_tokens": 4},
                    },
                },
                "[DONE]",
            ),
        )

    provider = OpenAICompatibleTextProvider(
        base_url="https://api.example/v1/",
        api_key="secret",
        supported_efforts={"gpt-test": {"high"}},
        transport=httpx.MockTransport(handler),
    )
    events = [event async for event in provider.stream(_request())]
    assert captured["url"] == "https://api.example/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert captured["json"]["messages"][0] == {
        "role": "system",
        "content": "Viết tiếng Việt.",
    }
    assert captured["json"]["reasoning_effort"] == "high"
    assert captured["json"]["stream_options"] == {"include_usage": True}
    assert [event.text for event in events if isinstance(event, TextDelta)] == ["Xin ", "chào"]
    done = events[-1]
    assert isinstance(done, StreamDone)
    assert done.stop_reason == "max_tokens"
    assert done.usage.input_tokens == 20
    assert done.usage.output_tokens == 7
    assert done.usage.cache_read_tokens == 4
    assert done.usage.reported is True


async def test_openai_effort_is_dropped_when_model_support_is_unknown():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
        )

    provider = OpenAICompatibleTextProvider(
        base_url="https://api.example", transport=httpx.MockTransport(handler)
    )
    done = [event async for event in provider.stream(_request())][-1]
    assert "reasoning_effort" not in captured["json"]
    assert done.usage.reported is False


async def test_ollama_uses_openai_endpoint_without_auth_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse({"choices": [{"delta": {"content": "local"}, "finish_reason": "stop"}]}),
        )

    provider = OllamaTextProvider(transport=httpx.MockTransport(handler))
    events = [event async for event in provider.stream(_request())]
    assert provider.name == "ollama_lmstudio"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert "authorization" not in captured["headers"]
    assert any(isinstance(event, TextDelta) and event.text == "local" for event in events)


@pytest.mark.parametrize(
    ("status", "headers", "error_type", "code"),
    [
        (401, {}, ProviderAuthError, "PROVIDER_AUTH"),
        (403, {}, ProviderAuthError, "PROVIDER_AUTH"),
        (404, {}, ProviderUnreachableError, "PROVIDER_UNREACHABLE"),
        (429, {"retry-after": "3"}, ProviderRateLimitError, "PROVIDER_RATE_LIMIT"),
        (500, {}, ProviderServerError, "PROVIDER_SERVER_ERROR"),
    ],
)
async def test_openai_compatible_maps_http_errors(status, headers, error_type, code):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers=headers, json={"error": "redacted"})

    provider = OpenAICompatibleTextProvider(
        base_url="https://api.example", api_key="secret", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(error_type) as caught:
        _ = [event async for event in provider.stream(_request())]
    assert caught.value.code == code
    if status == 429:
        assert caught.value.retry_after == 3.0
    if status == 404:
        assert caught.value.detail["reason"] == "endpoint_not_found"
