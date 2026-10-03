from __future__ import annotations

from collections.abc import Awaitable, Callable

from writestory_ai.contracts.longform import LLMValidation
from writestory_ai.contracts.state import StateDelta, StoryState
from writestory_ai.state.validate import ValidationResult, validate_delta


async def validate_candidate(
    state: StoryState,
    delta: StateDelta,
    paragraphs: dict[str, str],
    llm_validator: Callable | None = None,
) -> tuple[ValidationResult, LLMValidation | None]:
    deterministic = validate_delta(state, delta, paragraphs)
    if not deterministic.valid or llm_validator is None:
        return deterministic, None
    result = llm_validator(state, delta, paragraphs)
    if isinstance(result, Awaitable):
        result = await result
    llm = result if isinstance(result, LLMValidation) else LLMValidation.model_validate(result)
    verified_issues = []
    from writestory_ai.languages.vi.normalizer import normalize_text

    for issue in llm.issues:
        paragraph_id = issue.get("paragraph_id")
        quote = issue.get("quote")
        text = paragraphs.get(paragraph_id, "") if paragraph_id else ""
        if paragraph_id and quote and normalize_text(quote) in normalize_text(text):
            verified_issues.append(issue)
    # Ungrounded model claims are discarded before they can become blocking findings.
    return deterministic, LLMValidation(issues=verified_issues)
