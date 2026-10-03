from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkStatus = Literal["draft", "ready", "archived"]
ContinuityStatus = Literal["ok", "blocked_needs_resync", "stale_from"]
AutowriteMode = Literal["auto", "review_each", "review_every_k"]
WizardStep = Literal[
    "basics", "brief", "foundation", "address_rules", "event_outline", "writing_config", "review"
]


class WorkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    language: Literal["vi"] = "vi"
    genre: str | None = Field(default=None, max_length=80)
    genre_label_custom: str | None = Field(default=None, max_length=120)
    wizard_step: WizardStep | None = "basics"

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        import unicodedata

        normalized = unicodedata.normalize("NFC", value).strip()
        if not normalized:
            raise ValueError("title_empty")
        return normalized


class WorkPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    genre: str | None = Field(default=None, max_length=80)
    genre_label_custom: str | None = Field(default=None, max_length=120)
    brief: str | None = None
    target_chapters: int | None = Field(default=None, ge=1)
    chapter_length_min: int | None = Field(default=None, ge=1)
    chapter_length_max: int | None = Field(default=None, ge=1)
    autowrite_mode_default: AutowriteMode | None = None
    review_every_k: int | None = Field(default=None, ge=1)
    max_repair_rounds: int | None = Field(default=None, ge=0)
    budget_daily_usd: float | None = Field(default=None, gt=0)
    budget_daily_tokens: int | None = Field(default=None, ge=1)
    cover_asset_id: str | None = None
    wizard_step: WizardStep | None = None
    wizard_completed_steps: list[WizardStep] | None = None
    status: WorkStatus | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        import unicodedata

        normalized = unicodedata.normalize("NFC", value).strip()
        if not normalized:
            raise ValueError("title_empty")
        return normalized


class StyleProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vocab_register: Literal["han_viet", "balanced", "thuan_viet"]
    dialogue_style: Literal["dash", "quotes"]
    dialogue_dash_char: Literal["\u2013", "\u2014"] | None
    tone_mark_style: Literal["old", "new"]
    punctuation_rules: dict[str, Any]
    banned_phrases: list[str]
    voice: str | None
    voice_samples: list[str]
    revision: int


class StyleProfileIn(BaseModel):
    expected_revision: int = Field(ge=1)
    vocab_register: Literal["han_viet", "balanced", "thuan_viet"]
    dialogue_style: Literal["dash", "quotes"]
    dialogue_dash_char: Literal["\u2013", "\u2014"] | None = None
    tone_mark_style: Literal["old", "new"]
    punctuation_rules: dict[str, Any] = Field(default_factory=dict)
    banned_phrases: list[str] = Field(default_factory=list)
    voice: str | None = None
    voice_samples: list[str] = Field(default_factory=list, max_length=2)

    @field_validator("voice_samples")
    @classmethod
    def validate_voice_samples(cls, samples: list[str]) -> list[str]:
        if any(len(sample) > 2000 for sample in samples):
            raise ValueError("voice_sample_too_long")
        return samples

    @field_validator("dialogue_dash_char")
    @classmethod
    def validate_dialogue_dash_char(cls, value: str | None, info):
        if info.data.get("dialogue_style") == "quotes" and value is not None:
            raise ValueError("dash_character_requires_dash_dialogue")
        return value


class WorkOut(BaseModel):
    id: str
    project_id: str
    title: str
    language: Literal["vi"]
    genre: str | None
    genre_label_custom: str | None
    status: WorkStatus
    brief: str | None
    target_chapters: int | None
    chapter_length_min: int
    chapter_length_max: int
    autowrite_mode_default: AutowriteMode
    review_every_k: int | None
    max_repair_rounds: int | None
    budget_daily_usd: float | None
    budget_daily_tokens: int | None
    continuity_status: ContinuityStatus
    continuity_chapter_no: int | None
    continuity_reason: dict[str, Any] | None
    cover_asset_id: str | None
    wizard_step: WizardStep | None
    wizard_completed_steps: list[WizardStep]
    last_opened_at: str | None
    revision: int
    created_at: str
    updated_at: str
    style_profile: StyleProfileOut | None = None


class WorkBadge(BaseModel):
    kind: str
    label_key: str
    params: dict[str, Any] = Field(default_factory=dict)


class WorkListItem(BaseModel):
    id: str
    title: str
    genre: str | None
    genre_label: str | None
    status: WorkStatus
    continuity_status: ContinuityStatus
    continuity_chapter_no: int | None
    continuity_reason: dict[str, Any] | None
    committed_chapters: int
    target_chapters: int | None
    job: dict[str, Any] | None = None
    badge: WorkBadge
    cost_total_usd: float | None = None
    cover_url: str | None = None
    last_opened_at: str | None
    updated_at: str


class WorkListResponse(BaseModel):
    items: list[WorkListItem]
    next_cursor: str | None


class GenreDefaults(BaseModel):
    vocab_register: Literal["han_viet", "balanced", "thuan_viet"]
    dialogue_style: Literal["dash", "quotes"]
    tone_mark_style: Literal["old", "new"]
    chapter_length_min: int
    chapter_length_max: int


class GenrePresetOut(BaseModel):
    key: str
    label: str
    description: str
    defaults: GenreDefaults
