from __future__ import annotations

from collections.abc import Awaitable, Callable

from writestory_ai.contracts.longform import ReviewResult

_SEVERITY = {
    "fact": "blocker",
    "timeline": "blocker",
    "seam": "blocker",
    "name": "blocker",
    "ending": "blocker",
    "repetition": "blocker",
    "missing_event": "blocker",
    "meta_leak": "blocker",
    "address": "major",
    "POV": "major",
    "ooc": "major",
    "slop": "minor",
    "anachronism": "major",
    "name_variant": "major",
    "tone_mark_style": "major",
    "length": "major",
    "hook_overdue": "major",
    "pacing": "major",
    "craft": "minor",
    "voice": "minor",
    "spelling": "minor",
    "dialogue": "minor",
    "lexicon": "minor",
}


async def review(findings: list[dict], evaluator: Callable | None = None) -> ReviewResult:
    collected = [dict(finding) for finding in findings]
    confirmations: dict[str, bool] = {}
    if evaluator is not None:
        result = evaluator([dict(finding) for finding in findings])
        if isinstance(result, Awaitable):
            result = await result
        result = result if isinstance(result, ReviewResult) else ReviewResult.model_validate(result)
        confirmations = {
            str(c.get("finding_id")): bool(c.get("confirmed"))
            for c in result.confirmations
            if c.get("finding_id") is not None and c.get("confirmed") is not None
        }
        collected.extend(dict(finding) for finding in result.findings)

    merged: dict[tuple, dict] = {}
    for finding in collected:
        key = (
            finding.get("id"),
            finding.get("kind"),
            finding.get("paragraph_id"),
            finding.get("start"),
            finding.get("quote"),
        )
        item = merged.setdefault(key, finding)
        if finding.get("needs_confirmation"):
            item["needs_confirmation"] = True
        if finding.get("confidence") == "high":
            item["confidence"] = "high"

    accepted = []
    for item in merged.values():
        finding_id = str(item.get("id", ""))
        confirmed_flag = confirmations.get(finding_id, item.get("confirmed"))
        if item.get("needs_confirmation") and confirmed_flag is not True:
            if confirmed_flag is False:
                continue
            # Chưa có xác nhận từ model: giữ finding với trạng thái chờ xác nhận.
            item["confirmation_pending"] = True
        if item.get("kind") == "address":
            item["severity"] = (
                "blocker" if item.get("confidence") == "high" or confirmed_flag is True else "major"
            )
        else:
            item["severity"] = _SEVERITY.get(
                item.get("kind", "craft"), item.get("severity", "minor")
            )
        accepted.append(item)
    return ReviewResult(findings=accepted)
