from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LanguageFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str
    kind: str
    severity: Literal["blocker", "major", "minor"]
    confidence: Literal["high", "medium", "low"] = "high"
    paragraph_id: str | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    quote: str = Field(max_length=200)
    message_key: str
    params: dict[str, Any] = Field(default_factory=dict)
    suggestion: str | None = None
    needs_confirmation: bool = False


class ParagraphInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str
    text: str


class CheckContext(BaseModel):
    """Host supplied, persistence-free input shared by deterministic language checks."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    work_id: str
    chapter_no: int = Field(ge=1)
    genre_preset: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)
    paragraphs: list[ParagraphInput]
    canon_characters: list[dict[str, Any]] = Field(default_factory=list)
    canon_locations: list[dict[str, Any]] = Field(default_factory=list)
    address_rules: list[dict[str, Any]] = Field(default_factory=list)
    relationship_events: list[dict[str, Any]] = Field(default_factory=list)
    present_character_ids: list[str] = Field(default_factory=list)
    declared_new_names: list[str] = Field(default_factory=list)
