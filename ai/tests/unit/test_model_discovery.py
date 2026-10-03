import json

import httpx
import pytest

from writestory_ai.contracts.errors import ProviderUnreachableError
from writestory_ai.providers.anthropic import AnthropicTextProvider
from writestory_ai.providers.openai_compatible import OpenAICompatibleTextProvider


async def test_anthropic_list_models_paginates_and_normalizes_effort_capabilities():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "claude-a",
                            "display_name": "Claude A",
                            "max_input_tokens": 120000,
                            "max_tokens": 8192,
                            "capabilities": {
                                "effort": {
                                    "supported": True,
                                    "low": {"supported": True},
                                    "medium": {"supported": False},
                                    "high": {"supported": True},
                                },
                                "structured_outputs": {"supported": True},
                            },
                        }
                    ],
                    "has_more": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "claude-b", "capabilities": {"effort": {"supported": False}}},
                    {"id": "claude-c"},
                ],
                "has_more": False,
            },
        )

    provider = AnthropicTextProvider(
        "key", base_url="https://api.example/v1/", transport=httpx.MockTransport(handler)
    )
    models = await provider.list_models()
    assert len(requests) == 2
    assert str(requests[0].url) == "https://api.example/v1/models?limit=1000"
    assert requests[0].headers["x-api-key"] == "key"
    assert requests[0].headers["anthropic-version"] == "2023-06-01"
    assert requests[1].url.params["after_id"] == "claude-a"
    assert requests[1].url.params["limit"] == "1000"
    assert [model.id for model in models] == ["claude-a", "claude-b", "claude-c"]
    assert models[0].display_name == "Claude A"
    assert models[0].max_input_tokens == 120000
    assert models[0].max_tokens == 8192
    assert models[0].supported_efforts == ["low", "high"]
    assert models[0].capabilities["structured_outputs"]["supported"] is True
    assert models[1].supported_efforts == []
    assert models[2].supported_efforts is None


async def test_anthropic_deduplicates_models_and_rejects_limit_above_1000():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"id": "same"}, {"id": "same", "display_name": "ignored"}],
                "has_more": False,
            },
        )

    provider = AnthropicTextProvider("key", transport=httpx.MockTransport(handler))
    models = await provider.list_models(limit=5)
    assert len(models) == 1
    assert models[0].display_name is None
    with pytest.raises(ValueError):
        await provider.list_models(limit=1001)


async def test_anthropic_model_discovery_stops_after_twenty_pages():
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"data": [{"id": f"m-{calls}"}], "has_more": True})

    provider = AnthropicTextProvider("key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderUnreachableError) as caught:
        await provider.list_models()
    assert caught.value.detail["reason"] == "bad_response"
    assert calls == 20


async def test_openai_compatible_list_models_reads_ids_and_gateway_extras():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "model-a",
                        "display_name": "Model A",
                        "max_input_tokens": 64000,
                        "max_tokens": 8192,
                    },
                    {"id": "model-b"},
                    {"id": "model-a", "display_name": "duplicate"},
                ]
            },
        )

    provider = OpenAICompatibleTextProvider(
        base_url="https://gateway.example/v1/",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    models = await provider.list_models()
    assert captured["url"] == "https://gateway.example/v1/models"
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert [(model.id, model.display_name) for model in models] == [
        ("model-a", "Model A"),
        ("model-b", None),
    ]
    assert models[0].max_input_tokens == 64000
    assert models[0].max_tokens == 8192


@pytest.mark.parametrize(
    "payload",
    [[], {"data": None}, {"models": []}, {"data": [{"name": "missing-id"}]}],
)
async def test_openai_compatible_rejects_malformed_model_payload(payload):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(payload))

    provider = OpenAICompatibleTextProvider(
        base_url="https://gateway.example", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderUnreachableError) as caught:
        await provider.list_models()
    assert caught.value.detail["reason"] == "bad_response"
