import json

import pytest

from writestory_ai.contracts.errors import (
    OutputTruncatedError,
    ProviderRefusalError,
    StructuredOutputInvalidError,
)
from writestory_ai.contracts.revise import ReviseInput, ReviseOutput
from writestory_ai.contracts.state import StoryState
from writestory_ai.prompts.loader import PromptRegistry
from writestory_ai.providers.mock import MockScenario, MockTextProvider
from writestory_ai.workflows.longform.revise import apply_revision, create_revision


def revision_input(*, scope=None, mode="spot_fix"):
    return ReviseInput(
        work_id="w",
        chapter_no=1,
        mode=mode,
        scope=scope or {"type": "paragraphs", "paragraph_ids": ["abcdefgh"]},
        author_instruction="Sửa câu cho rõ.",
        paragraphs=[
            {"paragraph_id": "abcdefgh", "text": "Câu sai.", "editable": True},
            {"paragraph_id": "ijklmnop", "text": "Đoạn khóa.", "editable": False},
        ],
        state_before=StoryState(
            work_id="w", chapter_no=0, story_time={"label": "Mở đầu", "ordinal": 0}
        ),
    )


def test_revise_applies_only_editable_scope_and_splices_single_selection():
    request = revision_input()
    output = ReviseOutput(
        ops=[{"paragraph_id": "abcdefgh", "action": "replace", "text": "Câu đúng."}]
    )
    changed = apply_revision(request, output)
    assert changed[0].text == "Câu đúng."
    assert changed[1].text == "Đoạn khóa."

    selected = revision_input(
        scope={
            "type": "selection",
            "paragraph_ids": ["abcdefgh"],
            "selection": {"paragraph_id": "abcdefgh", "start": 4, "end": 7},
        }
    )
    output = ReviseOutput(selection_replacement="hay")
    assert apply_revision(selected, output)[0].text == "Câu hay."


@pytest.mark.asyncio
async def test_revise_repairs_invalid_scope_once_and_rejects_if_still_out_of_scope():
    request = revision_input()
    provider = MockTextProvider(
        MockScenario(
            text=json.dumps(
                {"ops": [{"paragraph_id": "ijklmnop", "action": "replace", "text": "Sai."}]}
            )
        )
    )
    fixed = []

    def fix_scope(_raw, _errors):
        fixed.append(True)
        return {"ops": [{"paragraph_id": "abcdefgh", "action": "replace", "text": "Đã sửa."}]}

    output = await create_revision(
        provider,
        model="mock",
        request=request,
        prompts=PromptRegistry(),
        json_fix=fix_scope,
    )
    assert len(fixed) == 1
    assert apply_revision(request, output)[0].text == "Đã sửa."

    malicious = MockTextProvider(
        MockScenario(
            text=json.dumps(
                {"ops": [{"paragraph_id": "ijklmnop", "action": "replace", "text": "Sửa khóa"}]}
            )
        )
    )
    with pytest.raises(StructuredOutputInvalidError):
        await create_revision(
            malicious,
            model="mock",
            request=request,
            prompts=PromptRegistry(),
            json_fix=lambda *_: {
                "ops": [
                    {"paragraph_id": "ijklmnop", "action": "replace", "text": "Vẫn ngoài phạm vi."}
                ]
            },
        )


@pytest.mark.asyncio
async def test_revise_uses_structured_capability_and_surfaces_provider_failures():
    class CaptureProvider(MockTextProvider):
        request = None

        async def stream(self, request):
            self.request = request
            async for event in super().stream(request):
                yield event

    payload = {"ops": [{"paragraph_id": "abcdefgh", "action": "replace", "text": "Mới."}]}
    structured = CaptureProvider(MockScenario(text=json.dumps(payload, ensure_ascii=False)))
    await create_revision(
        structured,
        model="mock",
        request=revision_input(),
        prompts=PromptRegistry(),
        capabilities={"structured_outputs": True},
    )
    assert structured.request.response_schema == ReviseOutput.model_json_schema()

    with pytest.raises(ProviderRefusalError):
        await create_revision(
            MockTextProvider(MockScenario(refusal=True)),
            model="mock",
            request=revision_input(),
            prompts=PromptRegistry(),
        )
    with pytest.raises(OutputTruncatedError):
        await create_revision(
            MockTextProvider(MockScenario(text="{}", truncate_at_chars=1)),
            model="mock",
            request=revision_input(),
            prompts=PromptRegistry(),
        )


@pytest.mark.asyncio
async def test_rework_requires_host_check_for_completed_events_and_requests_resettle():
    request = revision_input(mode="rework")
    request.completed_event_ids = ["event-done"]
    response = json.dumps(
        {"ops": [{"paragraph_id": "abcdefgh", "action": "replace", "text": "Viết lại."}]},
        ensure_ascii=False,
    )
    with pytest.raises(StructuredOutputInvalidError):
        await create_revision(
            MockTextProvider(MockScenario(text=response)),
            model="mock",
            request=request,
            prompts=PromptRegistry(),
        )

    output = await create_revision(
        MockTextProvider(MockScenario(text=response)),
        model="mock",
        request=request,
        prompts=PromptRegistry(),
        rework_validator=lambda _request, _output: True,
    )
    assert output.resettle_required
