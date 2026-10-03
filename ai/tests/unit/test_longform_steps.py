import pytest

from writestory_ai.contracts.errors import (
    OutputTruncatedError,
    ProviderRefusalError,
    StructuredOutputInvalidError,
)
from writestory_ai.contracts.paragraphs import ParagraphText
from writestory_ai.contracts.state import EndingState, StateDelta, StoryState, StoryTime
from writestory_ai.prompts.loader import PromptRegistry
from writestory_ai.providers.mock import MockScenario, MockTextProvider
from writestory_ai.state.apply import state_hash
from writestory_ai.workflows.longform.planner import create_plan
from writestory_ai.workflows.longform.repair import RepairExhausted, repair_until_clear
from writestory_ai.workflows.longform.reviewer import review
from writestory_ai.workflows.longform.seam_check import check_seam
from writestory_ai.workflows.longform.settlement import create_settlement, parse_settlement
from writestory_ai.workflows.longform.summaries import summarize_chapter_with_provider
from writestory_ai.workflows.longform.validator import validate_candidate
from writestory_ai.workflows.longform.writer import write_chapter


@pytest.mark.asyncio
async def test_writer_includes_tail_and_handles_refusal_without_retry():
    class SpyProvider(MockTextProvider):
        last_request = None

        async def stream(self, request):
            self.last_request = request
            async for event in super().stream(request):
                yield event

    provider = SpyProvider(MockScenario(text="Một đoạn truyện."))
    result = await write_chapter(
        provider, model="mock", plan="plan", handoff="handoff", tail_text="tail context"
    )
    assert "tail context" in provider.last_request.messages[0].content
    assert result.candidate and result.candidate.paragraphs
    refused = MockTextProvider(MockScenario(refusal=True))
    waiting = await write_chapter(refused, model="mock", plan="p", handoff="h", tail_text="t")
    assert waiting.waiting_user and refused.calls == 1


@pytest.mark.asyncio
async def test_writer_limits_continuations_and_refusal_is_not_retried():
    provider = MockTextProvider(MockScenario(text="x" * 100, truncate_at_chars=10))
    with pytest.raises(OutputTruncatedError):
        await write_chapter(
            provider, model="mock", plan="p", handoff="h", tail_text="tail", max_continuations=1
        )
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_seam_evaluator_and_reviewer_severity_mapping():
    previous = EndingState(
        story_time=StoryTime(label="Đêm", ordinal=1), last_scene_summary="Kết thúc"
    )
    seam = await check_seam(
        previous, [], evaluator=lambda *_: {"verdict": "fail", "notes": ["mismatch"]}
    )
    assert seam.verdict == "fail"
    result = await review([], evaluator=lambda _: {"findings": [{"kind": "fact", "quote": "x"}]})
    assert result.findings[0]["severity"] == "blocker"


@pytest.mark.asyncio
async def test_reviewer_owns_severity_and_keeps_unconfirmed_address_pending():
    result = await review(
        [
            {"id": "slop-1", "kind": "slop", "severity": "blocker"},
            {
                "id": "address-1",
                "kind": "address",
                "confidence": "medium",
                "needs_confirmation": True,
            },
        ],
        evaluator=lambda _: {"findings": [], "confirmations": []},
    )
    by_id = {finding["id"]: finding for finding in result.findings}
    assert by_id["slop-1"]["severity"] == "minor"
    assert by_id["address-1"]["severity"] == "major"
    assert by_id["address-1"]["confirmation_pending"]


@pytest.mark.asyncio
async def test_repair_success_and_exhausted():
    paragraph = [ParagraphText(paragraph_id="abcdefgh", text="Sai.")]
    findings = [{"severity": "blocker", "paragraph_id": "abcdefgh"}]

    async def repairer(_paragraphs, _findings):
        return {"ops": [{"paragraph_id": "abcdefgh", "action": "replace", "text": "Đúng."}]}

    fixed, remaining = await repair_until_clear(
        paragraph, findings, repairer, lambda _paragraphs: [], max_rounds=1, max_changed_ratio=1
    )
    assert fixed[0].text == "Đúng." and not remaining
    with pytest.raises(RepairExhausted):
        await repair_until_clear(
            paragraph,
            findings,
            repairer,
            lambda _paragraphs: findings,
            max_rounds=1,
            max_changed_ratio=1,
        )


@pytest.mark.asyncio
async def test_repair_skips_non_blockers_and_rejects_ops_outside_finding_scope():
    paragraph = [
        ParagraphText(paragraph_id="abcdefgh", text="Sai."),
        ParagraphText(paragraph_id="ijklmnop", text="Giữ nguyên."),
    ]
    calls = []

    async def repairer(_paragraphs, _findings):
        calls.append(True)
        return {"ops": [{"paragraph_id": "ijklmnop", "action": "replace", "text": "Sai sửa."}]}

    original, warnings = await repair_until_clear(
        paragraph,
        [{"severity": "major", "paragraph_id": "abcdefgh"}],
        repairer,
        lambda _paragraphs: [],
    )
    assert original == paragraph and warnings == [{"severity": "major", "paragraph_id": "abcdefgh"}]
    assert not calls

    with pytest.raises(RepairExhausted, match="scope"):
        await repair_until_clear(
            paragraph,
            [{"severity": "blocker", "paragraph_id": "abcdefgh"}],
            repairer,
            lambda _paragraphs: [],
            max_changed_ratio=1,
        )


def test_settlement_parses_schema_and_rejects_invalid():
    valid = (
        '{"work_id":"w","chapter_no":1,"base_state_chapter":0,'
        '"base_state_hash":"h","source":"pipeline",'
        '"ops":[{"op":"character.update","character_id":"c1",'
        '"evidence":{"kind":"paragraph","chapter_no":1,'
        '"paragraph_id":"abcdefgh","quote":"Anh đi."}}],'
        '"ending_state":{"story_time":{"label":"Đêm","ordinal":1},'
        '"present":[{"character_id":"c1"}],"last_scene_summary":"Anh đi."}}'
    )
    parsed = parse_settlement(valid)
    assert parsed.source == "pipeline"
    assert parsed.ops[0].evidence.paragraph_id == "abcdefgh"
    assert parsed.ending_state.present[0].character_id == "c1"
    with pytest.raises(StructuredOutputInvalidError):
        parse_settlement("not json")
    missing_ending = valid.replace(
        ',"ending_state":{"story_time":{"label":"Đêm","ordinal":1},'
        '"present":[{"character_id":"c1"}],"last_scene_summary":"Anh đi."}',
        "",
    )
    with pytest.raises(StructuredOutputInvalidError):
        parse_settlement(missing_ending)
    wrong_source = valid.replace('"source":"pipeline"', '"source":"user"')
    with pytest.raises(StructuredOutputInvalidError):
        parse_settlement(wrong_source)


@pytest.mark.asyncio
async def test_settlement_surfaces_refusal_and_truncated_json_as_typed_errors():
    refusal = MockTextProvider(MockScenario(refusal=True))
    with pytest.raises(ProviderRefusalError):
        await create_settlement(
            refusal,
            model="mock",
            paragraphs="[p:abcdefgh] Một đoạn.",
            prompts=PromptRegistry(),
        )

    truncated = MockTextProvider(MockScenario(text='{"source":"pipeline"}', truncate_at_chars=4))
    with pytest.raises(OutputTruncatedError):
        await create_settlement(
            truncated,
            model="mock",
            paragraphs="[p:abcdefgh] Một đoạn.",
            prompts=PromptRegistry(),
        )


@pytest.mark.asyncio
async def test_summary_step_uses_versioned_vietnamese_prompt_and_mock_provider():
    raw = '{"chapter_no":3,"synopsis":"Nhân vật tìm được manh mối.","events":["manh mối"]}'
    provider = MockTextProvider(MockScenario(text=raw))
    summary = await summarize_chapter_with_provider(
        provider,
        model="mock",
        chapter_no=3,
        chapter_text="Một cảnh điều tra.",
        prompts=PromptRegistry(),
    )
    assert summary.chapter_no == 3 and summary.events == ["manh mối"]


@pytest.mark.asyncio
async def test_planner_and_settler_parse_structured_outputs_with_single_fix():
    plan_raw = (
        '{"goal":"Tìm manh mối","opening":{},"beats":[],"target_length":{"min":10,"max":20},'
        '"pacing":{"events_remaining":0,"chapters_remaining":1,"ratio":0,"recommended_events":[0,0]}}'
    )
    plan_provider = MockTextProvider(MockScenario(text=plan_raw))
    plan = await create_plan(
        plan_provider,
        model="mock",
        chapter_no=1,
        target_length=(10, 20),
        outline="outline",
        context="context",
        prompts=PromptRegistry(),
    )
    assert plan.goal == "Tìm manh mối"
    broken = MockTextProvider(MockScenario(text="not json"))
    repaired = await create_settlement(
        broken,
        model="mock",
        paragraphs="[p:12345678] text",
        prompts=PromptRegistry(),
        json_fix=lambda *_: {
            "work_id": "w",
            "chapter_no": 1,
            "base_state_chapter": 0,
            "base_state_hash": "h",
            "source": "user",
        },
    )
    assert repaired.work_id == "w" and broken.calls == 1


@pytest.mark.asyncio
async def test_settlement_uses_capability_schema_or_json_mode_and_repairs_once():
    class CaptureProvider(MockTextProvider):
        request = None

        async def stream(self, request):
            self.request = request
            async for item in super().stream(request):
                yield item

    valid = {
        "work_id": "w",
        "chapter_no": 1,
        "base_state_chapter": 0,
        "base_state_hash": "h",
        "source": "pipeline",
        "ops": [],
        "ending_state": {
            "story_time": {"label": "Đêm", "ordinal": 1},
            "last_scene_summary": "Kết cảnh",
        },
    }
    structured = CaptureProvider(
        MockScenario(text=__import__("json").dumps(valid, ensure_ascii=False))
    )
    await create_settlement(
        structured,
        model="mock",
        paragraphs="[p:abcdefgh] Anh đi.",
        prompts=PromptRegistry(),
        capabilities={"structured_outputs": True},
    )
    assert structured.request.response_schema == StateDelta.model_json_schema()
    assert not structured.request.json_mode

    fallback = CaptureProvider(MockScenario(text="not json"))
    repairs = []

    def fix_once(*_):
        repairs.append(True)
        return valid

    await create_settlement(
        fallback,
        model="mock",
        paragraphs="[p:abcdefgh] Anh đi.",
        prompts=PromptRegistry(),
        json_fix=fix_once,
        capabilities={"structured_outputs": False},
    )
    assert fallback.request.json_mode and fallback.request.response_schema is None
    assert len(repairs) == 1


@pytest.mark.asyncio
async def test_planner_repairs_a_plan_that_fails_deterministic_rules_once():
    raw_plan = {
        "goal": "Tiếp tục hành trình",
        "opening": {"present_character_ids": ["dead"]},
        "beats": [],
        "target_length": {"min": 10, "max": 20},
        "allowed_ending": True,
        "pacing": {
            "events_remaining": 0,
            "chapters_remaining": 1,
            "ratio": 0,
            "recommended_events": [0, 0],
        },
    }
    provider = MockTextProvider(
        MockScenario(text=__import__("json").dumps(raw_plan, ensure_ascii=False))
    )
    repaired_plan = dict(
        raw_plan, opening={"present_character_ids": ["alive"]}, allowed_ending=False
    )
    fixes = []

    def fixer(raw, errors):
        fixes.append(errors)
        return repaired_plan

    result = await create_plan(
        provider,
        model="mock",
        chapter_no=1,
        target_length=(10, 20),
        outline="",
        context="",
        prompts=PromptRegistry(),
        json_fix=fixer,
        validation_context={
            "available_event_ids": set(),
            "alive_character_ids": {"alive"},
            "target_length": (10, 20),
            "chapter_no": 1,
            "target_chapters": 10,
        },
    )
    assert result.opening["present_character_ids"] == ["alive"] and fixes


@pytest.mark.asyncio
async def test_llm_validator_runs_only_after_deterministic_validation_passes():
    state = StoryState(work_id="w", chapter_no=0, story_time={"label": "Start", "ordinal": 0})
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="pipeline",
        ending_state={"story_time": {"label": "Start", "ordinal": 0}, "last_scene_summary": "Kết"},
    )
    called = []
    deterministic, llm = await validate_candidate(
        state, delta, {}, llm_validator=lambda *_: called.append(True) or {"issues": []}
    )
    assert deterministic.valid and llm is not None and called


@pytest.mark.asyncio
async def test_llm_validator_discards_unverified_quotes_and_seam_requires_grounded_mismatch():
    state = StoryState(work_id="w", chapter_no=0, story_time={"label": "Start", "ordinal": 0})
    delta = StateDelta(
        work_id="w",
        chapter_no=1,
        base_state_chapter=0,
        base_state_hash=state_hash(state),
        source="pipeline",
        ending_state={"story_time": {"label": "Start", "ordinal": 0}, "last_scene_summary": "Kết"},
    )
    _, llm = await validate_candidate(
        state,
        delta,
        {"abcdefgh": "Cô bước vào sân."},
        llm_validator=lambda *_: {
            "issues": [
                {"type": "fact", "paragraph_id": "abcdefgh", "quote": "bước vào"},
                {"type": "fact", "paragraph_id": "abcdefgh", "quote": "câu không có"},
            ]
        },
    )
    assert llm is not None and [issue["quote"] for issue in llm.issues] == ["bước vào"]

    previous = EndingState(
        location_label="Bến sông",
        story_time=StoryTime(label="Đêm", ordinal=1),
        last_scene_summary="Kết",
    )
    opening = [{"paragraph_id": "abcdefgh", "text": "Hôm sau, họ vẫn ở bến sông."}]
    mismatch = await check_seam(
        previous,
        opening,
        evaluator=lambda *_: {
            "verdict": "fail",
            "aspects": {
                "location": {
                    "verdict": "mismatch",
                    "paragraph_id": "abcdefgh",
                    "quote": "ở bến sông",
                }
            },
        },
    )
    assert mismatch.verdict == "fail"
    unsupported = await check_seam(
        previous,
        opening,
        evaluator=lambda *_: {
            "verdict": "fail",
            "aspects": {
                "location": {
                    "verdict": "mismatch",
                    "paragraph_id": "abcdefgh",
                    "quote": "địa điểm bịa",
                }
            },
        },
    )
    assert unsupported.verdict == "pass"
