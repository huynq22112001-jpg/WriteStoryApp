from __future__ import annotations

from typing import Literal

from pydantic import Field

from writestory_ai.contracts.state import EndingState, StateDelta, StrictModel
from writestory_ai.contracts.usage import Usage


class PacingBudget(StrictModel):
    events_remaining: int = Field(ge=0)
    chapters_remaining: int = Field(ge=0)
    ratio: float = Field(ge=0)
    recommended_events: tuple[int, int] = (0, 3)
    assigned_events: list[str] = Field(default_factory=list)
    warning: Literal["none", "crowded", "dragging", "no_material"] = "none"


class PlanBeat(StrictModel):
    order: int = Field(ge=1)
    summary: str
    required_event_ids: list[str] = Field(default_factory=list)
    hook_ids: list[str] = Field(default_factory=list)
    target_units: int = Field(ge=0)


class ChapterPlan(StrictModel):
    title: str = ""
    goal: str
    pov_character_id: str | None = None
    opening: dict
    beats: list[PlanBeat]
    required_event_ids: list[str] = Field(default_factory=list)
    hooks_to_advance: list[str] = Field(default_factory=list)
    hooks_to_resolve: list[str] = Field(default_factory=list)
    hook_deferrals: list[dict] = Field(default_factory=list)
    new_characters: list[dict] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    ending_hint: str = ""
    allowed_ending: bool = False
    target_length: dict
    pacing: PacingBudget


class DraftCandidate(StrictModel):
    candidate_id: str
    kind: Literal["draft", "repair", "author"] = "draft"
    parent_id: str | None = None
    round: int = 0
    paragraphs: list[dict]
    stop_reason: str = "end_turn"
    continuations: int = 0
    length: dict = Field(default_factory=dict)


class LLMValidation(StrictModel):
    issues: list[dict] = Field(default_factory=list)


class SeamResult(StrictModel):
    aspects: dict = Field(default_factory=dict)
    verdict: Literal["pass", "fail"]
    notes: list[str] = Field(default_factory=list)


class ReviewResult(StrictModel):
    findings: list[dict] = Field(default_factory=list)
    confirmations: list[dict] = Field(default_factory=list)
    plan_coverage: dict = Field(default_factory=dict)
    premature_ending: bool = False


class RepairOps(StrictModel):
    ops: list[dict] = Field(default_factory=list)
    notes: str = ""


class OutlineProposal(StrictModel):
    changes: list[dict] = Field(default_factory=list)
    pacing_assessment: str = ""


class PipelineResult(StrictModel):
    status: Literal["ready", "needs_user"]
    reason_code: str | None = None
    candidate: DraftCandidate
    delta: StateDelta | None = None
    ending_state: EndingState | None = None
    findings: list[dict] = Field(default_factory=list)
    plan_id: str = ""
    measurements: dict = Field(default_factory=dict)
    usage_by_step: dict[str, Usage] = Field(default_factory=dict)
