from writestory_ai.contracts.state import (
    EventState,
    FactState,
    HookState,
    Location,
    ParagraphEvidence,
    StateDelta,
    StoryState,
)
from writestory_ai.state.apply import apply_delta, state_hash
from writestory_ai.state.validate import validate_delta


def _state():
    return StoryState.model_validate(
        {
            "work_id": "w",
            "chapter_no": 0,
            "story_time": {"label": "Mở đầu", "ordinal": 0},
            "characters": [{"id": "c1", "status": "alive", "condition": "khỏe"}],
        }
    )


def test_delta_is_pure_and_hashes_new_state():
    state = _state()
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="user",
        ops=[{"op": "character.update", "character_id": "c1", "condition": "mệt"}],
    )
    updated, digest = apply_delta(state, delta)
    assert state.characters[0].condition == "khỏe"
    assert updated.characters[0].condition == "mệt"
    assert digest == state_hash(updated)


def test_reducer_resolves_temporary_character_and_location_ids_in_order():
    state = _state()
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="user",
        ops=[
            {"op": "location.add", "location": {"id": "new:location:1", "name": "Rừng"}},
            {
                "op": "character.add",
                "character": {"id": "new:character:1", "name": "Tân binh"},
                "location_id": "new:location:1",
            },
        ],
    )
    updated, _ = apply_delta(state, delta)
    added = next(
        character for character in updated.characters if character.id.startswith("character:")
    )
    assert added.location_id == updated.locations[0].id


def test_validation_rejects_dead_character_movement():
    state = _state()
    state.characters[0].status = "dead"
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="user",
        ops=[{"op": "character.move", "character_id": "c1", "to_location_id": "loc"}],
    )
    result = validate_delta(state, delta)
    assert not result.valid and any(i.code == "V04" for i in result.errors)


def test_validator_covers_time_address_location_event_and_overdue_hook_rules():
    state = _state()
    state.locations.append(Location(id="l1", name="A"))
    state.events.append(EventState(story_event_id="e2", depends_on=["e1"]))
    state.hooks.append(HookState(id="h1", title="hook", opened_at=0, due_by=1))
    state_hash_value = state_hash(state)
    delta = StateDelta(
        work_id="w",
        chapter_no=3,
        base_state_chapter=0,
        base_state_hash=state_hash_value,
        source="user",
        ops=[
            {"op": "time.advance", "to": {"label": "Lùi", "ordinal": -1}},
            {
                "op": "address.change",
                "speaker_id": "c1",
                "listener_id": "c2",
                "self_term": "ta",
                "address_term": "ngươi",
            },
            {"op": "character.move", "character_id": "c1", "to_location_id": "missing"},
            {"op": "character.learn", "character_id": "c1", "fact_id": "missing-fact"},
            {"op": "event.done", "story_event_id": "e2"},
        ],
    )
    result = validate_delta(state, delta)
    assert {x.code for x in result.errors} >= {"V03", "V05", "V10", "V11", "V12"}
    assert any(x.code == "V14" and x.severity == "major" for x in result.warnings)


def test_pipeline_evidence_requires_exact_candidate_quote():
    state = _state()
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="pipeline",
        ending_state={"story_time": {"label": "Mở đầu", "ordinal": 0}, "last_scene_summary": "Kết"},
        ops=[
            {
                "op": "character.update",
                "character_id": "c1",
                "condition": "mệt",
                "evidence": {
                    "kind": "paragraph",
                    "chapter_no": 1,
                    "paragraph_id": "abcdefgh",
                    "quote": "mệt",
                },
            }
        ],
    )
    result = validate_delta(state, delta, paragraphs={"abcdefgh": "Anh vẫn khỏe."})
    assert not result.valid and any(x.code == "V08" for x in result.errors)


def test_validator_covers_closed_hook_secret_fact_closed_fact_and_self_relationship():
    state = _state()
    state.hooks.append(HookState(id="closed", title="Resolved", status="resolved", opened_at=0))
    state.facts.append(
        FactState(
            id="secret",
            subject="villain",
            predicate="identity",
            object="X",
            is_secret=True,
            valid_from=0,
            evidence=ParagraphEvidence(chapter_no=1, paragraph_id="abcdefgh", quote="ẩn danh"),
        )
    )
    state.facts.append(
        FactState(
            id="closed-fact",
            subject="hero",
            predicate="name",
            object="A",
            valid_from=0,
            valid_until=1,
            evidence=ParagraphEvidence(chapter_no=1, paragraph_id="abcdefgh", quote="tên"),
        )
    )
    delta = StateDelta(
        work_id="w",
        chapter_no=2,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="user",
        ops=[
            {"op": "hook.advance", "hook_id": "closed", "note": "tiến triển"},
            {"op": "fact.close", "fact_id": "closed-fact"},
            {
                "op": "relationship.set",
                "a": "c1",
                "b": "c1",
                "kind": "other",
                "category": "other",
                "intensity": 0,
            },
        ],
            knowledge_uses=[
                {
                    "character_id": "c1",
                    "fact_id": "secret",
                    "evidence": {
                        "chapter_no": 2,
                        "paragraph_id": "abcdefgh",
                        "quote": "ẩn danh",
                    },
                }
            ],
    )
    result = validate_delta(state, delta, paragraphs={"abcdefgh": "Một bí mật ẩn danh."})
    assert {issue.code for issue in result.errors} >= {"V06", "V07", "V09", "V15"}


def test_ending_state_cannot_include_a_dead_character():
    state = _state()
    state.characters[0].status = "dead"
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="pipeline",
        ending_state={
            "story_time": state.story_time,
            "present": [{"character_id": "c1"}],
            "last_scene_summary": "Kết",
        },
    )
    result = validate_delta(state, delta)
    assert any(issue.code == "V13" for issue in result.errors)


def test_validator_checks_order_dependent_time_and_duplicate_event_ops():
    state = _state()
    state.events.append(EventState(story_event_id="e1"))
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="user",
        ops=[
            {"op": "time.advance", "to": {"label": "Ngày 2", "ordinal": 2}},
            {"op": "time.advance", "to": {"label": "Ngày 1", "ordinal": 1}},
            {"op": "event.done", "story_event_id": "e1"},
            {"op": "event.done", "story_event_id": "e1"},
        ],
    )
    result = validate_delta(state, delta)
    assert sum(issue.code == "V05" for issue in result.errors) == 1
    assert sum(issue.code == "V10" for issue in result.errors) == 1
