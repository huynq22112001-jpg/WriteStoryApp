from __future__ import annotations

from collections.abc import Awaitable, Callable

from writestory_ai.context.tokens import estimate_tokens
from writestory_ai.contracts.paragraphs import ParagraphOps, ParagraphText, apply_ops


class RepairExhausted(RuntimeError):
    code = "REPAIR_EXHAUSTED"


async def repair_until_clear(
    paragraphs: list[ParagraphText],
    findings: list[dict],
    repairer: Callable,
    checker: Callable,
    *,
    max_rounds: int = 2,
    token_cap: int = 4000,
    include_major: bool = False,
    max_changed_ratio: float = 0.25,
) -> tuple[list[ParagraphText], list[dict]]:
    current = paragraphs
    remaining = findings
    used_tokens = 0
    for _round in range(max_rounds):
        actionable = [
            f
            for f in remaining
            if f.get("severity") == "blocker" or (include_major and f.get("severity") == "major")
        ]
        if not actionable:
            return current, remaining
        ids = {str(f["paragraph_id"]) for f in actionable if f.get("paragraph_id")}
        proposal = repairer(current, actionable)
        if isinstance(proposal, Awaitable):
            proposal = await proposal
        ops = (
            proposal
            if isinstance(proposal, ParagraphOps)
            else ParagraphOps.model_validate(proposal)
        )
        used_tokens += sum(estimate_tokens(op.text or "") for op in ops.ops)
        changed_ids = {op.paragraph_id for op in ops.ops}
        if current and len(changed_ids) / len(current) > max_changed_ratio:
            raise RepairExhausted("Repair changed too much of the candidate")
        if used_tokens > token_cap or any(op.paragraph_id not in ids for op in ops.ops):
            raise RepairExhausted("Repair exceeded scope or token cap")
        current = apply_ops(current, ops, allowed_ids=ids)
        result = checker(current)
        if isinstance(result, Awaitable):
            result = await result
        remaining = result
        still_actionable = any(
            f.get("severity") == "blocker" or (include_major and f.get("severity") == "major")
            for f in remaining
        )
        if not still_actionable:
            return current, remaining
    raise RepairExhausted("Maximum repair rounds exhausted")
