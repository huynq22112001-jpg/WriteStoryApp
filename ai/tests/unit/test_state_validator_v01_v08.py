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
            "characters": [{"id": "c1"}, {"id": "c2"}],
            "locations": [{"id": "l1", "name": "Thành"}],
            "facts": [
                {
                    "id": "secret-1",
                    "subject": "c1",
                    "predicate": "biết",
                    "object": "bí mật",
                    "valid_from": 0,
                    "is_secret": True,
                    "evidence": {
                        "kind": "paragraph",
                        "chapter_no": 1,
                        "paragraph_id": "paragraph1",
                        "quote": "bí mật",
                    },
                }
            ],
            "hooks": [{"id": "hook-1", "title": "Lời hứa", "opened_at": 0}],
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


def codes(result):
    return {issue.code for issue in result.errors}


def test_v01_schema_accepts_valid_delta_and_rejects_invalid_shape():
    current = state()
    valid = delta(current, [{"op": "character.update", "character_id": "c1"}])
    from writestory_ai.contracts.state import StateDelta

    StateDelta.model_validate(valid)
    valid["ops"] = [{"op": "character.update", "character_id": "c1", "unexpected": True}]
    with pytest.raises(ValidationError):
        StateDelta.model_validate(valid)


def test_v02_accepts_matching_base_and_rejects_stale_chapter_or_hash():
    current = state()
    good = delta(current, [])
    assert validate_delta(current, type_delta(good)).valid
    stale = {**good, "base_state_chapter": 2}
    assert "V02" in codes(validate_delta(current, type_delta(stale)))
    stale_hash = {**good, "base_state_hash": "stale"}
    assert "V02" in codes(validate_delta(current, type_delta(stale_hash)))


def type_delta(payload):
    from writestory_ai.contracts.state import StateDelta

    return StateDelta.model_validate(payload)


def test_v03_accepts_prior_declarations_and_rejects_unknown_or_forward_refs():
    current = state()
    ordered = delta(
        current,
        [
            {"op": "location.add", "location": {"id": "new:location:1", "name": "Rừng"}},
            {
                "op": "character.add",
                "character": {"id": "new:character:1", "name": "Người mới"},
                "location_id": "new:location:1",
            },
            {"op": "character.update", "character_id": "new:character:1", "condition": "mệt"},
            {
                "op": "fact.add",
                "fact": {
                    "id": "new:fact:1",
                    "subject": "c1",
                    "predicate": "nhìn thấy",
                    "object": "dấu vết",
                    "evidence": {
                        "kind": "user",
                        "note": "Ghi chú tác giả",
                        "at": "2026-10-03T00:00:00Z",
                    },
                },
            },
            {"op": "character.learn", "character_id": "c1", "fact_id": "new:fact:1"},
        ],
    )
    assert "V03" not in codes(validate_delta(current, type_delta(ordered)))

    unknown = delta(
        current, [{"op": "character.move", "character_id": "absent", "to_location_id": "l1"}]
    )
    assert "V03" in codes(validate_delta(current, type_delta(unknown)))
    unknown_knowledge = delta(
        current,
        [],
        knowledge_uses=[
            {
                "character_id": "absent",
                "fact_id": "absent-fact",
                "evidence": {"chapter_no": 1, "paragraph_id": "paragraph1", "quote": "text"},
            }
        ],
    )
    result = validate_delta(current, type_delta(unknown_knowledge), {"paragraph1": "text"})
    assert "V03" in codes(result)
    forward_ref = delta(
        current,
        [
            {"op": "character.update", "character_id": "new:character:1"},
            {"op": "character.add", "character": {"id": "new:character:1", "name": "Người mới"}},
        ],
    )
    assert "V03" in codes(validate_delta(current, type_delta(forward_ref)))


def test_v04_blocks_dead_character_changes_and_warns_on_explicit_resurrection():
    current = state()
    current.characters[0].status = "dead"
    move = delta(current, [{"op": "character.move", "character_id": "c1", "to_location_id": "l1"}])
    assert "V04" in codes(validate_delta(current, type_delta(move)))

    resurrection = delta(
        current,
        [
            {
                "op": "character.update",
                "character_id": "c1",
                "status": "alive",
                "override_reason": "Hồi sinh",
            }
        ],
    )
    result = validate_delta(current, type_delta(resurrection))
    assert result.valid
    assert any(issue.code == "V04" and issue.severity == "major" for issue in result.warnings)


def test_v05_accepts_forward_time_and_rejects_unmarked_flashback():
    current = state()
    forward = delta(current, [{"op": "time.advance", "to": {"label": "Ngày hai", "ordinal": 2}}])
    assert "V05" not in codes(validate_delta(current, type_delta(forward)))
    backward = delta(current, [{"op": "time.advance", "to": {"label": "Hôm qua", "ordinal": -1}}])
    assert "V05" in codes(validate_delta(current, type_delta(backward)))
    flashback = delta(
        current,
        [{"op": "time.advance", "to": {"label": "Hôm qua", "ordinal": -1}, "flashback": True}],
    )
    assert "V05" not in codes(validate_delta(current, type_delta(flashback)))


def test_v06_accepts_later_hook_deferral_and_rejects_closed_or_non_later_hook():
    current = state()
    valid = delta(
        current, [{"op": "hook.defer", "hook_id": "hook-1", "new_due_by": 4, "reason": "Đổi lịch"}]
    )
    assert "V06" not in codes(validate_delta(current, type_delta(valid)))
    invalid_due = delta(
        current, [{"op": "hook.defer", "hook_id": "hook-1", "new_due_by": 1, "reason": "Đổi lịch"}]
    )
    assert "V06" in codes(validate_delta(current, type_delta(invalid_due)))
    current.hooks[0].status = "resolved"
    closed = delta(current, [{"op": "hook.advance", "hook_id": "hook-1", "note": "Tiến triển"}])
    assert "V06" in codes(validate_delta(current, type_delta(closed)))


def test_v07_allows_known_secret_and_rejects_secret_used_before_learning():
    current = state()
    use = {
        "character_id": "c2",
        "fact_id": "secret-1",
        "evidence": {"chapter_no": 1, "paragraph_id": "paragraph1", "quote": "bí mật"},
    }
    before_learning = delta(current, [], knowledge_uses=[use])
    result = validate_delta(current, type_delta(before_learning), {"paragraph1": "Câu có bí mật."})
    assert "V07" in codes(result)

    learned_first = delta(
        current,
        [{"op": "character.learn", "character_id": "c2", "fact_id": "secret-1"}],
        knowledge_uses=[use],
    )
    result = validate_delta(current, type_delta(learned_first), {"paragraph1": "Câu có bí mật."})
    assert "V07" not in codes(result)


def test_v08_requires_candidate_paragraph_and_accepts_normalized_quote():
    current = state()
    evidence_op = {
        "op": "character.update",
        "character_id": "c1",
        "condition": "mệt",
        "evidence": {
            "kind": "paragraph",
            "chapter_no": 1,
            "paragraph_id": "paragraph1",
            "quote": "Hoàng",
        },
    }
    good = delta(current, [evidence_op])
    assert "V08" not in codes(
        validate_delta(current, type_delta(good), {"paragraph1": "Hoàng bước vào."})
    )
    bad_quote = {**evidence_op, "evidence": {**evidence_op["evidence"], "quote": "không có"}}
    bad = delta(current, [bad_quote])
    assert "V08" in codes(
        validate_delta(current, type_delta(bad), {"paragraph1": "Hoàng bước vào."})
    )

    pipeline_missing_evidence = {
        **delta(current, [{"op": "character.update", "character_id": "c1"}], source="pipeline"),
        "ending_state": {
            "story_time": current.story_time.model_dump(),
            "last_scene_summary": "Kết.",
        },
    }
    assert "V08" in codes(validate_delta(current, type_delta(pipeline_missing_evidence), {}))
