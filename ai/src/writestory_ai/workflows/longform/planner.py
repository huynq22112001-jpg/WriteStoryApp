import json

from writestory_ai.contracts.errors import StructuredOutputInvalidError
from writestory_ai.contracts.generation import GenerationRequest, Message
from writestory_ai.contracts.longform import ChapterPlan
from writestory_ai.providers.collect import collect


def validate_plan(
    plan: ChapterPlan,
    *,
    available_event_ids: set[str],
    alive_character_ids: set[str],
    target_length: tuple[int, int],
    chapter_no: int,
    target_chapters: int,
    allow_early_ending: bool = False,
) -> list[str]:
    errors = []
    if not set(plan.required_event_ids) <= available_event_ids:
        errors.append("required_event_ids chứa sự kiện không khả dụng")
    if (
        plan.opening.get("present_character_ids", [])
        and not set(plan.opening["present_character_ids"]) <= alive_character_ids
    ):
        errors.append("opening có nhân vật không còn sống")
    if tuple(plan.target_length.get(k) for k in ("min", "max")) != target_length:
        errors.append("target_length không khớp WriteSettings")
    expected_end = chapter_no >= target_chapters or allow_early_ending
    if plan.allowed_ending != expected_end:
        errors.append("allowed_ending không khớp cấu hình kết thúc")
    return errors


async def create_plan(
    provider,
    *,
    model: str,
    chapter_no: int,
    target_length: tuple[int, int],
    outline: str,
    context: str,
    prompts,
    json_fix=None,
    max_tokens: int = 1800,
    validation_context: dict | None = None,
) -> ChapterPlan:
    prompt = prompts.render(
        "longform.planner",
        chapter_no=chapter_no,
        target_min=target_length[0],
        target_max=target_length[1],
        outline=outline,
        context=context,
    )
    result = await collect(
        provider,
        GenerationRequest(
            model=model, max_tokens=max_tokens, messages=[Message(role="user", content=prompt)]
        ),
    )
    raw = result.text
    try:
        plan = ChapterPlan.model_validate(json.loads(raw))
    except (ValueError, TypeError) as first:
        if json_fix is None:
            raise StructuredOutputInvalidError("ChapterPlan JSON không hợp lệ") from first
        repaired = json_fix(raw, str(first))
        if hasattr(repaired, "__await__"):
            repaired = await repaired
        try:
            plan = ChapterPlan.model_validate(
                repaired if isinstance(repaired, dict) else json.loads(repaired)
            )
        except (ValueError, TypeError) as error:
            raise StructuredOutputInvalidError("ChapterPlan JSON vẫn không hợp lệ") from error
    if validation_context is not None:
        errors = validate_plan(plan, **validation_context)
        if errors:
            if json_fix is None:
                raise StructuredOutputInvalidError("ChapterPlan không qua kiểm tra xác định")
            repaired = json_fix(raw, "; ".join(errors))
            if hasattr(repaired, "__await__"):
                repaired = await repaired
            try:
                plan = ChapterPlan.model_validate(
                    repaired if isinstance(repaired, dict) else json.loads(repaired)
                )
            except (ValueError, TypeError) as error:
                raise StructuredOutputInvalidError("ChapterPlan JSON vẫn không hợp lệ") from error
            if validate_plan(plan, **validation_context):
                raise StructuredOutputInvalidError("ChapterPlan vẫn không qua kiểm tra xác định")
    return plan
