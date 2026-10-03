from __future__ import annotations

from typing import Protocol


class ContextPort(Protocol):
    async def get_context(self, work_id: str, chapter_no: int) -> dict: ...
