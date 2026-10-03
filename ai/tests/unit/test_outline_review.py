import pytest

from writestory_ai.contracts.longform import OutlineProposal
from writestory_ai.workflows.longform.outline_review import (
    apply_outline_proposal,
    review_outline_if_due,
    should_review_outline,
)


def test_review_outline_due_each_k_or_two_moved_events():
    assert should_review_outline(6, 3, 0)
    assert should_review_outline(4, 3, 2)
    assert not should_review_outline(4, 3, 1)


def test_outline_proposal_does_not_change_locked_event():
    events = [
        {"id": "locked", "status": "planned", "planned_chapter": 4, "locked": True},
        {"id": "open", "status": "planned", "planned_chapter": 4},
    ]
    result = apply_outline_proposal(
        OutlineProposal.model_validate({
            "changes": [
                {"story_event_id": "locked", "action": "drop"},
                {"story_event_id": "open", "action": "move", "to_chapter": 8},
            ]
        }),
        events,
    )
    by_id = {item["id"]: item for item in result}
    assert by_id["locked"]["status"] == "planned"
    assert by_id["open"]["planned_chapter"] == 8


@pytest.mark.asyncio
async def test_outline_evaluator_is_skipped_when_not_due_and_proposal_applied_when_due():
    events = [{"id": "e", "status": "planned", "planned_chapter": 2}]
    called = False

    async def evaluator(_events):
        nonlocal called
        called = True
        return {"changes": [{"story_event_id": "e", "action": "move", "to_chapter": 5}]}

    unchanged, proposal = await review_outline_if_due(
        chapter_no=2,
        every_k=3,
        moved_event_count=0,
        events=events,
        evaluator=evaluator,
    )
    assert unchanged == events and proposal is None and not called
    updated, proposal = await review_outline_if_due(
        chapter_no=3,
        every_k=3,
        moved_event_count=0,
        events=events,
        evaluator=evaluator,
    )
    assert proposal is not None and called
    assert updated[0]["planned_chapter"] == 5
