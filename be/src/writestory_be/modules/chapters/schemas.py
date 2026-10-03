from typing import Any, Literal

from pydantic import BaseModel, Field


class ChapterCreate(BaseModel):
    chapter_no: int | None = Field(default=None, ge=1)
    title: str = Field(default="", max_length=200)


class ReorderIn(BaseModel):
    chapter_ids: list[str]


class WorkingCopyIn(BaseModel):
    doc_json: dict[str, Any]
    base_revision_id: str | None = None
    client_session_id: str | None = None
    client_seq: int = Field(default=0, ge=0)


class SnapshotIn(BaseModel):
    expected_revision: int | None = Field(default=None, ge=0)
    reason: Literal[
        "leave_chapter",
        "idle",
        "manual_snapshot",
        "before_ai_accept",
        "after_ai_accept",
        "before_restore",
        "full_replace",
    ] = "manual_snapshot"


class ReplaceIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    doc_json: dict[str, Any] | None = None
    expected_revision: int = Field(ge=0)


class RestoreIn(BaseModel):
    expected_revision: int = Field(ge=0)


class ChapterOut(BaseModel):
    id: str
    work_id: str
    chapter_no: int
    title: str
    status: str
    state_applied: bool
    revision_count: int
    current_revision_id: str | None
    syllable_count: int
    char_count: int


class RevisionOut(BaseModel):
    id: str
    chapter_id: str
    revision_no: int
    parent_revision_id: str | None
    source: str
    reason: str
    doc_json: dict[str, Any]
    plain_text: str
    paragraphs: list[dict[str, Any]]
    content_hash: str
    syllable_count: int
    char_count: int
    created_at: str
