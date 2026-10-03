from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import Field

from writestory_ai.contracts.state import StrictModel


class ContextBlock(StrictModel):
    id: str
    layer: Literal["app", "story", "chapter", "turn"]
    text: str
    token_estimate: int = Field(ge=0)
    protected: bool = False
    compressible: bool = True


class ContextTraceItem(StrictModel):
    block_id: str
    included: bool
    original_tokens: int
    final_tokens: int
    reason: str | None = None


class ContextPackage(StrictModel):
    text: str
    token_estimate: int
    included_ids: list[str]
    dropped_ids: list[str]


class ContextTrace(StrictModel):
    items: list[ContextTraceItem]
    total_tokens: int


class ProtectedContextOverBudget(ValueError):
    code = "CONTEXT_PROTECTED_OVER_BUDGET"


def compose_context(
    blocks: list[ContextBlock],
    *,
    token_budget: int,
    compressor: Callable[[ContextBlock, int], ContextBlock | None] | None = None,
) -> tuple[ContextPackage, ContextTrace]:
    layer_order = {"app": 0, "story": 1, "chapter": 2, "turn": 3}
    ordered = sorted(blocks, key=lambda block: layer_order[block.layer])
    protected = [block for block in ordered if block.protected]
    protected_total = sum(block.token_estimate for block in protected)
    if protected_total > token_budget:
        raise ProtectedContextOverBudget("Protected context exceeds model input budget")
    remaining = token_budget - protected_total
    selected = list(protected)
    compressed: dict[str, ContextBlock] = {}
    for block in ordered:
        if block.protected:
            continue
        if block.token_estimate <= remaining:
            selected.append(block)
            remaining -= block.token_estimate
        elif block.compressible and compressor is not None:
            reduced = compressor(block, remaining)
            if reduced is not None and reduced.token_estimate <= remaining:
                selected.append(reduced)
                compressed[block.id] = reduced
                remaining -= reduced.token_estimate
    selected_ids = {block.id for block in selected}
    text = "\n\n".join(
        compressed.get(block.id, block).text for block in ordered if block.id in selected_ids
    )
    traces = [
        ContextTraceItem(
            block_id=b.id,
            included=b.id in selected_ids,
            original_tokens=b.token_estimate,
            final_tokens=(
                compressed[b.id].token_estimate if b.id in compressed else b.token_estimate
            )
            if b.id in selected_ids
            else 0,
            reason=None if b.id in selected_ids else "budget",
        )
        for b in ordered
    ]
    package = ContextPackage(
        text=text,
        token_estimate=sum(compressed.get(b.id, b).token_estimate for b in selected),
        included_ids=[b.id for b in ordered if b.id in selected_ids],
        dropped_ids=[b.id for b in ordered if b.id not in selected_ids],
    )
    return package, ContextTrace(items=traces, total_tokens=package.token_estimate)
