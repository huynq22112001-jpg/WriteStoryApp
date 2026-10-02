from pydantic import BaseModel, Field


class StepProgress(BaseModel):
    """Tiến độ một bước pipeline; BE chuyển thành event `job.step` (Plan §23.1.C)."""

    step: str
    attempt: int = 1
    round: int | None = None
    max_rounds: int | None = None
    progress: float | None = Field(default=None, ge=0.0, le=1.0)


class TokenDelta(BaseModel):
    """Đoạn văn bản mới của candidate; `offset` là vị trí ký tự (code point) trong candidate."""

    candidate_id: str
    step: str
    offset: int = Field(ge=0)
    text: str
