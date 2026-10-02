"""Route chỉ dùng khi phát triển/spike (chỉ đăng ký khi `dev_features=true`, F00 be.md).

`POST /v1/dev/mock-runs` mô phỏng nhiều truyện cùng stream bằng mock provider của package AI để
kiểm tra Phòng viết/editor không bị chặn trước khi có pipeline thật (Plan §9 Giai đoạn 0).
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from writestory_ai.contracts.errors import AIError
from writestory_ai.contracts.generation import GenerationRequest, Message, StreamDone, TextDelta
from writestory_ai.providers.mock import MockScenario, MockTextProvider

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.bootstrap.context import Runtime
from writestory_be.core.ids import new_id

router = APIRouter(prefix="/v1/dev", tags=["dev"])

SAMPLE_TEXT = (
    "Mưa đêm rơi lất phất trên mái hiên khách điếm. Lâm Phong siết chặt chuôi kiếm, "
    "lắng nghe tiếng bước chân dừng lại ngoài cổng. Mộc Lan khẽ thổi tắt ngọn đèn dầu. "
    "Trong bóng tối, hai người nhìn nhau, không ai nói một lời."
)


class MockRunsRequest(BaseModel):
    works: int = Field(default=3, ge=1, le=5)
    tokens_per_sec: float = Field(default=20, gt=0, le=500)
    latency_ms: int = Field(default=300, ge=0, le=10_000)
    repeat: int = Field(default=3, ge=1, le=50, description="Số lần lặp văn bản mẫu")


class MockRunsAccepted(BaseModel):
    run_ids: list[str]
    work_ids: list[str]


async def _run_one(runtime: Runtime, job_id: str, work_id: str, body: MockRunsRequest) -> None:
    bus = runtime.event_bus
    candidate_id = new_id()
    provider = MockTextProvider(
        MockScenario(
            text=" ".join([SAMPLE_TEXT] * body.repeat),
            latency_ms=body.latency_ms,
            tokens_per_sec=body.tokens_per_sec,
        )
    )
    request = GenerationRequest(model="mock", messages=[Message(role="user", content="Viết tiếp")])
    bus.publish("job.state", {"status": "running"}, work_id=work_id, job_id=job_id, chapter_no=1)
    bus.publish("job.step", {"step": "write", "attempt": 1}, work_id=work_id, job_id=job_id)
    offset = 0
    try:
        async for event in provider.stream(request):
            if isinstance(event, TextDelta):
                bus.publish_transient(
                    "token.delta",
                    {"candidate_id": candidate_id, "step": "write", "mode": "full",
                     "offset": offset, "text": event.text},
                    work_id=work_id,
                    job_id=job_id,
                )
                offset += len(event.text)
            elif isinstance(event, StreamDone):
                bus.publish(
                    "job.state",
                    {"status": "succeeded", "usage": event.usage.model_dump()},
                    work_id=work_id,
                    job_id=job_id,
                )
    except AIError as exc:
        bus.publish(
            "job.state",
            {"status": "failed", "error": {"code": exc.code, "message": str(exc)}},
            work_id=work_id,
            job_id=job_id,
        )


@router.post("/mock-runs", status_code=status.HTTP_202_ACCEPTED, name="create_mock_runs")
async def create_mock_runs(body: MockRunsRequest, runtime: RuntimeDep) -> MockRunsAccepted:
    run_ids: list[str] = []
    work_ids: list[str] = []
    for index in range(body.works):
        job_id, work_id = new_id(), f"mock-work-{index + 1}"
        runtime.event_bus.publish(
            "job.queued",
            {"job_type": "mock_write", "priority": 0, "queue_position": index},
            work_id=work_id,
            job_id=job_id,
        )
        runtime.spawn(_run_one(runtime, job_id, work_id, body))
        run_ids.append(job_id)
        work_ids.append(work_id)
    return MockRunsAccepted(run_ids=run_ids, work_ids=work_ids)
