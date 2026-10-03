import asyncio
import json

import pytest
from sqlalchemy import select

from writestory_ai.contracts.longform import DraftCandidate, PipelineResult
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.migrations import prepare_database
from writestory_be.infrastructure.db.models.longform_generation import ChapterCandidate
from writestory_be.infrastructure.db.models.system import Job, JobStep
from writestory_be.modules.longform.write_service import WriteJobRequest, WriteJobService


@pytest.fixture
async def longform_db(runtime):
    await asyncio.to_thread(prepare_database, runtime.data_root)
    yield
    if runtime.writer_queue is not None:
        await runtime.writer_queue.close()
    if runtime.db_engine is not None:
        await runtime.db_engine.dispose()


@pytest.mark.asyncio
async def test_write_job_pins_models_checkpoints_and_persists_candidate(
    client, runtime, monkeypatch, longform_db
):
    work = await client.post(
        "/v1/works",
        headers={"Idempotency-Key": "write-job-work"},
        json={"title": "Một chương"},
    )
    work_id = work.json()["id"]
    chapter = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Mở đầu"})
    chapter_id = chapter.json()["id"]

    async def resolve(_self, _work_id, role):
        return {"provider_id": "provider", "model_id": f"model-{role}", "effort": "low"}

    monkeypatch.setattr(
        "writestory_be.modules.longform.write_service.ModelResolver.resolve", resolve
    )

    class FakePipeline:
        async def execute(self, payload, *, progress, checkpoint, context_port):
            assert payload["pinned"]["writer"]["model_id"] == "model-writer"
            await checkpoint.save(
                "write",
                {
                    "write": {
                        "candidate": {
                            "paragraphs": [
                                {"paragraph_id": "para0001", "text": "Mưa rơi trên mái ngói."}
                            ]
                        }
                    }
                },
            )
            await progress.on_step(
                type("Step", (), {"step": "write", "round": 0, "max_rounds": 1, "progress": 1.0})()
            )
            return PipelineResult(
                status="ready",
                candidate=DraftCandidate(
                    candidate_id="draft",
                    paragraphs=[{"paragraph_id": "para0001", "text": "Mưa rơi trên mái ngói."}],
                ),
                delta=None,
            )

    runtime.longform_pipeline_executor = FakePipeline()
    queued = []
    runtime.spawn = lambda coro: queued.append(coro)
    response = await WriteJobService(runtime).enqueue(
        work_id,
        WriteJobRequest(chapter_no=1, mode="review_each", idempotency_key="write-job-001"),
    )
    assert response["status"] == "queued"
    await queued.pop(0)

    async with runtime.ensure_database_services().read_sessions() as session:
        job = await session.get(Job, response["job_id"])
        candidate = await session.scalar(
            select(ChapterCandidate).where(ChapterCandidate.chapter_id == chapter_id)
        )
        step = await session.scalar(select(JobStep).where(JobStep.job_id == job.id))
        assert job.status == "waiting_user"
        assert job.wait_reason == "review_required"
        assert job.checkpoint_json is None
        assert candidate.status == "ready"
        assert json.loads(candidate.paragraphs_json)[0]["paragraph_id"] == "para0001"
        assert step.status == "succeeded"


@pytest.mark.asyncio
async def test_interrupted_write_resumes_from_saved_checkpoint(client, runtime, longform_db):
    work = await client.post(
        "/v1/works", headers={"Idempotency-Key": "resume-work-001"}, json={"title": "Resume"}
    )
    work_id = work.json()["id"]
    chapter = await client.post(f"/v1/works/{work_id}/chapters", json={"title": "Mở đầu"})
    chapter_id = chapter.json()["id"]
    job_id, candidate_id = new_id(), new_id()
    now = "2026-10-03T00:00:00Z"
    checkpoint = {
        "write": {
            "candidate": {"paragraphs": [{"paragraph_id": "para0001", "text": "Đã viết một phần."}]}
        }
    }
    async with runtime.ensure_database_services().read_sessions() as session:
        session.add(
            Job(
                id=job_id,
                idempotency_key="resume-job-001",
                type="write",
                work_id=work_id,
                status="interrupted",
                input_json=json.dumps(
                    {
                        "chapter_id": chapter_id,
                        "chapter_no": 1,
                        "mode": "review_each",
                        "pinned": {},
                        "settings": {},
                    }
                ),
                base_revision_id=None,
                stage="write",
                checkpoint_json=json.dumps(checkpoint, ensure_ascii=False),
                attempt=1,
                created_at=now,
                updated_at=now,
                revision=2,
            )
        )
        session.add(
            ChapterCandidate(
                id=candidate_id,
                work_id=work_id,
                chapter_id=chapter_id,
                chapter_no=1,
                job_id=job_id,
                kind="draft",
                base_revision_id=None,
                status="partial",
                scope="{}",
                content_json="{}",
                paragraphs_json="[]",
                ops_json="[]",
                check_summary="{}",
                accepted_paragraph_ids="[]",
                created_at=now,
            )
        )
        await session.commit()

    class ResumePipeline:
        async def execute(
            self,
            payload,
            *,
            progress,
            checkpoint,
            context_port,
            resume_from=None,
            checkpoint_payload=None,
        ):
            assert resume_from == "write"
            assert (
                checkpoint_payload["write"]["candidate"]["paragraphs"][0]["paragraph_id"]
                == "para0001"
            )
            return PipelineResult(
                status="ready",
                candidate=DraftCandidate(
                    candidate_id="draft",
                    paragraphs=[{"paragraph_id": "para0001", "text": "Đã xong."}],
                ),
            )

    runtime.longform_pipeline_executor = ResumePipeline()
    from writestory_be.jobs.handlers.chapter_write import ChapterWriteRunner

    await ChapterWriteRunner(runtime).run(job_id)
    async with runtime.ensure_database_services().read_sessions() as session:
        job = await session.get(Job, job_id)
        candidate = await session.get(ChapterCandidate, candidate_id)
        assert job.status == "waiting_user"
        assert candidate.status == "ready"
