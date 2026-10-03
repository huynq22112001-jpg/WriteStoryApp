from __future__ import annotations

from pydantic import BaseModel, ValidationError

from writestory_ai.contracts.errors import (
    OutputTruncatedError,
    ProviderRefusalError,
    StructuredOutputInvalidError,
)
from writestory_ai.contracts.events import StepProgress
from writestory_ai.contracts.foundation import (
    AddressRulesOutput,
    CastOutput,
    EventOutlineVolumeOutput,
    FoundationInput,
    FoundationStageResult,
    FrameCoreOutput,
    HooksOutput,
)
from writestory_ai.contracts.generation import GenerationRequest, Message
from writestory_ai.contracts.state import (
    CharacterState,
    EventState,
    HookState,
    Location,
    Relationship,
    StoryState,
    StoryTime,
)
from writestory_ai.contracts.usage import Usage
from writestory_ai.evaluators.foundation_checks import check_foundation
from writestory_ai.providers.collect import collect

_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "frame_core": FrameCoreOutput,
    "cast": CastOutput,
    "address_rules": AddressRulesOutput,
    "hooks": HooksOutput,
}


def _plain(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def seed_story_state(request: FoundationInput, parts: dict[str, dict]) -> StoryState:
    """Create the chapter-zero state from accepted/generated foundation parts."""
    cast = _plain(parts.get("cast", {}))
    opening = cast.get("opening", {})
    present_ids = set(opening.get("present_character_ids", []))
    characters = [
        CharacterState(
            id=item["temp_id"],
            location_id=item.get("initial_location_temp_id")
            or (opening.get("location_temp_id") if item["temp_id"] in present_ids else None),
            condition=item.get("initial_condition", ""),
            goals=item.get("goals", []),
            in_last_scene=item["temp_id"] in present_ids,
            last_seen_chapter=0 if item["temp_id"] in present_ids else None,
        )
        for item in cast.get("characters", [])
    ]
    relationships = [
        Relationship(
            a=item["a"],
            b=item["b"],
            kind=item["kind"],
            category=item["kind"]
            if item["kind"]
            in {"family", "mentor", "friend", "romance", "rival", "enemy", "political", "other"}
            else "other",
            intensity=max(-3, min(3, item.get("intensity", 3) - 3)),
            since_chapter=0,
        )
        for item in cast.get("relationships", [])
    ]
    events = [
        EventState(
            story_event_id=event["temp_id"],
            status="planned",
            planned_chapter=event["planned_chapter"],
            depends_on=event.get("depends_on", []),
        )
        for key, part in parts.items()
        if key.startswith("events_")
        for event in _plain(part).get("events", [])
    ]
    hooks = [
        HookState(
            id=hook["temp_id"],
            title=hook["title"],
            status="open",
            opened_at=hook["opened_at_chapter"],
            due_by=hook["due_by_chapter"],
            payoff_plan=hook.get("payoff_plan", ""),
            priority=hook.get("priority", 2),
        )
        for hook in _plain(parts.get("hooks", {})).get("hooks", [])
    ]
    return StoryState(
        work_id=request.work_id,
        chapter_no=0,
        story_time=StoryTime(label=opening.get("story_time_label", "Mở đầu"), ordinal=0),
        characters=characters,
        relationships=relationships,
        hooks=hooks,
        events=events,
        locations=[
            Location(id=item["temp_id"], name=item["name"], aliases=item.get("aliases", []))
            for item in cast.get("locations", [])
        ],
    )


def _parts_for_stage(request: FoundationInput, context: dict) -> list[tuple[str, str, dict]]:
    if request.stage == "frame":
        candidates = [
            ("frame_core", "vi.foundation.frame_core", FrameCoreOutput),
            ("cast", "vi.foundation.cast", CastOutput),
        ]
        selected = request.parts or [name for name, _, _ in candidates]
        return [(name, prompt, {}) for name, prompt, _ in candidates if name in selected]
    if request.stage == "address_rules":
        selected = request.parts or ["address_rules"]
        return (
            [("address_rules", "vi.foundation.address_rules", {})]
            if "address_rules" in selected
            else []
        )

    selected = request.parts
    frame = _plain(context.get("frame_core", {}))
    volumes = frame.get("volume_map", [])
    if not volumes:
        raise ValueError("event_outline requires frame_core.volume_map")
    plan = []
    for volume in volumes:
        volume = _plain(volume)
        name = f"events_v{volume['volume_no']}"
        if selected is None or name in selected:
            plan.append((name, "vi.foundation.event_outline_volume", volume))
    if selected is None or "hooks" in selected:
        plan.append(("hooks", "vi.foundation.hooks", {}))
    return plan


def _context_for_part(part: str, context: dict, request: FoundationInput, extra: dict) -> dict:
    frame = _plain(context.get("frame_core", {}))
    cast = _plain(context.get("cast", {}))
    prior_events = [
        event
        for name, value in context.items()
        if name.startswith("events_")
        for event in _plain(value).get("events", [])
    ]
    return {
        "genre": request.genre,
        "genre_label": request.genre_label,
        "brief": request.brief,
        "target_chapters": request.target_chapters,
        "chapter_length_min": request.chapter_length_min,
        "chapter_length_max": request.chapter_length_max,
        "style": request.style,
        "instruction": request.instruction or "",
        "frame_core": frame,
        "cast": cast,
        "accepted": request.accepted,
        "previous_events": prior_events,
        "volume": extra,
        "events": prior_events,
    }


async def _request_part(
    provider,
    *,
    model: str,
    prompt: str,
    schema: dict,
    capabilities: dict,
    max_tokens: int,
):
    structured = bool(capabilities.get("structured_outputs"))
    return await collect(
        provider,
        GenerationRequest(
            model=model,
            max_tokens=max_tokens,
            messages=[Message(role="user", content=prompt)],
            system=None
            if structured
            else "Chỉ trả về một đối tượng JSON đúng schema, không thêm markdown.",
            response_schema=schema if structured else None,
            json_mode=not structured,
        ),
    )


async def _fix_invalid_json(
    provider,
    *,
    model: str,
    raw: str,
    errors: str,
    prompts,
    schema: dict,
    capabilities: dict,
    max_tokens: int,
) -> str:
    prompt = prompts.render("common.json_fix", raw_output=raw, errors=errors)
    result = await _request_part(
        provider,
        model=model,
        prompt=prompt,
        schema=schema,
        capabilities=capabilities,
        max_tokens=max_tokens,
    )
    if result.stop_reason == "refusal":
        raise ProviderRefusalError("Provider refused to repair foundation JSON")
    if result.stop_reason == "max_tokens":
        raise OutputTruncatedError("Foundation JSON repair was truncated")
    return result.text


def _parse(model: type[BaseModel], raw: str):
    try:
        return model.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        raise StructuredOutputInvalidError("Foundation output không đúng schema") from exc


async def run_stage(
    request: FoundationInput,
    provider,
    *,
    model: str,
    prompts,
    checkpoint=None,
    progress=None,
    capabilities: dict | None = None,
    max_tokens: int = 16000,
) -> FoundationStageResult:
    """Generate one foundation stage. AI returns data only; persistence stays in the host."""
    capabilities = capabilities or {}
    accumulated = {
        **{key: _plain(value) for key, value in request.accepted.items()},
        **{key: _plain(value) for key, value in request.previous_parts.items()},
    }
    plan = _parts_for_stage(request, accumulated)
    if request.parts is not None:
        valid_names = {name for name, _, _ in plan}
        unknown = set(request.parts) - valid_names
        if unknown:
            raise ValueError(
                f"Foundation parts do not belong to stage: {', '.join(sorted(unknown))}"
            )
    outputs: dict[str, dict] = {}
    usages: list[Usage] = []
    prompt_versions: dict[str, str] = {}
    for part, prompt_id, extra in plan:
        if part in request.previous_parts and (request.parts is None or part not in request.parts):
            outputs[part] = _plain(request.previous_parts[part])
            continue
        if part in request.accepted and (request.parts is None or part not in request.parts):
            outputs[part] = _plain(request.accepted[part])
            continue
        if part.startswith("events_"):
            output_model = EventOutlineVolumeOutput
        else:
            output_model = _OUTPUT_MODELS[part]
        prompt = prompts.render(prompt_id, **_context_for_part(part, accumulated, request, extra))
        prompt_versions[part] = prompts.prompt_version(prompt_id)
        result = await _request_part(
            provider,
            model=model,
            prompt=prompt,
            schema=output_model.model_json_schema(),
            capabilities=capabilities,
            max_tokens=max_tokens,
        )
        if result.stop_reason == "refusal":
            raise ProviderRefusalError(f"Provider refused foundation part {part}")
        if result.stop_reason == "max_tokens":
            if part.startswith("events_") and extra.get("chapter_from", 0) < extra.get(
                "chapter_to", 0
            ):
                midpoint = (extra["chapter_from"] + extra["chapter_to"]) // 2
                split_outputs = []
                for lower, upper in (
                    (extra["chapter_from"], midpoint),
                    (midpoint + 1, extra["chapter_to"]),
                ):
                    split_volume = {**extra, "chapter_from": lower, "chapter_to": upper}
                    split_prompt = prompts.render(
                        prompt_id, **_context_for_part(part, accumulated, request, split_volume)
                    )
                    split = await _request_part(
                        provider,
                        model=model,
                        prompt=split_prompt,
                        schema=output_model.model_json_schema(),
                        capabilities=capabilities,
                        max_tokens=max_tokens,
                    )
                    if split.stop_reason == "refusal":
                        raise ProviderRefusalError(f"Provider refused foundation part {part}")
                    if split.stop_reason == "max_tokens":
                        raise OutputTruncatedError(
                            f"Foundation part {part} remained truncated after split"
                        )
                    split_outputs.append(_parse(output_model, split.text))
                    usages.append(split.usage)
                parsed = EventOutlineVolumeOutput(
                    volume_no=extra["volume_no"],
                    events=[event for item in split_outputs for event in item.events],
                )
                usages.append(result.usage)
            else:
                raise OutputTruncatedError(f"Foundation part {part} was truncated")
        else:
            try:
                parsed = _parse(output_model, result.text)
                usages.append(result.usage)
            except StructuredOutputInvalidError as first:
                repaired = await _fix_invalid_json(
                    provider,
                    model=model,
                    raw=result.text,
                    errors=str(first),
                    prompts=prompts,
                    schema=output_model.model_json_schema(),
                    capabilities=capabilities,
                    max_tokens=max_tokens,
                )
                parsed = _parse(output_model, repaired)
        output = _plain(parsed)
        if part.startswith("events_") and output.get("volume_no") != extra.get("volume_no"):
            raise StructuredOutputInvalidError(f"Foundation output {part} has wrong volume_no")
        outputs[part] = output
        accumulated[part] = output
        if checkpoint is not None:
            await checkpoint.save(part, {"output": output, "usage": usages[-1].model_dump()})
        if progress is not None and hasattr(progress, "on_step"):
            await progress.on_step(StepProgress(step=part, progress=1.0))

    warnings = check_foundation(request, accumulated)
    seed_state = (
        seed_story_state(request, accumulated)
        if request.stage == "event_outline"
        and {"frame_core", "cast", "address_rules", "hooks"}.issubset(accumulated)
        else None
    )
    return FoundationStageResult(
        stage=request.stage,
        parts=outputs,
        warnings=warnings,
        usage=usages,
        prompt_versions=prompt_versions,
        seed_state=seed_state,
    )
