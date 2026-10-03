from types import SimpleNamespace

import pytest

from writestory_be.modules.works.domain import (
    FoundationReadiness,
    FoundationReadinessPort,
    validate_ready_transition,
)


class ReadyFoundation(FoundationReadinessPort):
    async def check(self, work_id: str) -> FoundationReadiness:
        return FoundationReadiness(True, [])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("title", "", "title"),
        ("genre", None, "genre"),
        ("brief", " ", "brief"),
        ("target_chapters", 0, "target_chapters"),
        ("chapter_length_max", 2000, "chapter_length"),
    ],
)
async def test_ready_transition_reports_missing_work_fields(field, value, expected):
    work = SimpleNamespace(
        id="work-id",
        title="Title",
        genre="urban",
        genre_label_custom=None,
        brief="Brief",
        target_chapters=10,
        chapter_length_min=2500,
        chapter_length_max=3500,
    )
    setattr(work, field, value)
    assert expected in await validate_ready_transition(work, ReadyFoundation())


@pytest.mark.asyncio
async def test_ready_transition_requires_foundation():
    work = SimpleNamespace(
        id="work-id",
        title="Title",
        genre="urban",
        genre_label_custom=None,
        brief="Brief",
        target_chapters=10,
        chapter_length_min=2500,
        chapter_length_max=3500,
    )
    assert await validate_ready_transition(work, FoundationReadinessPort()) == ["foundation"]
