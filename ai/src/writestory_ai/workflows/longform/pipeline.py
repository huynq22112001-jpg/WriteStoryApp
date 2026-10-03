from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from writestory_ai.contracts.errors import CancelledError
from writestory_ai.contracts.generation import GenerationInput
from writestory_ai.contracts.longform import DraftCandidate, PipelineResult
from writestory_ai.ports.limiter import ProviderLimiterPort

STEPS = (
    "load",
    "plan",
    "compose",
    "write",
    "check",
    "settle",
    "validate",
    "seam",
    "review",
    "repair",
    "summarize",
)


class CheckpointSink(Protocol):
    async def save(self, step: str, payload: dict[str, Any]) -> None: ...


class CancelToken(Protocol):
    def is_cancelled(self) -> bool: ...


async def _resolve(value):
    return await value if isinstance(value, Awaitable) else value


async def run_chapter(
    *,
    generation_input: GenerationInput,
    context_port: Any,
    provider: Any,
    progress: Any,
    checkpoint: CheckpointSink,
    cancel: CancelToken,
    limiter: ProviderLimiterPort,
    provider_id: str,
    steps: dict[str, Callable],
    resume_from: str | None = None,
) -> PipelineResult:
    """Run the 11 AI stages and checkpoint each boundary; persistence is owned by the host."""
    missing = [name for name in STEPS if name not in steps]
    if missing:
        raise ValueError(f"Missing longform pipeline stages: {', '.join(missing)}")
    state = await context_port.get_context(generation_input.work_id, generation_input.chapter_no)
    input_resume = getattr(generation_input, "resume", None)
    resume_from = resume_from or (input_resume.step if input_resume else None)
    values: dict[str, Any] = {
        "context": state,
        "provider": provider,
        "generation_input": generation_input,
    }
    if resume_from is not None and resume_from not in STEPS:
        raise ValueError(f"Unknown longform resume step: {resume_from}")
    start_index = STEPS.index(resume_from) if resume_from else 0
    if resume_from:
        if not hasattr(context_port, "load_checkpoint"):
            raise RuntimeError("ContextPort does not support checkpoint resume")
        restored = await _resolve(
            context_port.load_checkpoint(
                generation_input.work_id, generation_input.chapter_no, resume_from
            )
        )
        if isinstance(restored, dict):
            values.update(restored)

    async def limited_call(operation: Callable, *args, estimated_tokens: int = 0, **kwargs):
        if cancel.is_cancelled():
            raise CancelledError("Chapter pipeline cancelled")
        async with limiter.acquire(provider_id, estimated_tokens=estimated_tokens):
            if cancel.is_cancelled():
                raise CancelledError("Chapter pipeline cancelled")
            return await _resolve(operation(*args, **kwargs))

    async def run_step(name: str) -> Any:
        if cancel.is_cancelled():
            raise CancelledError("Chapter pipeline cancelled")
        values[name] = await _resolve(steps[name](values, limited_call))
        await checkpoint.save(name, {k: v for k, v in values.items() if k != "provider"})
        if progress is not None and hasattr(progress, "on_step"):
            from writestory_ai.contracts.events import StepProgress

            await progress.on_step(StepProgress(step=name, progress=1.0))

    def needs_repair() -> bool:
        seam = values.get("seam")
        if getattr(seam, "verdict", None) == "fail" or (
            isinstance(seam, dict) and seam.get("verdict") == "fail"
        ):
            return True
        validation = values.get("validate")
        if isinstance(validation, tuple) and validation:
            validation = validation[0]
        if getattr(validation, "valid", True) is False:
            return True
        if isinstance(validation, dict) and validation.get("valid") is False:
            return True
        for key in ("check", "review"):
            output = values.get(key)
            findings = getattr(output, "findings", output)
            if isinstance(findings, dict):
                findings = findings.get("findings", [])
            if isinstance(findings, list) and any(
                (
                    item.get("severity")
                    if isinstance(item, dict)
                    else getattr(item, "severity", None)
                )
                == "blocker"
                for item in findings
            ):
                return True
        return False

    async def should_stop_for_user() -> PipelineResult | None:
        for value in values.values():
            if isinstance(value, PipelineResult) and value.status == "needs_user":
                return value
        return None

    verifier = STEPS[4:9]
    repair_name = STEPS[9]
    summary_name = STEPS[10]
    if start_index >= len(STEPS) - 1:
        await run_step(summary_name)
    else:
        if start_index < 4:
            for name in STEPS[start_index:4]:
                await run_step(name)
                stopped = await should_stop_for_user()
                if stopped is not None:
                    return stopped
        # If resuming within verification, start at that checkpoint once, then rerun the full
        # validation chain after any repair.
        verify_start = max(0, start_index - 4) if 4 <= start_index <= 8 else 0
        repair_round = 0
        if start_index == 9:
            await run_step(repair_name)
            repair_round = 1
        while True:
            for name in verifier[verify_start:]:
                await run_step(name)
                stopped = await should_stop_for_user()
                if stopped is not None:
                    return stopped
            verify_start = 0
            if not needs_repair():
                await checkpoint.save(repair_name, {"skipped": True, "reason": "no_blocker"})
                break
            settings = getattr(generation_input, "settings", None)
            max_rounds = getattr(settings, "max_repair_rounds", 2)
            if repair_round >= max_rounds:
                candidate = values.get("write")
                if not isinstance(candidate, DraftCandidate):
                    candidate = DraftCandidate.model_validate(candidate)
                return PipelineResult(
                    status="needs_user",
                    reason_code="REPAIR_EXHAUSTED",
                    candidate=candidate,
                    findings=[
                        item
                        for key in ("check", "review")
                        for item in getattr(values.get(key), "findings", [])
                        if getattr(item, "severity", None) == "blocker"
                    ],
                )
            await run_step(repair_name)
            repair_round += 1
            stopped = await should_stop_for_user()
            if stopped is not None:
                return stopped
        await run_step(summary_name)
    result = values.get("summarize")
    if isinstance(result, PipelineResult):
        return result
    if isinstance(result, dict):
        return PipelineResult.model_validate(result)
    raise RuntimeError("The summarize stage must return PipelineResult")
