from typing import Protocol

from writestory_ai.contracts.events import StepProgress, TokenDelta
from writestory_ai.contracts.usage import Usage


class ProgressSink(Protocol):
    """BE triển khai port này để chuyển tiến độ AI thành job events (F01)."""

    async def on_step(self, progress: StepProgress) -> None: ...

    async def on_token(self, delta: TokenDelta) -> None: ...

    async def on_usage(self, step: str, usage: Usage) -> None: ...
