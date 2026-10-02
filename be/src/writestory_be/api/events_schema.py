"""Envelope của luồng sự kiện toàn cục (Plan §23.1.C, §24 D10).

Payload chi tiết theo từng `type` do tính năng phát ra định nghĩa (F10, F11, F12…); ở base,
`payload` là object tự do. Đổi nghĩa trường có sẵn → tăng `EVENT_SCHEMA_VERSION`.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

EVENT_SCHEMA_VERSION = 1

EventType = Literal[
    "job.queued",
    "job.state",
    "job.step",
    "token.delta",
    "stream.tail",
    "candidate.ready",
    "candidate.updated",
    "finding.added",
    "finding.updated",
    "chapter.committed",
    "work.continuity",
    "queue.changed",
    "provider.status",
    "usage.updated",
    "vault.status",
    "notification.created",
    "backend.notice",
]

# Event không lưu, không replay; chỉ gửi cho client đăng ký truyện tương ứng.
TRANSIENT_TYPES: frozenset[str] = frozenset({"token.delta"})


class EventEnvelope(BaseModel):
    v: int = EVENT_SCHEMA_VERSION
    seq: int
    ts: str
    type: EventType
    work_id: str | None = None
    job_id: str | None = None
    chapter_no: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    persisted: bool = Field(default=True, exclude=True)
