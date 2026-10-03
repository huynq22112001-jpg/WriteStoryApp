from __future__ import annotations

from collections.abc import Callable

from writestory_ai.contracts.state import TailText
from writestory_ai.languages.vi.length import count_syllables


def estimate_tokens(text: str, *, tokens_per_syllable: float = 1.0, margin: float = 0.15) -> int:
    if tokens_per_syllable <= 0 or margin < 0:
        raise ValueError("Invalid token estimation parameters")
    return round(count_syllables(text) * tokens_per_syllable * (1 + margin))


def count_tokens(
    text: str, counter: Callable[[str], int] | None = None, *, tokens_per_syllable: float = 1.0
) -> int:
    return (
        counter(text) if counter else estimate_tokens(text, tokens_per_syllable=tokens_per_syllable)
    )


async def count_request_tokens(
    provider, messages, *, fallback_text: str, tokens_per_syllable: float = 1.0
) -> tuple[int, str]:
    counter = getattr(provider, "count_tokens", None)
    if counter is not None:
        result = counter(messages)
        if hasattr(result, "__await__"):
            result = await result
        return int(result), "exact"
    return estimate_tokens(fallback_text, tokens_per_syllable=tokens_per_syllable), "estimate"


def cut_tail(
    paragraphs: list[tuple[str, str]],
    *,
    min_tokens: int = 1000,
    max_tokens: int = 2000,
    tokens_per_syllable: float = 1.0,
) -> TailText:
    if min_tokens < 0 or max_tokens < min_tokens:
        raise ValueError("Invalid tail token bounds")
    chosen: list[tuple[str, str]] = []
    total = 0
    for paragraph_id, text in reversed(paragraphs):
        size = estimate_tokens(text, tokens_per_syllable=tokens_per_syllable, margin=0)
        if total + size > max_tokens:
            break
        chosen.append((paragraph_id, text))
        total += size
        if total >= min_tokens:
            break
    chosen.reverse()
    return TailText(
        text="\n\n".join(text for _, text in chosen),
        paragraph_ids=[pid for pid, _ in chosen],
        token_estimate=total,
    )
