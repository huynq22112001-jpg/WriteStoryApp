from typing import Literal

from pydantic import BaseModel, Field

from writestory_ai.contracts.usage import Usage

Effort = Literal["low", "medium", "high", "xhigh", "max"]
StopReason = Literal["end_turn", "max_tokens", "refusal"]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GenerationRequest(BaseModel):
    """Một lời gọi sinh văn bản.

    `effort=None` nghĩa là không gửi tham số và dùng mặc định provider (Plan §7.1).
    """

    model: str
    messages: list[Message]
    system: str | None = None
    max_tokens: int = Field(default=4096, gt=0)
    effort: Effort | None = None
    response_schema: dict | None = None
    json_mode: bool = False


class PinnedRole(BaseModel):
    provider_id: str
    model_id: str
    effort: Effort | None = None
    max_tokens: int = Field(gt=0)
    capabilities: dict = Field(default_factory=dict)


class PinnedRoles(BaseModel):
    planner: PinnedRole
    writer: PinnedRole
    checker: PinnedRole
    reviewer: PinnedRole
    summary: PinnedRole


class WriteSettings(BaseModel):
    length_min: int = 2500
    length_max: int = 3500
    length_tolerance: float = 0.1
    length_hard_floor_ratio: float = 0.7
    max_repair_rounds: int = Field(default=2, ge=0)
    repair_token_cap: int = Field(default=4000, ge=1)
    repair_max_changed_ratio: float = 0.25
    repair_include_major: bool = True
    max_continuations: int = Field(default=2, ge=0, le=2)
    tail_min: int = 1000
    tail_max: int = 2000
    outline_review_every_k: int = 10
    arc_summary_every: int = 10
    allow_early_ending: bool = False
    target_chapters: int | None = None


class ResumePoint(BaseModel):
    step: str
    round: int = 0
    plan_id: str | None = None
    candidate_id: str | None = None
    settle_ref: str | None = None
    reason: str | None = None


class GenerationInput(BaseModel):
    work_id: str
    chapter_no: int
    job_id: str
    pinned: PinnedRoles
    bible_revision: int = 0
    prompt_manifest_version: str = ""
    settings: WriteSettings = Field(default_factory=WriteSettings)
    brief: str | None = None
    instruction: str | None = None
    mode: Literal["auto", "review_each", "review_every_k"] = "review_each"
    resume: ResumePoint | None = None


class TextDelta(BaseModel):
    type: Literal["text"] = "text"
    text: str


class StreamDone(BaseModel):
    type: Literal["done"] = "done"
    stop_reason: StopReason
    usage: Usage


StreamEvent = TextDelta | StreamDone


class GenerationResult(BaseModel):
    text: str
    stop_reason: StopReason
    usage: Usage
