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
TRANSIENT_TYPES: frozenset[str] = frozenset({"token.delta", "stream.tail"})


class JobQueuedPayload(BaseModel):
    job_type: str
    priority: int = 0
    queue_position: int | None = None


class JobStatePayload(BaseModel):
    status: str
    wait_reason: str | None = None
    error: dict[str, Any] | None = None
    retry_at: str | None = None


class JobStepPayload(BaseModel):
    step: str
    attempt: int
    round: int | None = None
    max_rounds: int | None = None
    progress: float | None = Field(default=None, ge=0, le=1)


class TokenDeltaPayload(BaseModel):
    candidate_id: str
    step: str
    mode: Literal["full", "preview"]
    offset: int | None = None
    text: str | None = None
    tail: str | None = None


class StreamTailPayload(BaseModel):
    candidate_id: str
    step: str
    tail: str = Field(max_length=200)


class BackendNoticePayload(BaseModel):
    kind: str
    detail: dict[str, Any] = Field(default_factory=dict)


class VaultStatusPayload(BaseModel):
    state: Literal["absent", "locked", "unlocked"]
    mode: Literal["undecided", "vault", "session_only"]


PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "job.queued": JobQueuedPayload,
    "job.state": JobStatePayload,
    "job.step": JobStepPayload,
    "token.delta": TokenDeltaPayload,
    "stream.tail": StreamTailPayload,
    "backend.notice": BackendNoticePayload,
    "vault.status": VaultStatusPayload,
}


def validate_event_payload(event_type: str, payload: dict[str, Any]) -> BaseModel | dict[str, Any]:
    model = PAYLOAD_MODELS.get(event_type)
    return model.model_validate(payload) if model is not None else payload


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
