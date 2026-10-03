from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from writestory_ai.contracts.longform import (
    DraftCandidate,
    PipelineResult,
    ReviewResult,
    SeamResult,
)
from writestory_ai.workflows.longform.pipeline import STEPS, run_chapter


class Checkpoints:
    def __init__(self):
        self.names = []

    async def save(self, name, payload):
        self.names.append(name)


class Cancel:
    def is_cancelled(self):
        return False


class Limiter:
    def __init__(self):
        self.calls = 0

    @asynccontextmanager
    async def acquire(self, provider_id, *, estimated_tokens=0):
        self.calls += 1
        yield


@pytest.mark.asyncio
async def test_pipeline_runs_all_steps_checkpoints_and_uses_limiter_helper():
    inp = SimpleNamespace(work_id="w", chapter_no=1)
    context = SimpleNamespace(get_context=lambda *_: _async_value({"ok": True}))

    async def stage(values, call):
        if values.get("plan") is None:
            await call(lambda: _async_value("permitted"))
        return PipelineResult(
            status="ready", candidate=DraftCandidate(candidate_id="c", paragraphs=[])
        )

    steps = {name: stage for name in STEPS}
    checkpoints = Checkpoints()
    limiter = Limiter()
    result = await run_chapter(
        generation_input=inp,
        context_port=context,
        provider=object(),
        progress=None,
        checkpoint=checkpoints,
        cancel=Cancel(),
        limiter=limiter,
        provider_id="p",
        steps=steps,
    )
    assert result.status == "ready" and checkpoints.names == list(STEPS)
    assert limiter.calls >= 1


@pytest.mark.asyncio
async def test_pipeline_resume_runs_from_requested_checkpoint_and_requires_all_stages():
    calls = []

    def make_stage(name):
        async def stage(_values, _call):
            calls.append(name)
            if name == "summarize":
                return PipelineResult(
                    status="ready", candidate=DraftCandidate(candidate_id="c", paragraphs=[])
                )
            return name

        return stage

    class ResumableContext:
        async def get_context(self, *_):
            return {"loaded": True}

        async def load_checkpoint(self, *_):
            return {"plan": "reused"}

    callbacks = {name: make_stage(name) for name in STEPS}
    checkpoints = Checkpoints()
    result = await run_chapter(
        generation_input=SimpleNamespace(work_id="w", chapter_no=1),
        context_port=ResumableContext(),
        provider=object(),
        progress=None,
        checkpoint=checkpoints,
        cancel=Cancel(),
        limiter=Limiter(),
        provider_id="p",
        steps=callbacks,
        resume_from="compose",
    )
    assert result.status == "ready"
    assert calls == [name for name in STEPS[2:] if name != "repair"]
    assert checkpoints.names == list(STEPS[2:])


@pytest.mark.asyncio
async def test_pipeline_rejects_incomplete_stage_registry():
    with pytest.raises(ValueError, match="Missing longform pipeline stages"):
        await run_chapter(
            generation_input=SimpleNamespace(work_id="w", chapter_no=1),
            context_port=object(),
            provider=object(),
            progress=None,
            checkpoint=Checkpoints(),
            cancel=Cancel(),
            limiter=Limiter(),
            provider_id="p",
            steps={},
        )


@pytest.mark.asyncio
async def test_pipeline_rechecks_after_seam_failure_and_returns_repair_exhausted():
    inp = SimpleNamespace(work_id="w", chapter_no=1, settings=SimpleNamespace(max_repair_rounds=2))
    context = SimpleNamespace(get_context=lambda *_: _async_value({"ok": True}))
    checkpoints = Checkpoints()
    calls = []
    seam_rounds = 0

    async def stage(name):
        async def callback(_values, _call):
            nonlocal seam_rounds
            calls.append(name)
            if name == "seam":
                seam_rounds += 1
                return SeamResult(verdict="fail" if seam_rounds == 1 else "pass")
            if name == "review":
                return ReviewResult()
            if name == "write":
                return DraftCandidate(candidate_id="candidate-1", paragraphs=[])
            if name == "summarize":
                return PipelineResult(
                    status="ready",
                    candidate=DraftCandidate(candidate_id="candidate-1", paragraphs=[]),
                )
            return None

        return callback

    steps = {name: await stage(name) for name in STEPS}
    result = await run_chapter(
        generation_input=inp,
        context_port=context,
        provider=object(),
        progress=None,
        checkpoint=checkpoints,
        cancel=Cancel(),
        limiter=Limiter(),
        provider_id="p",
        steps=steps,
    )
    assert result.status == "ready"
    assert calls.count("repair") == 1 and calls.count("check") == 2
    assert calls[-1] == "summarize"

    inp.settings.max_repair_rounds = 1
    seam_rounds = 0

    async def always_fail(_values, _call):
        if _values.get("write") is None:
            return DraftCandidate(candidate_id="candidate-1", paragraphs=[])
        return SeamResult(verdict="fail")

    exhausted_steps = {name: always_fail for name in STEPS}
    exhausted = await run_chapter(
        generation_input=inp,
        context_port=context,
        provider=object(),
        progress=None,
        checkpoint=Checkpoints(),
        cancel=Cancel(),
        limiter=Limiter(),
        provider_id="p",
        steps=exhausted_steps,
    )
    assert exhausted.status == "needs_user" and exhausted.reason_code == "REPAIR_EXHAUSTED"


async def _async_value(value):
    return value
