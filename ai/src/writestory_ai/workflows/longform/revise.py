from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from pydantic import ValidationError

from writestory_ai.contracts.errors import (
    OutputTruncatedError,
    ProviderRefusalError,
    StructuredOutputInvalidError,
)
from writestory_ai.contracts.generation import GenerationRequest, Message
from writestory_ai.contracts.paragraphs import ParagraphOps, ParagraphText, apply_ops
from writestory_ai.contracts.revise import ReviseInput, ReviseOutput
from writestory_ai.languages.vi.normalizer import normalize_text
from writestory_ai.providers.collect import collect


def validate_revise_output(data: ReviseOutput, request: ReviseInput) -> None:
    paragraphs = {paragraph.paragraph_id: paragraph for paragraph in request.paragraphs}
    if request.scope.type == "selection":
        selection = request.scope.selection
        target = paragraphs.get(selection.paragraph_id)
        if target is None or not target.editable:
            raise ValueError("Selected paragraph is not editable")
        if selection.end > len(target.text):
            raise ValueError("Selection range exceeds paragraph length")
        if data.selection_replacement is None or data.ops:
            raise ValueError(
                "Selection revision requires selection_replacement and no paragraph ops"
            )
        return
    if data.selection_replacement is not None:
        raise ValueError("selection_replacement is only valid for selection scope")
    if request.scope.type == "chapter":
        editable = {key for key, paragraph in paragraphs.items() if paragraph.editable}
    else:
        editable = {
            key
            for key in request.scope.paragraph_ids
            if key in paragraphs and paragraphs[key].editable
        }
    op_ids = [operation.paragraph_id for operation in data.ops]
    if len(op_ids) != len(set(op_ids)):
        raise ValueError("A paragraph may be changed at most once per revision")
    if any(paragraph_id not in editable for paragraph_id in op_ids):
        raise ValueError("Revision contains an operation outside its editable scope")


def apply_revision(request: ReviseInput, output: ReviseOutput) -> list[ParagraphText]:
    validate_revise_output(output, request)
    paragraphs = [
        ParagraphText(paragraph_id=item.paragraph_id, text=item.text) for item in request.paragraphs
    ]
    if request.scope.type == "selection":
        selection = request.scope.selection
        target = next(item for item in paragraphs if item.paragraph_id == selection.paragraph_id)
        replacement = normalize_text(output.selection_replacement or "")
        target.text = target.text[: selection.start] + replacement + target.text[selection.end :]
        return paragraphs
    allowed = {item.paragraph_id for item in request.paragraphs if item.editable}
    if request.scope.type == "paragraphs":
        allowed &= set(request.scope.paragraph_ids)
    normalized_ops = output.ops.copy()
    for operation in normalized_ops:
        if operation.text is not None:
            operation.text = normalize_text(operation.text)
    return apply_ops(paragraphs, ParagraphOps(ops=normalized_ops), allowed_ids=allowed)


async def create_revision(
    provider,
    *,
    model: str,
    request: ReviseInput,
    prompts,
    json_fix: Callable | None = None,
    capabilities: dict | None = None,
    rework_validator: Callable | None = None,
    max_tokens: int = 3000,
) -> ReviseOutput:
    prompt = prompts.render(
        "longform.revise",
        mode=request.mode,
        paragraphs=request.paragraphs,
        scope=request.scope.model_dump(mode="json"),
        instruction=request.author_instruction,
        findings=request.findings,
        next_opening=request.next_opening or "",
        state_before=request.state_before.model_dump(mode="json"),
        handoff_prev=request.handoff_prev,
        style_profile=request.style_profile,
        address_rules=request.address_rules,
        length_target=request.length_target,
        completed_event_ids=request.completed_event_ids,
    )
    structured = bool((capabilities or {}).get("structured_outputs"))
    response = await collect(
        provider,
        GenerationRequest(
            model=model,
            max_tokens=max_tokens,
            messages=[Message(role="user", content=prompt)],
            system=None
            if structured
            else "Chỉ trả về một đối tượng JSON đúng schema ReviseOutput.",
            response_schema=ReviseOutput.model_json_schema() if structured else None,
            json_mode=not structured,
        ),
    )
    if response.stop_reason == "refusal":
        raise ProviderRefusalError("Provider refused the revision")
    if response.stop_reason == "max_tokens":
        raise OutputTruncatedError("Revision JSON was truncated")

    raw: str | dict = response.text
    errors = ""
    for attempt in range(2):
        try:
            value = raw if isinstance(raw, dict) else json.loads(raw)
            output = ReviseOutput.model_validate(value)
            validate_revise_output(output, request)
            if request.mode == "rework" and request.completed_event_ids:
                if rework_validator is None:
                    raise ValueError("rework requires completed-event validation")
                preserved = rework_validator(request, output)
                if isinstance(preserved, Awaitable):
                    preserved = await preserved
                if not preserved:
                    raise ValueError("rework would remove or alter a completed story event")
            output.resettle_required = bool(output.ops or output.selection_replacement is not None)
            output.usage = response.usage
            return output
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            errors = str(exc)
            if attempt or json_fix is None:
                raise StructuredOutputInvalidError(
                    "Revise output không đúng schema/phạm vi"
                ) from exc
            repaired = json_fix(raw, errors)
            if isinstance(repaired, Awaitable):
                repaired = await repaired
            raw = repaired if isinstance(repaired, dict) else str(repaired)
    raise StructuredOutputInvalidError("Revise output không đúng schema/phạm vi")
