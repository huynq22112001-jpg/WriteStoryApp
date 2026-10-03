import pytest
from pydantic import ValidationError

from writestory_ai.contracts.state import StateDelta, StoryState


def test_delta_json_round_trip_with_discriminated_ops():
    delta = StateDelta.model_validate(
        {
            "work_id": "w",
            "chapter_no": 1,
            "base_state_chapter": 0,
            "base_state_hash": "abc",
            "source": "user",
            "ops": [
                {"op": "hook.defer", "hook_id": "h1", "new_due_by": 4, "reason": "Nhịp truyện"}
            ],
        }
    )
    assert StateDelta.model_validate_json(delta.model_dump_json()) == delta
    assert delta.ops[0].op == "hook.defer"


def test_event_planning_ops_require_reason_and_unknown_fields_fail():
    with pytest.raises(ValidationError):
        StateDelta.model_validate(
            {
                "work_id": "w",
                "chapter_no": 1,
                "base_state_chapter": 0,
                "base_state_hash": "x",
                "source": "pipeline",
                "ops": [{"op": "event.move", "story_event_id": "e", "to_chapter": 4}],
            }
        )
    with pytest.raises(ValidationError):
        StateDelta.model_validate(
            {
                "work_id": "w",
                "chapter_no": 1,
                "base_state_chapter": 0,
                "base_state_hash": "x",
                "source": "pipeline",
                "extra": 1,
            }
        )


def test_story_state_schema_is_strict_and_round_trips():
    state = StoryState.model_validate(
        {"work_id": "w", "chapter_no": 0, "story_time": {"label": "Mở đầu", "ordinal": 0}}
    )
    assert StoryState.model_validate_json(state.model_dump_json()) == state
