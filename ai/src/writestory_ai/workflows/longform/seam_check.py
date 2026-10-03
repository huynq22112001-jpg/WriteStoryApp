from __future__ import annotations

from collections.abc import Awaitable, Callable

from writestory_ai.contracts.longform import SeamResult
from writestory_ai.contracts.state import EndingState


async def check_seam(
    previous: EndingState,
    opening_paragraphs: list[dict],
    evaluator: Callable | None = None,
    *,
    plan_opening: dict | None = None,
) -> SeamResult:
    if evaluator is not None:
        result = evaluator(previous, opening_paragraphs)
        if isinstance(result, Awaitable):
            result = await result
        result = result if isinstance(result, SeamResult) else SeamResult.model_validate(result)
        paragraphs = {
            str(item.get("paragraph_id", "")): str(item.get("text", ""))
            for item in opening_paragraphs
        }
        from writestory_ai.languages.vi.normalizer import normalize_text

        aspects = {}
        for name, raw in result.aspects.items():
            if not isinstance(raw, dict):
                continue
            aspect = dict(raw)
            verdict = aspect.get("verdict")
            paragraph_id, quote = aspect.get("paragraph_id"), aspect.get("quote")
            if verdict == "mismatch" or verdict == "transition_ok":
                text = paragraphs.get(str(paragraph_id), "") if paragraph_id else ""
                if not quote or normalize_text(str(quote)) not in normalize_text(text):
                    aspect["verdict"] = "not_addressed"
                    aspect["unverified"] = True
            if aspect.get("verdict") == "transition_ok":
                transition = (plan_opening or {}).get("transition", "none")
                if transition == "none":
                    aspect["verdict"] = "mismatch"
                    aspect["unverified"] = False
            aspects[name] = aspect

        hard_mismatch = any(
            aspects.get(name, {}).get("verdict") == "mismatch"
            for name in ("location", "time", "present_characters")
        )
        unfinished = aspects.get("unfinished_actions", {}).get("verdict") == "not_addressed"
        if unfinished:
            deferred = any(
                action.get("handling") == "defer_explicit"
                for action in (plan_opening or {}).get("unfinished_actions", [])
            )
            aspect = aspects["unfinished_actions"]
            text = paragraphs.get(str(aspect.get("paragraph_id", "")), "")
            quote = aspect.get("quote")
            deferred = (
                deferred and bool(quote) and normalize_text(str(quote)) in normalize_text(text)
            )
            unfinished = not deferred
        # Emotion mismatches are reported but do not block the seam.
        verdict = "fail" if hard_mismatch or unfinished else result.verdict
        if aspects and not hard_mismatch and not unfinished:
            verdict = "pass"
        return SeamResult(aspects=aspects, verdict=verdict, notes=result.notes)
    # Without an LLM evaluator, verify only obvious location mentions.
    first_text = " ".join(p.get("text", "") for p in opening_paragraphs[:3])
    expected = previous.location_label
    if expected and expected not in first_text:
        return SeamResult(
            verdict="fail", notes=["Mở chương chưa xác lập địa điểm cuối chương trước"]
        )
    return SeamResult(verdict="pass", notes=["Không phát hiện mâu thuẫn địa điểm hiển nhiên"])
