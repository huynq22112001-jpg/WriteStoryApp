from __future__ import annotations

from typing import Literal

from pydantic import Field

from writestory_ai.contracts.state import StrictModel


class ParagraphText(StrictModel):
    paragraph_id: str = Field(pattern=r"^[a-z0-9]{8}$")
    text: str


class ParagraphOp(StrictModel):
    paragraph_id: str
    action: Literal["replace", "insert_after", "delete"]
    text: str | None = None


class ParagraphOps(StrictModel):
    ops: list[ParagraphOp] = Field(default_factory=list)


def render_paragraphs(paragraphs: list[ParagraphText]) -> str:
    return "\n".join(f"[p:{p.paragraph_id}] {p.text}" for p in paragraphs)


def apply_ops(
    paragraphs: list[ParagraphText], ops: ParagraphOps, *, allowed_ids: set[str] | None = None
) -> list[ParagraphText]:
    current = [p.model_copy(deep=True) for p in paragraphs]
    allowed = allowed_ids if allowed_ids is not None else {p.paragraph_id for p in current}
    for op in ops.ops:
        if op.paragraph_id not in allowed:
            raise ValueError(f"Paragraph outside repair scope: {op.paragraph_id}")
        index = next((i for i, p in enumerate(current) if p.paragraph_id == op.paragraph_id), None)
        if index is None:
            raise ValueError(f"Paragraph does not exist: {op.paragraph_id}")
        if op.action == "replace":
            current[index].text = op.text or ""
        elif op.action == "delete":
            current.pop(index)
        else:
            new_id = f"{(index + 1):08x}"[-8:]
            if any(p.paragraph_id == new_id for p in current):
                raise ValueError("Generated paragraph id collision")
            current.insert(index + 1, ParagraphText(paragraph_id=new_id, text=op.text or ""))
    return current
