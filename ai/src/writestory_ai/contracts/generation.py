from typing import Literal

from pydantic import BaseModel, Field

from writestory_ai.contracts.usage import Usage

Effort = Literal["low", "medium", "high", "xhigh", "max"]
StopReason = Literal["end_turn", "max_tokens", "refusal"]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GenerationRequest(BaseModel):
    """Một lời gọi sinh văn bản. `effort=None` = không gửi tham số, dùng mặc định provider (Plan §7.1)."""

    model: str
    messages: list[Message]
    system: str | None = None
    max_tokens: int = Field(default=4096, gt=0)
    effort: Effort | None = None


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
