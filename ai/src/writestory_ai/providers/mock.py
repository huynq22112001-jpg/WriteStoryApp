"""Provider giả cho test, dev và spike R0 (tests/README.md "Mock provider", Plan §24 D23).

Nằm trong `src` để bản đóng gói spike dùng được; fixture test chỉ re-export.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from writestory_ai.contracts.errors import (
    AIError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderUnreachableError,
)
from writestory_ai.contracts.generation import (
    GenerationRequest,
    StreamDone,
    StreamEvent,
    TextDelta,
)
from writestory_ai.contracts.usage import Usage

DEFAULT_TEXT = (
    "Mưa đêm rơi lất phất trên mái hiên. Lâm Phong siết chặt chuôi kiếm, "
    "lắng nghe tiếng bước chân ngoài cổng."
)


@dataclass
class MockFailure:
    """Một lần thất bại trong `fail_sequence`: `kind` ∈ auth | unreachable | rate_limit | server."""

    kind: str
    retry_after: float | None = None


@dataclass
class MockScenario:
    text: str = DEFAULT_TEXT
    latency_ms: int = 0
    tokens_per_sec: float | None = None
    chunk_chars: int = 8
    fail_sequence: list[MockFailure] = field(default_factory=list)
    refusal: bool = False
    truncate_at_chars: int | None = None
    disconnect_after_chars: int | None = None


def _failure_to_error(failure: MockFailure) -> AIError:
    match failure.kind:
        case "auth":
            return ProviderAuthError("mock: sai API key")
        case "unreachable":
            return ProviderUnreachableError("mock: không kết nối được")
        case "rate_limit":
            return ProviderRateLimitError("mock: 429", retry_after=failure.retry_after)
        case "server":
            return ProviderServerError("mock: 500")
        case other:
            raise ValueError(f"MockFailure.kind không hợp lệ: {other}")


class MockTextProvider:
    name = "mock"

    def __init__(self, scenario: MockScenario | None = None) -> None:
        self.scenario = scenario or MockScenario()
        self.calls = 0

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamEvent]:
        sc = self.scenario
        call_index = self.calls
        self.calls += 1

        if sc.latency_ms:
            await asyncio.sleep(sc.latency_ms / 1000)
        if call_index < len(sc.fail_sequence):
            raise _failure_to_error(sc.fail_sequence[call_index])

        input_tokens = sum(len(m.content) for m in request.messages) // 4 + 1
        if sc.refusal:
            yield StreamDone(
                stop_reason="refusal",
                usage=Usage(input_tokens=input_tokens, output_tokens=0),
            )
            return

        text = sc.text
        stop_reason = "end_turn"
        if sc.truncate_at_chars is not None and sc.truncate_at_chars < len(text):
            text = text[: sc.truncate_at_chars]
            stop_reason = "max_tokens"

        delay = 0.0
        if sc.tokens_per_sec:
            # Ước lượng 4 ký tự ~ 1 token chỉ để mô phỏng nhịp stream.
            delay = (sc.chunk_chars / 4) / sc.tokens_per_sec

        sent = 0
        for start in range(0, len(text), sc.chunk_chars):
            if sc.disconnect_after_chars is not None and sent >= sc.disconnect_after_chars:
                raise ProviderUnreachableError("mock: mất kết nối giữa stream")
            chunk = text[start : start + sc.chunk_chars]
            sent += len(chunk)
            yield TextDelta(text=chunk)
            if delay:
                await asyncio.sleep(delay)

        yield StreamDone(
            stop_reason=stop_reason,
            usage=Usage(input_tokens=input_tokens, output_tokens=len(text) // 4 + 1),
        )
