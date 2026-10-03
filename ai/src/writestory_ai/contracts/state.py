from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StoryTime(StrictModel):
    label: str
    ordinal: float
    day_index: int | None = None
    time_of_day: Literal["sang", "trua", "chieu", "toi", "dem"] | None = None


class ParagraphEvidence(StrictModel):
    kind: Literal["paragraph"] = "paragraph"
    chapter_no: int = Field(ge=1)
    paragraph_id: str = Field(min_length=1)
    quote: str = Field(min_length=1, max_length=200)


class UserEvidence(StrictModel):
    kind: Literal["user"] = "user"
    note: str = Field(min_length=1)
    at: datetime


Evidence = Annotated[ParagraphEvidence | UserEvidence, Field(discriminator="kind")]


class CharacterState(StrictModel):
    id: str
    status: Literal["alive", "dead", "missing", "unknown"] = "alive"
    location_id: str | None = None
    condition: str = ""
    goals: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)
    inventory: list[str] = Field(default_factory=list)
    in_last_scene: bool = False
    last_seen_chapter: int | None = None


class Relationship(StrictModel):
    a: str
    b: str
    kind: str
    category: Literal[
        "family", "mentor", "friend", "romance", "rival", "enemy", "political", "other"
    ]
    intensity: int = Field(ge=-3, le=3)
    since_chapter: int = Field(ge=0)


class FactState(StrictModel):
    id: str
    subject: str
    predicate: str
    object: str
    valid_from: int
    valid_until: int | None = None
    is_secret: bool = False
    evidence: Evidence


class HookState(StrictModel):
    id: str
    title: str
    status: Literal["open", "progressing", "deferred", "resolved", "superseded"] = "open"
    opened_at: int
    due_by: int | None = None
    last_advanced: int | None = None
    payoff_plan: str = ""
    priority: Literal[1, 2, 3] = 2


class EventState(StrictModel):
    story_event_id: str
    status: Literal["planned", "done", "moved", "dropped"] = "planned"
    planned_chapter: int | None = None
    done_chapter: int | None = None
    depends_on: list[str] = Field(default_factory=list)


class Location(StrictModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class StoryState(StrictModel):
    schema_version: Literal[1] = 1
    work_id: str
    chapter_no: int = Field(ge=0)
    story_time: StoryTime
    characters: list[CharacterState] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    facts: list[FactState] = Field(default_factory=list)
    hooks: list[HookState] = Field(default_factory=list)
    events: list[EventState] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)


class PresentCharacter(StrictModel):
    character_id: str
    condition: str = ""
    emotion: str = ""
    doing: str = ""


class EndingState(StrictModel):
    location_id: str | None = None
    location_label: str = ""
    story_time: StoryTime
    present: list[PresentCharacter] = Field(default_factory=list)
    unfinished_actions: list[str] = Field(default_factory=list)
    dominant_emotion: str = ""
    pov_character_id: str | None = None
    last_scene_summary: str = Field(max_length=1000)


class StateOpBase(StrictModel):
    evidence: Evidence | None = None
    reason: str | None = None
    in_flashback: bool = False


class CharacterSpec(StrictModel):
    id: str
    name: str
    aliases: list[dict] = Field(default_factory=list)
    role_note: str = ""


class FactSpec(StrictModel):
    id: str
    subject: str
    predicate: str
    object: str
    is_secret: bool = False
    evidence: Evidence


class HookSpec(StrictModel):
    id: str
    title: str
    payoff_plan: str = ""
    due_by: int | None = None
    priority: Literal[1, 2, 3] = 2


class LocationSpec(StrictModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class CharacterAdd(StateOpBase):
    op: Literal["character.add"]
    character: CharacterSpec
    location_id: str | None = None


class CharacterUpdate(StateOpBase):
    op: Literal["character.update"]
    character_id: str
    status: Literal["alive", "dead", "missing", "unknown"] | None = None
    condition: str | None = None
    goals_set: list[str] | None = None
    goals_add: list[str] = Field(default_factory=list)
    goals_remove: list[str] = Field(default_factory=list)
    inventory_add: list[str] = Field(default_factory=list)
    inventory_remove: list[str] = Field(default_factory=list)
    override_reason: str | None = None


class CharacterMove(StateOpBase):
    op: Literal["character.move"]
    character_id: str
    to_location_id: str


class CharacterLearn(StateOpBase):
    op: Literal["character.learn"]
    character_id: str
    fact_id: str


class RelationshipSet(StateOpBase):
    op: Literal["relationship.set"]
    a: str
    b: str
    kind: str
    category: Literal[
        "family", "mentor", "friend", "romance", "rival", "enemy", "political", "other"
    ]
    intensity: int = Field(ge=-3, le=3)


class AddressChange(StateOpBase):
    op: Literal["address.change"]
    speaker_id: str
    listener_id: str
    self_term: str
    address_term: str


class FactAdd(StateOpBase):
    op: Literal["fact.add"]
    fact: FactSpec


class FactClose(StateOpBase):
    op: Literal["fact.close"]
    fact_id: str


class HookOpen(StateOpBase):
    op: Literal["hook.open"]
    hook: HookSpec


class HookAdvance(StateOpBase):
    op: Literal["hook.advance"]
    hook_id: str
    note: str


class HookResolve(StateOpBase):
    op: Literal["hook.resolve"]
    hook_id: str
    as_superseded: bool = False


class HookDefer(StateOpBase):
    op: Literal["hook.defer"]
    hook_id: str
    new_due_by: int
    reason: str


class EventDone(StateOpBase):
    op: Literal["event.done"]
    story_event_id: str


class EventMove(StateOpBase):
    op: Literal["event.move"]
    story_event_id: str
    to_chapter: int
    reason: str


class EventDrop(StateOpBase):
    op: Literal["event.drop"]
    story_event_id: str
    reason: str


class TimeAdvance(StateOpBase):
    op: Literal["time.advance"]
    to: StoryTime
    flashback: bool = False


class LocationAdd(StateOpBase):
    op: Literal["location.add"]
    location: LocationSpec


StateOp = Annotated[
    CharacterAdd
    | CharacterUpdate
    | CharacterMove
    | CharacterLearn
    | RelationshipSet
    | AddressChange
    | FactAdd
    | FactClose
    | HookOpen
    | HookAdvance
    | HookResolve
    | HookDefer
    | EventDone
    | EventMove
    | EventDrop
    | TimeAdvance
    | LocationAdd,
    Field(discriminator="op"),
]


class KnowledgeUse(StrictModel):
    character_id: str
    fact_id: str
    evidence: ParagraphEvidence


class StateDelta(StrictModel):
    schema_version: Literal[1] = 1
    work_id: str
    chapter_no: int = Field(ge=1)
    base_state_chapter: int = Field(ge=0)
    base_state_hash: str
    source: Literal["pipeline", "user"]
    candidate_id: str | None = None
    ops: list[StateOp] = Field(default_factory=list)
    knowledge_uses: list[KnowledgeUse] = Field(default_factory=list)
    ending_state: EndingState | None = None

    @model_validator(mode="after")
    def validate_source_evidence(self):
        if self.source == "pipeline" and self.ending_state is None:
            raise ValueError("pipeline StateDelta requires ending_state")
        if self.source == "user" and self.candidate_id is not None:
            raise ValueError("user StateDelta cannot have candidate_id")
        for op in self.ops:
            if isinstance(op.evidence, UserEvidence) and self.source != "user":
                raise ValueError("UserEvidence is valid only for user StateDelta")
        return self


class TailText(StrictModel):
    text: str
    paragraph_ids: list[str] = Field(default_factory=list)
    token_estimate: int = Field(ge=0)
