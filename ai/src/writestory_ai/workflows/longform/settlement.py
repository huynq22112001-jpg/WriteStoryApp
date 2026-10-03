from __future__ import annotations

import json

from pydantic import ValidationError

from writestory_ai.contracts.errors import (
    OutputTruncatedError,
    ProviderRefusalError,
    StructuredOutputInvalidError,
)
from writestory_ai.contracts.generation import GenerationRequest, Message
from writestory_ai.contracts.state import StateDelta
from writestory_ai.providers.collect import collect


def parse_settlement(raw: str, *, fix_json=None) -> StateDelta:
    try:
        parsed = StateDelta.model_validate_json(raw)
        if parsed.source != "pipeline":
            raise ValueError("Settlement phải có source=pipeline")
        return parsed
    except (ValidationError, ValueError) as first:
        if fix_json is None:
            raise StructuredOutputInvalidError("Settlement JSON không đúng schema") from first
        repaired = fix_json(raw, str(first))
        if hasattr(repaired, "__await__"):
            raise TypeError("Use parse_settlement_async for async JSON repair") from first
        try:
            parsed = StateDelta.model_validate(
                repaired if isinstance(repaired, dict) else json.loads(repaired)
            )
            if parsed.source != "pipeline":
                raise ValueError("Settlement phải có source=pipeline")
            return parsed
        except (ValidationError, ValueError) as second:
            raise StructuredOutputInvalidError("Settlement JSON vẫn không đúng schema") from second


async def create_settlement(
    provider,
    *,
    model: str,
    paragraphs: str,
    prompts,
    json_fix=None,
    max_tokens: int = 1800,
    capabilities: dict | None = None,
) -> StateDelta:
    prompt = prompts.render("longform.settler", paragraphs=paragraphs)
    structured = bool((capabilities or {}).get("structured_outputs"))
    result = await collect(
        provider,
        GenerationRequest(
            model=model,
            max_tokens=max_tokens,
            messages=[Message(role="user", content=prompt)],
            system=None
            if structured
            else "Chỉ trả về một đối tượng JSON đúng schema StateDelta, không thêm markdown.",
            response_schema=StateDelta.model_json_schema() if structured else None,
            json_mode=not structured,
        ),
    )
    if result.stop_reason == "refusal":
        raise ProviderRefusalError("Provider refused to settle the candidate")
    if result.stop_reason == "max_tokens":
        raise OutputTruncatedError("Settlement JSON was truncated")
    if json_fix is None:
        return parse_settlement(result.text)
    try:
        return StateDelta.model_validate_json(result.text)
    except ValidationError as first:
        repaired = json_fix(result.text, str(first))
        if hasattr(repaired, "__await__"):
            repaired = await repaired
        try:
            return StateDelta.model_validate(
                repaired if isinstance(repaired, dict) else json.loads(repaired)
            )
        except (ValidationError, ValueError) as second:
            raise StructuredOutputInvalidError("Settlement JSON vẫn không đúng schema") from second
