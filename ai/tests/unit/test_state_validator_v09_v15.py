import pytest
from pydantic import ValidationError

from writestory_ai.contracts.state import StoryState
from writestory_ai.state.apply import state_hash
from writestory_ai.state.validate import validate_delta


def state() -> StoryState:
    return StoryState.model_validate(
        {
            "work_id": "work-1",
            "chapter_no": 0,
            "story_time": {"label": "Ngày đầu", "ordinal": 0},
            "characters": [
                {"id": "c1", "location_id": "l1"},
                {"id": "c2", "location_id": "l1"},
            ],
            "locations": [{"id": "l1", "name": "Thành"}],
            "facts": [
                {
                    "id": "fact-1",
                    "subject": "c1",
                    "predicate": "có",
                    "object": "nhẫn",
                    "valid_from": 0,
                    "evidence": {
                        "kind": "user",
                        "note": "Canon ban đầu",
                        "at": "2026-10-03T00:00:00Z",
                    },
                }
            ],
            "hooks": [{"id": "hook-1", "title": "Lời hứa", "opened_at": 0}],
            "events": [
                {"story_event_id": "event-1"},
                {"story_event_id": "event-2", "depends_on": ["event-1"]},
                {"story_event_id": "event-done", "status": "done"},
            ],
        }
    )


def delta(current: StoryState, ops: list[dict], **kwargs):
    return {
        "work_id": current.work_id,
        "chapter_no": 1,
        "base_state_chapter": current.chapter_no,
        "base_state_hash": state_hash(current),
        "source": "user",
        "ops": ops,
        **kwargs,
    }


def make_delta(payload):
    from writestory_ai.contracts.state import StateDelta

    return StateDelta.model_validate(payload)


def error_codes(result):
    return {issue.code for issue in result.errors}


def test_v09_warns_for_duplicate_active_fact_and_rejects_repeated_close():
    current = state()
    duplicate = delta(
        current,
        [
            {
                "op": "fact.add",
                "fact": {
                    "id": "new:fact:1",
                    "subject": "c1",
                    "predicate": "có",
                    "object": "nhẫn",
                    "evidence": {
                        "kind": "user",
                        "note": "Đã có trong state",
                        "at": "2026-10-03T00:00:00Z",
                    },
                },
            }
        ],
    )
    result = validate_delta(current, make_delta(duplicate))
    assert result.valid
    assert any(issue.code == "V09" and issue.severity == "warning" for issue in result.warnings)

    repeated_close = delta(
        current,
        [
            {"op": "fact.close", "fact_id": "fact-1"},
            {"op": "fact.close", "fact_id": "fact-1"},
        ],
    )
    assert "V09" in error_codes(validate_delta(current, make_delta(repeated_close)))


def test_v10_checks_event_dependency_order_duplicates_moves_and_drop():
    current = state()
    valid = delta(
        current,
        [
            {"op": "event.done", "story_event_id": "event-1"},
            {"op": "event.done", "story_event_id": "event-2"},
        ],
    )
    assert "V10" not in error_codes(validate_delta(current, make_delta(valid)))

    missing_dependency = delta(current, [{"op": "event.done", "story_event_id": "event-2"}])
    assert "V10" in error_codes(validate_delta(current, make_delta(missing_dependency)))
    repeated_done = delta(
        current,
        [
            {"op": "event.done", "story_event_id": "event-1"},
            {"op": "event.done", "story_event_id": "event-1"},
        ],
    )
    assert "V10" in error_codes(validate_delta(current, make_delta(repeated_done)))
    past_move = delta(
        current,
        [{"op": "event.move", "story_event_id": "event-1", "to_chapter": 1, "reason": "Dời"}],
    )
    assert "V10" in error_codes(validate_delta(current, make_delta(past_move)))
    drop_done = delta(
        current,
        [{"op": "event.drop", "story_event_id": "event-done", "reason": "Bỏ"}],
    )
    assert "V10" in error_codes(validate_delta(current, make_delta(drop_done)))


def test_v11_requires_relationship_change_for_address_change():
    current = state()
    address = {
        "op": "address.change",
        "speaker_id": "c1",
        "listener_id": "c2",
        "self_term": "ta",
        "address_term": "ngươi",
    }
    invalid = delta(current, [address])
    assert "V11" in error_codes(validate_delta(current, make_delta(invalid)))
    valid = delta(
        current,
        [
            {
                "op": "relationship.set",
                "a": "c1",
                "b": "c2",
                "kind": "đồng minh",
                "category": "friend",
                "intensity": 1,
            },
            address,
        ],
    )
    assert "V11" not in error_codes(validate_delta(current, make_delta(valid)))


def test_v12_accepts_prior_location_add_and_rejects_missing_location():
    current = state()
    valid = delta(
        current,
        [
            {"op": "location.add", "location": {"id": "new:location:1", "name": "Rừng"}},
            {"op": "character.move", "character_id": "c1", "to_location_id": "new:location:1"},
        ],
    )
    assert "V12" not in error_codes(validate_delta(current, make_delta(valid)))
    invalid = delta(
        current,
        [{"op": "character.move", "character_id": "c1", "to_location_id": "absent"}],
    )
    assert "V12" in error_codes(validate_delta(current, make_delta(invalid)))


def pipeline_delta(current: StoryState, ending_state: dict, ops: list[dict] | None = None):
    return make_delta(
        delta(
            current,
            ops or [],
            source="pipeline",
            ending_state=ending_state,
        )
    )


def test_v13_checks_living_present_time_and_warns_for_location_mismatch():
    current = state()
    good_end = {
        "story_time": current.story_time.model_dump(),
        "present": [{"character_id": "c1"}],
        "location_id": "l1",
        "last_scene_summary": "Kết cảnh.",
    }
    assert validate_delta(current, pipeline_delta(current, good_end)).valid

    dead = current.model_copy(deep=True)
    dead.characters[0].status = "dead"
    dead_end = {**good_end, "story_time": dead.story_time.model_dump()}
    assert "V13" in error_codes(validate_delta(dead, pipeline_delta(dead, dead_end)))

    wrong_time = {
        **good_end,
        "story_time": {"label": "Ngày khác", "ordinal": 3},
    }
    assert "V13" in error_codes(validate_delta(current, pipeline_delta(current, wrong_time)))

    wrong_location = {**good_end, "location_id": "other"}
    result = validate_delta(current, pipeline_delta(current, wrong_location))
    assert result.valid
    assert any(issue.code == "V13" and issue.severity == "warning" for issue in result.warnings)


def test_v14_reports_overdue_hook_as_major_warning_without_blocking():
    current = state()
    current.hooks[0].due_by = 0
    overdue = delta(current, [])
    result = validate_delta(current, make_delta(overdue))
    assert result.valid
    assert any(issue.code == "V14" and issue.severity == "major" for issue in result.warnings)

    deferred = delta(
        current,
        [{"op": "hook.defer", "hook_id": "hook-1", "new_due_by": 4, "reason": "Lùi hạn"}],
    )
    assert not any(
        issue.code == "V14" for issue in validate_delta(current, make_delta(deferred)).warnings
    )

    current.hooks[0].status = "resolved"
    resolved = validate_delta(current, make_delta(overdue))
    assert not any(issue.code == "V14" for issue in resolved.warnings)


def test_v15_rejects_self_relationship_and_accepts_valid_relationship():
    current = state()
    self_relation = delta(
        current,
        [
            {
                "op": "relationship.set",
                "a": "c1",
                "b": "c1",
                "kind": "khác",
                "category": "other",
                "intensity": 0,
            }
        ],
    )
    assert "V15" in error_codes(validate_delta(current, make_delta(self_relation)))

    valid = delta(
        current,
        [
            {
                "op": "relationship.set",
                "a": "c1",
                "b": "c2",
                "kind": "đồng minh",
                "category": "friend",
                "intensity": -3,
            }
        ],
    )
    assert "V15" not in error_codes(validate_delta(current, make_delta(valid)))

    invalid_intensity = {
        **valid,
        "ops": [{**valid["ops"][0], "intensity": 4}],
    }
    with pytest.raises(ValidationError):
        make_delta(invalid_intensity)
