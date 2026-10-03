import json

import pytest

from writestory_ai.contracts.foundation import FoundationInput
from writestory_ai.contracts.generation import StreamDone, TextDelta
from writestory_ai.contracts.usage import Usage
from writestory_ai.evaluators.foundation_checks import check_foundation
from writestory_ai.prompts.loader import PromptRegistry
from writestory_ai.workflows.longform.foundation import run_stage


class ScriptedProvider:
    name = "scripted"

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.requests = []

    async def stream(self, request):
        self.requests.append(request)
        output = self.outputs.pop(0)
        text, reason = output if isinstance(output, tuple) else (output, "end_turn")
        if text:
            yield TextDelta(text=text)
        yield StreamDone(
            stop_reason=reason,
            usage=Usage(input_tokens=1, output_tokens=max(1, len(text) // 4)),
        )


class Checkpoints:
    def __init__(self):
        self.parts = []

    async def save(self, name, _payload):
        self.parts.append(name)


def frame_part(volumes=None):
    return {
        "story_frame": {
            "premise": "Một người tìm lại ký ức.",
            "setting": "Thành phố ven sông.",
            "tone": "ấm áp",
            "themes": ["gia đình"],
            "main_conflict": "Mất trí nhớ",
            "ending_direction": "Hòa giải",
        },
        "volume_map": volumes
        or [
            {
                "volume_no": 1,
                "title": "Khởi đầu",
                "chapter_from": 1,
                "chapter_to": 2,
                "arc_goal": "Tìm manh mối",
            }
        ],
        "book_rules": [{"key": "magic", "rule": "Không có phép thuật", "kind": "world"}],
        "author_intent": {"long_term": "Hòa giải", "current_focus": "Gặp lại"},
    }


def cast_part():
    return {
        "characters": [
            {"temp_id": "c1", "name": "Lâm Phong", "role_kind": "protagonist", "is_main": True},
            {"temp_id": "c2", "name": "Hàn Vũ", "role_kind": "friend", "is_main": True},
        ],
        "relationships": [{"a": "c1", "b": "c2", "kind": "bạn bè", "intensity": 3}],
        "locations": [{"temp_id": "l1", "name": "Bến sông"}],
        "opening": {
            "story_time_label": "Chiều đầu thu",
            "location_temp_id": "l1",
            "present_character_ids": ["c1", "c2"],
        },
    }


def address_part():
    return {
        "rules": [
            {
                "speaker": "c1",
                "listener": "c2",
                "self_term": "tôi",
                "address_term": "cậu",
                "from_chapter": 1,
            },
            {
                "speaker": "c2",
                "listener": "c1",
                "self_term": "tớ",
                "address_term": "cậu",
                "from_chapter": 1,
            },
        ]
    }


def event_part(volume_no, event_id, chapter, depends_on=None):
    return {
        "volume_no": volume_no,
        "events": [
            {
                "temp_id": event_id,
                "summary": f"Sự kiện {event_id}",
                "planned_chapter": chapter,
                "depends_on": depends_on or [],
            }
        ],
    }


def foundation_input(stage="frame", **kwargs):
    return FoundationInput(
        work_id="w",
        genre="urban",
        genre_label="Đô thị",
        brief="Hai người bạn gặp lại nhau.",
        target_chapters=2,
        stage=stage,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_foundation_runs_frame_cast_address_and_volume_events_with_checkpoints():
    prompt_registry = PromptRegistry()
    checkpoints = Checkpoints()
    frame = await run_stage(
        foundation_input(),
        ScriptedProvider(
            json.dumps(
                frame_part(
                    [
                        {
                            "volume_no": 1,
                            "title": "Quyển 1",
                            "chapter_from": 1,
                            "chapter_to": 1,
                            "arc_goal": "Mở",
                        },
                        {
                            "volume_no": 2,
                            "title": "Quyển 2",
                            "chapter_from": 2,
                            "chapter_to": 2,
                            "arc_goal": "Khép",
                        },
                    ]
                ),
                ensure_ascii=False,
            ),
            json.dumps(cast_part(), ensure_ascii=False),
        ),
        model="mock",
        prompts=prompt_registry,
        checkpoint=checkpoints,
    )
    assert set(frame.parts) == {"frame_core", "cast"}
    assert checkpoints.parts == ["frame_core", "cast"]

    address = await run_stage(
        foundation_input(
            "address_rules",
            previous_parts={"frame_core": frame.parts["frame_core"], "cast": frame.parts["cast"]},
        ),
        ScriptedProvider(json.dumps(address_part(), ensure_ascii=False)),
        model="mock",
        prompts=prompt_registry,
    )
    assert address.parts["address_rules"]["rules"]
    assert not any(w.code == "address_missing_pair" for w in address.warnings)

    event_input = foundation_input(
        "event_outline",
        previous_parts={
            "frame_core": frame.parts["frame_core"],
            "cast": frame.parts["cast"],
            "address_rules": address.parts["address_rules"],
        },
    )
    event_result = await run_stage(
        event_input,
        ScriptedProvider(
            json.dumps(event_part(1, "e1", 1), ensure_ascii=False),
            json.dumps(event_part(2, "e2", 2, ["e1"]), ensure_ascii=False),
            json.dumps({"hooks": []}, ensure_ascii=False),
        ),
        model="mock",
        prompts=prompt_registry,
    )
    assert event_result.parts["events_v1"]["events"][0]["temp_id"] == "e1"
    assert event_result.parts["events_v2"]["events"][0]["depends_on"] == ["e1"]
    assert not any(
        w.code in {"dangling_dependency", "event_density"} for w in event_result.warnings
    )
    assert event_result.seed_state is not None
    assert event_result.seed_state.chapter_no == 0
    assert event_result.seed_state.story_time.label == "Chiều đầu thu"
    assert {event.story_event_id for event in event_result.seed_state.events} == {"e1", "e2"}
    assert all(character.in_last_scene for character in event_result.seed_state.characters)


@pytest.mark.asyncio
async def test_foundation_repairs_invalid_json_once_and_supports_schema_capability():
    valid_frame = json.dumps(frame_part(), ensure_ascii=False)
    provider = ScriptedProvider(
        "not json", valid_frame, json.dumps(cast_part(), ensure_ascii=False)
    )
    await run_stage(foundation_input(), provider, model="mock", prompts=PromptRegistry())
    assert len(provider.requests) == 3
    assert "not json" in provider.requests[1].messages[0].content

    structured = ScriptedProvider(valid_frame, json.dumps(cast_part(), ensure_ascii=False))
    await run_stage(
        foundation_input(),
        structured,
        model="mock",
        prompts=PromptRegistry(),
        capabilities={"structured_outputs": True},
    )
    assert structured.requests[0].response_schema is not None


@pytest.mark.asyncio
async def test_foundation_splits_truncated_volume_and_refusal_is_typed():
    prior = {"frame_core": frame_part(), "cast": cast_part(), "address_rules": address_part()}
    provider = ScriptedProvider(
        ("{", "max_tokens"),
        json.dumps(event_part(1, "e1", 1), ensure_ascii=False),
        json.dumps(event_part(1, "e2", 2, ["e1"]), ensure_ascii=False),
        json.dumps({"hooks": []}, ensure_ascii=False),
    )
    result = await run_stage(
        foundation_input("event_outline", previous_parts=prior),
        provider,
        model="mock",
        prompts=PromptRegistry(),
    )
    assert [event["temp_id"] for event in result.parts["events_v1"]["events"]] == ["e1", "e2"]
    assert len(provider.requests) == 4

    refused = ScriptedProvider(("", "refusal"))
    with pytest.raises(Exception) as error:
        await run_stage(foundation_input(), refused, model="mock", prompts=PromptRegistry())
    assert getattr(error.value, "code", None) == "PROVIDER_REFUSAL"


def test_foundation_checks_report_cycles_duplicate_aliases_missing_address_and_due_hooks():
    request = foundation_input()
    parts = {
        "frame_core": frame_part(),
        "cast": {
            **cast_part(),
            "characters": [
                {
                    "temp_id": "c1",
                    "name": "Lâm Phong",
                    "aliases": [{"text": "Nam"}],
                    "is_main": True,
                },
                {"temp_id": "c2", "name": "Lam Phong", "aliases": [], "is_main": True},
            ],
        },
        "address_rules": {"rules": []},
        "events_v1": {
            "events": [
                {"temp_id": "e1", "planned_chapter": 1, "depends_on": ["e2"]},
                {"temp_id": "e2", "planned_chapter": 1, "depends_on": ["e1"]},
            ]
        },
        "hooks": {"hooks": [{"temp_id": "h1", "due_by_chapter": 3}]},
    }
    codes = {warning.code for warning in check_foundation(request, parts)}
    assert {
        "duplicate_name",
        "address_missing_pair",
        "event_dependency_cycle",
        "hook_due_out_of_range",
        "event_density",
    } <= codes
