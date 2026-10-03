from __future__ import annotations

from typing import Literal

from pydantic import Field

from writestory_ai.contracts.state import StoryState, StrictModel
from writestory_ai.contracts.usage import Usage


class FoundationInput(StrictModel):
    work_id: str
    language: str = "vi"
    genre: str
    genre_label: str = ""
    brief: str
    target_chapters: int = Field(ge=1)
    chapter_length_min: int = Field(default=2500, ge=1)
    chapter_length_max: int = Field(default=3500, ge=1)
    style: dict = Field(default_factory=dict)
    stage: Literal["frame", "address_rules", "event_outline"] = "frame"
    parts: list[str] | None = None
    accepted: dict = Field(default_factory=dict)
    previous_parts: dict[str, dict] = Field(default_factory=dict)
    instruction: str | None = None
    models: dict[str, dict] = Field(default_factory=dict)


class FoundationWarning(StrictModel):
    code: str
    path: str
    message: str


class StoryFrame(StrictModel):
    premise: str
    setting: str
    tone: str
    themes: list[str] = Field(default_factory=list)
    main_conflict: str
    ending_direction: str


class VolumeMapEntry(StrictModel):
    volume_no: int = Field(ge=1)
    title: str
    chapter_from: int = Field(ge=1)
    chapter_to: int = Field(ge=1)
    arc_goal: str


class BookRule(StrictModel):
    key: str
    rule: str
    kind: Literal["world", "power_system", "taboo", "style"]
    rationale: str = ""


class AuthorIntent(StrictModel):
    long_term: str
    current_focus: str


class FrameCoreOutput(StrictModel):
    story_frame: StoryFrame
    volume_map: list[VolumeMapEntry] = Field(default_factory=list)
    book_rules: list[BookRule] = Field(default_factory=list)
    author_intent: AuthorIntent


class FoundationAlias(StrictModel):
    text: str
    kind: str = "nickname"


class FoundationCharacter(StrictModel):
    temp_id: str
    name: str
    aliases: list[FoundationAlias] = Field(default_factory=list)
    role_kind: str
    is_main: bool = False
    description: str = ""
    personality: str = ""
    goals: list[str] = Field(default_factory=list)
    background: str = ""
    initial_condition: str = ""
    initial_location_temp_id: str | None = None


class FoundationRelationship(StrictModel):
    a: str
    b: str
    kind: str
    intensity: int = Field(ge=1, le=5)


class FoundationLocation(StrictModel):
    temp_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class FoundationOpening(StrictModel):
    story_time_label: str
    location_temp_id: str | None = None
    present_character_ids: list[str] = Field(default_factory=list)


class CastOutput(StrictModel):
    characters: list[FoundationCharacter] = Field(default_factory=list)
    relationships: list[FoundationRelationship] = Field(default_factory=list)
    locations: list[FoundationLocation] = Field(default_factory=list)
    opening: FoundationOpening


class AddressRule(StrictModel):
    speaker: str
    listener: str
    self_term: str
    address_term: str
    from_chapter: int = Field(ge=1)
    until_chapter: int | None = Field(default=None, ge=1)
    phase_label: str | None = None
    rationale: str = ""


class AddressRulesOutput(StrictModel):
    rules: list[AddressRule] = Field(default_factory=list)


class OutlineEvent(StrictModel):
    temp_id: str
    summary: str
    detail: str = ""
    planned_chapter: int = Field(ge=1)
    depends_on: list[str] = Field(default_factory=list)
    storyline: str | None = None


class EventOutlineVolumeOutput(StrictModel):
    volume_no: int = Field(ge=1)
    events: list[OutlineEvent] = Field(default_factory=list)


class FoundationHook(StrictModel):
    temp_id: str
    title: str
    description: str = ""
    opened_at_chapter: int = Field(ge=1)
    due_by_chapter: int = Field(ge=1)
    payoff_plan: str
    priority: int = Field(ge=1, le=3)
    related_event_temp_id: str | None = None


class HooksOutput(StrictModel):
    hooks: list[FoundationHook] = Field(default_factory=list)


class FoundationStageResult(StrictModel):
    stage: Literal["frame", "address_rules", "event_outline"]
    parts: dict[str, dict] = Field(default_factory=dict)
    warnings: list[FoundationWarning] = Field(default_factory=list)
    usage: list[Usage] = Field(default_factory=list)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    seed_state: StoryState | None = None
