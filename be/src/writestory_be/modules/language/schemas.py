from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SlopEntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    pattern: str = Field(min_length=1, max_length=200)
    is_regex: bool = False
    scope: Literal["paragraph_start", "anywhere"] = "anywhere"
    max_per_1000_units: float | None = Field(default=None, ge=0)
    note: str = Field(default="", max_length=500)


class SlopListPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    additions: list[SlopEntryIn] = Field(default_factory=list, max_length=500)
    disabled: list[str] = Field(default_factory=list, max_length=500)


class SlopListOut(BaseModel):
    builtin: list[dict[str, Any]]
    user: dict[str, Any]
    version: int


class NormalizeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=1_000_000)
    mode: Literal["paste", "save"]
    work_id: str | None = None


class NormalizeOut(BaseModel):
    text: str
    changes: list[dict[str, Any]]
    legacy_encoding: dict[str, Any] | None = None


class ParagraphTextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str = Field(pattern=r"^[a-z0-9]{8}$")
    text: str


class TextCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str | None = None
    paragraphs: list[ParagraphTextIn] | None = None
    checks: list[str] | None = None


class LanguageFindingOut(BaseModel):
    check_id: str
    kind: str
    severity: str
    confidence: str
    paragraph_id: str | None = None
    start: int | None = None
    end: int | None = None
    quote: str
    message_key: str
    params: dict[str, Any]
    suggestion: str | None = None
    needs_confirmation: bool


class TextCheckOut(BaseModel):
    findings: list[LanguageFindingOut]
    length: dict[str, int]
