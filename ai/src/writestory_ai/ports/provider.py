from collections.abc import AsyncIterator
from typing import Protocol

from writestory_ai.contracts.generation import GenerationRequest, StreamEvent


class TextProvider(Protocol):
    """Adapter sinh văn bản. Lỗi được ném dưới dạng `AIError` có kiểu (contracts/errors.py).

    `stream` luôn kết thúc bằng đúng một `StreamDone`; refusal và cắt `max_tokens` được báo qua
    `StreamDone.stop_reason`, không ném lỗi; bước gọi quyết định xử lý (Plan §23.3 #3).
    """

    name: str

    def stream(self, request: GenerationRequest) -> AsyncIterator[StreamEvent]: ...
