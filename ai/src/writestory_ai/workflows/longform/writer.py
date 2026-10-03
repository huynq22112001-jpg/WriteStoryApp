from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from writestory_ai.contracts.errors import OutputEmptyError, OutputTruncatedError
from writestory_ai.contracts.events import TokenDelta
from writestory_ai.contracts.generation import (
    GenerationRequest,
    GenerationResult,
    Message,
    StreamDone,
    TextDelta,
)
from writestory_ai.contracts.longform import DraftCandidate
from writestory_ai.ports.provider import TextProvider


class WriterOutput(BaseModel):
    candidate: DraftCandidate | None
    waiting_user: bool = False
    reason_code: str | None = None
    usage: dict = {}


async def write_chapter(
    provider: TextProvider,
    *,
    model: str,
    plan: str,
    handoff: str,
    tail_text: str,
    instruction: str = "",
    max_tokens: int = 4096,
    max_continuations: int = 2,
    paragraph_id_factory: Callable[[], str] | None = None,
    progress=None,
) -> WriterOutput:
    if max_continuations < 0 or max_continuations > 2:
        raise ValueError("max_continuations must be between 0 and 2")
    parts: list[str] = []
    usage = None
    stop_reason = "end_turn"
    offset = 0
    for _continuation in range(max_continuations + 1):
        prompt = (
            f"Kế hoạch:\n{plan}\n\nMối nối chương trước:\n{handoff}"
            f"\n\nVăn bản cuối chương trước:\n{tail_text}\n\nYêu cầu:\n{instruction}"
        )
        if parts:
            prompt += (
                "\n\nViết tiếp chính xác từ điểm dừng, không lặp lại đoạn trước:\n"
                + parts[-1][-1200:]
            )
        request = GenerationRequest(
            model=model, max_tokens=max_tokens, messages=[Message(role="user", content=prompt)]
        )
        pieces = []
        done = None
        async for event in provider.stream(request):
            if isinstance(event, TextDelta):
                pieces.append(event.text)
                if progress is not None:
                    await progress.on_token(
                        TokenDelta(
                            candidate_id="draft", step="write", offset=offset, text=event.text
                        )
                    )
                offset += len(event.text)
            elif isinstance(event, StreamDone):
                done = event
        if done is None:
            raise RuntimeError("Provider stream ended without StreamDone")
        text_chunk = "".join(pieces)
        if not text_chunk.strip() and done.stop_reason != "refusal":
            raise OutputEmptyError()
        result = GenerationResult(text=text_chunk, stop_reason=done.stop_reason, usage=done.usage)
        usage = result.usage if usage is None else usage + result.usage
        if result.stop_reason == "refusal":
            return WriterOutput(
                candidate=None,
                waiting_user=True,
                reason_code="PROVIDER_REFUSAL",
                usage=usage.model_dump(),
            )
        parts.append(result.text)
        stop_reason = result.stop_reason
        if stop_reason != "max_tokens":
            break
    if stop_reason == "max_tokens":
        raise OutputTruncatedError("Reached maximum continuation count")
    text = "\n\n".join(x.strip() for x in parts if x.strip())
    paragraph_texts = [p.strip() for p in text.split("\n\n") if p.strip()]
    ids = iter(range(1, len(paragraph_texts) + 1))
    factory = paragraph_id_factory or (lambda: f"{next(ids):08x}")
    paragraphs = [{"paragraph_id": factory(), "text": p} for p in paragraph_texts]
    return WriterOutput(
        candidate=DraftCandidate(
            candidate_id="draft",
            paragraphs=paragraphs,
            stop_reason=stop_reason,
            continuations=max(0, len(parts) - 1),
        ),
        usage=usage.model_dump() if usage else {},
    )
