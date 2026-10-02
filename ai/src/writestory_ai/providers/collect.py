from writestory_ai.contracts.errors import OutputEmptyError
from writestory_ai.contracts.generation import (
    GenerationRequest,
    GenerationResult,
    StreamDone,
    TextDelta,
)
from writestory_ai.ports.provider import TextProvider


async def collect(provider: TextProvider, request: GenerationRequest) -> GenerationResult:
    """Gom stream thành một kết quả. Output rỗng (không phải refusal) → `OutputEmptyError`."""
    parts: list[str] = []
    done: StreamDone | None = None
    async for event in provider.stream(request):
        if isinstance(event, TextDelta):
            parts.append(event.text)
        elif isinstance(event, StreamDone):
            done = event
    if done is None:
        raise OutputEmptyError("stream kết thúc mà không có StreamDone")
    text = "".join(parts)
    if not text.strip() and done.stop_reason != "refusal":
        raise OutputEmptyError()
    return GenerationResult(text=text, stop_reason=done.stop_reason, usage=done.usage)
