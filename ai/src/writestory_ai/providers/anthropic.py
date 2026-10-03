"""Anthropic Messages API streaming adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from pydantic import ValidationError

from writestory_ai.contracts.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderUnreachableError,
)
from writestory_ai.contracts.generation import (
    GenerationRequest,
    StreamDone,
    StreamEvent,
    TextDelta,
)
from writestory_ai.contracts.models import ProviderModel
from writestory_ai.contracts.usage import Usage

_API_VERSION = "2023-06-01"
_DEFAULT_BASE_URL = "https://api.anthropic.com"
_MAX_MODEL_PAGES = 20
_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def _messages_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/messages"
    return f"{root}/v1/messages"


def _models_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/models"
    return f"{root}/v1/models"


def _model_bad_response(message: str = "Anthropic returned malformed model data"):
    return ProviderUnreachableError(message, detail={"reason": "bad_response"})


def _anthropic_model(raw: Any) -> ProviderModel:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise _model_bad_response()
    capabilities = raw.get("capabilities")
    efforts: list[str] | None = None
    if isinstance(capabilities, dict) and isinstance(capabilities.get("effort"), dict):
        effort = capabilities["effort"]
        if effort.get("supported") is False:
            efforts = []
        elif effort.get("supported") is True:
            efforts = [
                level
                for level in _EFFORT_LEVELS
                if isinstance(effort.get(level), dict) and effort[level].get("supported") is True
            ]
    try:
        return ProviderModel(
            id=raw["id"],
            display_name=raw.get("display_name"),
            max_input_tokens=raw.get("max_input_tokens"),
            max_tokens=raw.get("max_tokens"),
            supported_efforts=efforts,
            capabilities=capabilities if isinstance(capabilities, dict) else None,
        )
    except ValidationError as exc:
        raise _model_bad_response() from exc


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
        except TypeError, ValueError, OverflowError:
            return None


def _http_error(response: httpx.Response) -> Exception:
    status = response.status_code
    if status in (401, 403):
        return ProviderAuthError(f"Anthropic API returned HTTP {status}")
    if status == 429:
        return ProviderRateLimitError(
            "Anthropic API rate limit",
            retry_after=_retry_after(response.headers.get("retry-after")),
        )
    if status >= 500:
        return ProviderServerError(f"Anthropic API returned HTTP {status}")
    reason = "endpoint_not_found" if status == 404 else "bad_response"
    return ProviderUnreachableError(
        f"Anthropic API returned HTTP {status}", detail={"reason": reason, "http_status": status}
    )


class AnthropicTextProvider:
    """Streams text deltas and usage from the Messages API."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._url = _messages_url(base_url)
        self._timeout = timeout
        self._transport = transport

    async def list_models(self, *, limit: int = 1000) -> list[ProviderModel]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        headers = {"x-api-key": self._api_key, "anthropic-version": _API_VERSION}
        models: list[ProviderModel] = []
        seen: set[str] = set()
        after_id: str | None = None
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self._timeout
            ) as client:
                for _page in range(_MAX_MODEL_PAGES):
                    params = {"limit": limit}
                    if after_id is not None:
                        params["after_id"] = after_id
                    response = await client.get(
                        _models_url(self._base_url), headers=headers, params=params
                    )
                    if response.is_error:
                        raise _http_error(response)
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise _model_bad_response() from exc
                    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                        raise _model_bad_response()
                    page_models = [_anthropic_model(raw) for raw in payload["data"]]
                    for model in page_models:
                        if model.id not in seen:
                            seen.add(model.id)
                            models.append(model)
                    if payload.get("has_more") is not True:
                        return models
                    if not page_models:
                        raise _model_bad_response("Anthropic pagination returned an empty page")
                    after_id = page_models[-1].id
        except httpx.TimeoutException as exc:
            raise ProviderUnreachableError(
                "Anthropic model discovery timed out", detail={"reason": "timeout"}
            ) from exc
        except httpx.TransportError as exc:
            raise ProviderUnreachableError(
                "Anthropic model discovery connection failed", detail={"reason": "connection"}
            ) from exc
        raise _model_bad_response("Anthropic model discovery exceeded 20 pages")

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamEvent]:
        body: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.system is not None:
            body["system"] = request.system
        output_config: dict[str, Any] = {}
        if request.effort is not None:
            output_config["effort"] = request.effort
        if request.response_schema is not None:
            output_config["format"] = {
                "type": "json_schema",
                "schema": request.response_schema,
            }
        if output_config:
            body["output_config"] = output_config

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        input_tokens = output_tokens = cache_read = cache_write = 0
        usage_reported = False
        stop_reason: str | None = None
        data_lines: list[str] = []

        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self._timeout
            ) as client:
                async with client.stream("POST", self._url, headers=headers, json=body) as response:
                    if response.is_error:
                        raise _http_error(response)
                    if "text/event-stream" not in response.headers.get("content-type", ""):
                        raise ProviderUnreachableError(
                            "Anthropic response was not an event stream",
                            detail={"reason": "bad_response"},
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_lines.append(line[5:].lstrip())
                            continue
                        if line or not data_lines:
                            continue
                        event_data = "\n".join(data_lines)
                        data_lines.clear()
                        if event_data == "[DONE]":
                            break
                        try:
                            event = json.loads(event_data)
                        except json.JSONDecodeError as exc:
                            raise ProviderUnreachableError(
                                "Anthropic returned malformed stream data",
                                detail={"reason": "bad_response"},
                            ) from exc

                        event_type = event.get("type")
                        if event_type == "message_start":
                            usage = event.get("message", {}).get("usage", {})
                            if isinstance(usage, dict):
                                usage_reported = True
                                input_tokens = int(usage.get("input_tokens", 0) or 0)
                                cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
                                cache_write = int(usage.get("cache_creation_input_tokens", 0) or 0)
                        elif event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta" and isinstance(
                                delta.get("text"), str
                            ):
                                yield TextDelta(text=delta["text"])
                        elif event_type == "message_delta":
                            delta = event.get("delta", {})
                            reason = delta.get("stop_reason")
                            if isinstance(reason, str):
                                stop_reason = reason
                            usage = event.get("usage", {})
                            if isinstance(usage, dict) and "output_tokens" in usage:
                                usage_reported = True
                                output_tokens = int(usage.get("output_tokens", 0) or 0)
                        elif event_type == "error":
                            raise ProviderUnreachableError(
                                "Anthropic stream ended with an error",
                                detail={"reason": "stream_error"},
                            )
        except httpx.TimeoutException as exc:
            raise ProviderUnreachableError(
                "Anthropic request timed out", detail={"reason": "timeout"}
            ) from exc
        except httpx.TransportError as exc:
            raise ProviderUnreachableError(
                "Anthropic connection failed", detail={"reason": "connection"}
            ) from exc

        normalized_reason = {
            "max_tokens": "max_tokens",
            "refusal": "refusal",
        }.get(stop_reason, "end_turn")
        yield StreamDone(
            stop_reason=normalized_reason,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                reported=usage_reported,
            ),
        )
