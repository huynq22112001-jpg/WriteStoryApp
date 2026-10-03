from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from writestory_ai.contracts.paragraphs import ParagraphOp
from writestory_ai.contracts.state import StoryState, StrictModel
from writestory_ai.contracts.usage import Usage


class SelectionRange(StrictModel):
    paragraph_id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self):
        if self.end < self.start:
            raise ValueError("selection end must be greater than or equal to start")
        return self


class ReviseScope(StrictModel):
    type: Literal["selection", "paragraphs", "chapter"]
    paragraph_ids: list[str] = Field(default_factory=list)
    selection: SelectionRange | None = None

    @model_validator(mode="after")
    def validate_selection(self):
        if self.type == "selection":
            if self.selection is None:
                raise ValueError("selection scope requires a range")
            if self.paragraph_ids and self.paragraph_ids != [self.selection.paragraph_id]:
                raise ValueError("selection scope must target exactly its selected paragraph")
        elif self.selection is not None:
            raise ValueError("only selection scope may include a range")
        return self


class ReviseParagraph(StrictModel):
    paragraph_id: str
    text: str
    editable: bool = True


class ReviseInput(StrictModel):
    work_id: str
    chapter_no: int = Field(ge=1)
    language: str = "vi"
    mode: Literal["spot_fix", "polish", "rewrite", "rework"]
    scope: ReviseScope
    author_instruction: str
    paragraphs: list[ReviseParagraph]
    findings: list[dict] = Field(default_factory=list)
    completed_event_ids: list[str] = Field(default_factory=list)
    state_before: StoryState
    handoff_prev: dict = Field(default_factory=dict)
    next_opening: str | None = None
    style_profile: dict = Field(default_factory=dict)
    address_rules: list[dict] = Field(default_factory=list)
    length_target: dict = Field(default_factory=dict)


class ReviseOutput(StrictModel):
    ops: list[ParagraphOp] = Field(default_factory=list)
    selection_replacement: str | None = None
    addressed_finding_ids: list[str] = Field(default_factory=list)
    new_entities: list[dict] = Field(default_factory=list)
    resettle_required: bool = False
    rationale: str = ""
    usage: Usage = Field(default_factory=Usage)
