"""OpenAI Chat Completions compatible streaming adapter, including local gateways."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
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
    Effort,
    GenerationRequest,
    StreamDone,
    StreamEvent,
    TextDelta,
)
from writestory_ai.contracts.models import ProviderModel
from writestory_ai.contracts.usage import Usage


def _chat_completions_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/chat/completions"
    return f"{root}/v1/chat/completions"


def _models_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/models"
    return f"{root}/v1/models"


def _model_bad_response() -> ProviderUnreachableError:
    return ProviderUnreachableError(
        "OpenAI-compatible API returned malformed model data", detail={"reason": "bad_response"}
    )


def _compatible_model(raw: Any) -> ProviderModel:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise _model_bad_response()
    try:
        return ProviderModel(
            id=raw["id"],
            display_name=raw.get("display_name"),
            max_input_tokens=raw.get("max_input_tokens"),
            max_tokens=raw.get("max_tokens"),
            supported_efforts=raw.get("supported_efforts"),
            capabilities=(
                raw.get("capabilities") if isinstance(raw.get("capabilities"), dict) else None
            ),
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
        return ProviderAuthError(f"OpenAI-compatible API returned HTTP {status}")
    if status == 429:
        return ProviderRateLimitError(
            "OpenAI-compatible API rate limit",
            retry_after=_retry_after(response.headers.get("retry-after")),
        )
    if status >= 500:
        return ProviderServerError(f"OpenAI-compatible API returned HTTP {status}")
    reason = "endpoint_not_found" if status == 404 else "bad_response"
    return ProviderUnreachableError(
        f"OpenAI-compatible API returned HTTP {status}",
        detail={"reason": reason, "http_status": status},
    )


class OpenAICompatibleTextProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 60.0,
        supported_efforts: Mapping[str, set[Effort] | frozenset[Effort]] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = _chat_completions_url(base_url)
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._supported_efforts = {
            model_id: frozenset(efforts) for model_id, efforts in (supported_efforts or {}).items()
        }
        self._transport = transport

    async def list_models(self) -> list[ProviderModel]:
        headers = {"accept": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self._timeout
            ) as client:
                response = await client.get(_models_url(self._base_url), headers=headers)
                if response.is_error:
                    raise _http_error(response)
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise _model_bad_response() from exc
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise _model_bad_response()
                models: list[ProviderModel] = []
                seen: set[str] = set()
                for raw in payload["data"]:
                    model = _compatible_model(raw)
                    if model.id not in seen:
                        seen.add(model.id)
                        models.append(model)
                return models
        except httpx.TimeoutException as exc:
            raise ProviderUnreachableError(
                "OpenAI-compatible model discovery timed out", detail={"reason": "timeout"}
            ) from exc
        except httpx.TransportError as exc:
            raise ProviderUnreachableError(
                "OpenAI-compatible model discovery connection failed",
                detail={"reason": "connection"},
            ) from exc

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamEvent]:
        messages: list[dict[str, str]] = []
        if request.system is not None:
            messages.append({"role": "system", "content": request.system})
        messages.extend(message.model_dump() for message in request.messages)
        body: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        supported = self._supported_efforts.get(request.model, frozenset())
        if request.effort is not None and request.effort in supported:
            body["reasoning_effort"] = request.effort
        if request.response_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": request.response_schema,
                },
            }
        elif request.json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {"content-type": "application/json", "accept": "text/event-stream"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"

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
                            "OpenAI-compatible response was not an event stream",
                            detail={"reason": "bad_response"},
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_lines.append(line[5:].lstrip())
                            continue
                        if line or not data_lines:
                            continue
                        payload = "\n".join(data_lines)
                        data_lines.clear()
                        if payload == "[DONE]":
                            break
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError as exc:
                            raise ProviderUnreachableError(
                                "OpenAI-compatible API returned malformed stream data",
                                detail={"reason": "bad_response"},
                            ) from exc
                        if not isinstance(event, dict):
                            raise ProviderUnreachableError(
                                "OpenAI-compatible API returned malformed stream data",
                                detail={"reason": "bad_response"},
                            )

                        usage = event.get("usage")
                        if isinstance(usage, dict):
                            usage_reported = True
                            input_tokens = int(usage.get("prompt_tokens", 0) or 0)
                            output_tokens = int(usage.get("completion_tokens", 0) or 0)
                            details = usage.get("prompt_tokens_details") or {}
                            if isinstance(details, dict):
                                cache_read = int(details.get("cached_tokens", 0) or 0)

                        choices = event.get("choices") or []
                        for choice in choices:
                            if not isinstance(choice, dict):
                                continue
                            delta = choice.get("delta") or {}
                            content = delta.get("content") if isinstance(delta, dict) else None
                            if isinstance(content, str) and content:
                                yield TextDelta(text=content)
                            elif isinstance(content, list):
                                for part in content:
                                    if (
                                        isinstance(part, dict)
                                        and part.get("type") == "text"
                                        and isinstance(part.get("text"), str)
                                    ):
                                        yield TextDelta(text=part["text"])
                            reason = choice.get("finish_reason")
                            if isinstance(reason, str):
                                stop_reason = reason
        except httpx.TimeoutException as exc:
            raise ProviderUnreachableError(
                "OpenAI-compatible request timed out", detail={"reason": "timeout"}
            ) from exc
        except httpx.TransportError as exc:
            raise ProviderUnreachableError(
                "OpenAI-compatible connection failed", detail={"reason": "connection"}
            ) from exc

        normalized_reason = {
            "length": "max_tokens",
            "max_tokens": "max_tokens",
            "content_filter": "refusal",
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


class OllamaTextProvider(OpenAICompatibleTextProvider):
    """Ollama/LM Studio compatible API; local inference does not require an API key."""

    name = "ollama_lmstudio"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        timeout: float = 600.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(base_url=base_url, timeout=timeout, transport=transport)
