from __future__ import annotations

import hashlib
import inspect
import json

from sqlalchemy import select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.ai.progress_adapter import ProgressCheckpointAdapter
from writestory_be.infrastructure.db.models.chapters import Chapter
from writestory_be.infrastructure.db.models.longform_generation import ChapterCandidate, Finding
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.jobs.locks import WorkLockManager
from writestory_be.modules.longform.commit import commit_chapter


class ChapterWriteRunner:
    """Host runner; the installed P219 executor owns model-specific stage wiring."""

    def __init__(self, runtime, *, owner_id: str | None = None):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()
        self.locks = WorkLockManager(self.uow, owner_id or f"backend:{runtime.pid}")

    async def run(self, job_id: str):
        now = utcnow_iso()

        async def begin(ctx):
            job = await ctx.session.get(Job, job_id)
            if job is None:
                return None
            payload = json.loads(job.input_json)
            from writestory_be.modules.longform.gate import entry_gate

            await entry_gate(ctx.session, job.work_id, payload["chapter_no"])
            candidate = await ctx.session.scalar(
                select(ChapterCandidate)
                .where(ChapterCandidate.job_id == job.id)
                .order_by(ChapterCandidate.created_at)
                .limit(1)
            )
            if candidate is None:
                candidate = ChapterCandidate(
                    id=new_id(),
                    work_id=job.work_id,
                    chapter_id=payload["chapter_id"],
                    chapter_no=payload["chapter_no"],
                    job_id=job.id,
                    kind="draft",
                    base_revision_id=job.base_revision_id,
                    status="streaming",
                    scope="{}",
                    content_json="{}",
                    paragraphs_json="[]",
                    ops_json="[]",
                    check_summary="{}",
                    accepted_paragraph_ids="[]",
                    created_at=now,
                )
                ctx.session.add(candidate)
            else:
                candidate.status = "streaming"
            job.status, job.started_at, job.updated_at = "running", now, now
            job.attempt += 1
            return {
                "payload": payload,
                "candidate_id": candidate.id,
                "resume_step": job.stage if job.checkpoint_json else None,
                "checkpoint": json.loads(job.checkpoint_json) if job.checkpoint_json else None,
            }

        started = await self.uow.write(begin)
        if started is None:
            return
        async with self.uow.read_sessions() as session:
            job = await session.get(Job, job_id)
            work_id = job.work_id
        await self.locks.wait_and_acquire(work_id, job_id)
        adapter = ProgressCheckpointAdapter(self.runtime, job_id, started["candidate_id"])
        try:
            executor = getattr(self.runtime, "longform_pipeline_executor", None)
            if executor is None or executor is self:
                raise RuntimeError("P219 pipeline executor chưa được đăng ký trong Runtime")
            context_port = getattr(self.runtime, "context_port", None)
            if context_port is None:
                from writestory_be.infrastructure.ai.context_adapter import DatabaseContextAdapter

                context_port = DatabaseContextAdapter(self.uow, job_id=job_id)
            kwargs = {"progress": adapter, "checkpoint": adapter, "context_port": context_port}
            signature = inspect.signature(executor.execute)
            if started["resume_step"] and (
                "resume_from" in signature.parameters
                or any(p.kind == p.VAR_KEYWORD for p in signature.parameters.values())
            ):
                kwargs["resume_from"] = started["resume_step"]
                kwargs["checkpoint_payload"] = started["checkpoint"]
            output = await executor.execute(started["payload"], **kwargs)
            await self._finish(job_id, started["candidate_id"], output)
        except Exception as exc:
            await self._fail(job_id, started["candidate_id"], exc)
        finally:
            await self.locks.release(work_id, job_id)

    async def _finish(self, job_id, candidate_id, output):
        value = output.model_dump(mode="json") if hasattr(output, "model_dump") else output
        now = utcnow_iso()

        async def write(ctx):
            job = await ctx.session.get(Job, job_id)
            candidate = await ctx.session.get(ChapterCandidate, candidate_id)
            result = value.get("candidate", {})
            paragraphs = result.get("paragraphs", [])
            candidate.paragraphs_json = json.dumps(paragraphs, ensure_ascii=False)
            candidate.plain_text = "\n\n".join(p.get("text", "") for p in paragraphs)
            candidate.content_json = json.dumps({"paragraphs": paragraphs}, ensure_ascii=False)
            candidate.proposed_delta = json.dumps(value.get("delta"), ensure_ascii=False)
            candidate.ending_state = json.dumps(value.get("ending_state"), ensure_ascii=False)
            candidate.seam_json = json.dumps(value.get("seam_json", {}), ensure_ascii=False)
            candidate.summary_json = json.dumps(value.get("summary", {}), ensure_ascii=False)
            candidate.plan_id = value.get("plan_id") or None
            candidate.check_summary = json.dumps(
                value.get("check_summary", value.get("measurements", {})), ensure_ascii=False
            )
            for item in value.get("findings", []):
                packed_finding = (
                    item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                )
                fingerprint = hashlib.sha256(
                    json.dumps(packed_finding, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest()
                exists = await ctx.session.scalar(
                    select(Finding.id).where(
                        Finding.candidate_id == candidate.id, Finding.fingerprint == fingerprint
                    )
                )
                if exists:
                    continue
                finding = Finding(
                    id=new_id(),
                    work_id=job.work_id,
                    chapter_id=candidate.chapter_id,
                    chapter_no=candidate.chapter_no,
                    candidate_id=candidate.id,
                    job_id=job.id,
                    source=packed_finding.get("source", "review"),
                    check_id=packed_finding.get("check_id"),
                    kind=packed_finding.get("kind", "craft"),
                    severity=packed_finding.get("severity", "minor"),
                    confidence=packed_finding.get("confidence"),
                    message=packed_finding.get("message", ""),
                    message_key=packed_finding.get("message_key"),
                    params=json.dumps(packed_finding.get("params", {}), ensure_ascii=False),
                    evidence=json.dumps(packed_finding.get("evidence", []), ensure_ascii=False),
                    evidence_status=packed_finding.get("evidence_status", "verified"),
                    suggestion=packed_finding.get("suggestion"),
                    refs=json.dumps(packed_finding.get("refs", []), ensure_ascii=False),
                    fingerprint=fingerprint,
                    round=packed_finding.get("round", 0),
                    needs_confirmation=packed_finding.get("needs_confirmation", False),
                    status="open",
                    created_at=now,
                )
                ctx.session.add(finding)
                ctx.add_event(
                    "finding.added",
                    {
                        "finding_id": finding.id,
                        "chapter_no": candidate.chapter_no,
                        "severity": finding.severity,
                        "kind": finding.kind,
                    },
                    work_id=job.work_id,
                    job_id=job.id,
                    chapter_no=candidate.chapter_no,
                )
            candidate.status = "ready" if value.get("status") == "ready" else "partial"
            candidate.ready_at = now if candidate.status == "ready" else None
            job.status = "waiting_user"
            reason = value.get("reason_code")
            job.wait_reason = (
                "review_required"
                if candidate.status == "ready"
                else (reason or "repair_exhausted").lower()
            )
            if candidate.status == "ready" and json.loads(job.input_json).get("mode") == "auto":
                job.wait_reason = "commit_pending"
            chapter = await ctx.session.get(Chapter, candidate.chapter_id)
            if chapter:
                chapter.status = "waiting_user"
            if reason in {"REPAIR_EXHAUSTED", "STATE_INVALID"}:
                from writestory_be.infrastructure.db.models.works import Work
                from writestory_be.modules.longform.continuity import mark_blocked

                work = await ctx.session.get(Work, job.work_id)
                mark_blocked(work, candidate.chapter_no, reason)
                ctx.add_event(
                    "work.continuity",
                    {
                        "status": work.continuity_status,
                        "chapter_no": work.continuity_chapter_no,
                        "reason": {"reason": reason},
                    },
                    work_id=work.id,
                    job_id=job.id,
                    chapter_no=candidate.chapter_no,
                )
            job.finished_at = now
            job.updated_at = now
            job.checkpoint_json = None
            ctx.add_event(
                "candidate.ready" if candidate.status == "ready" else "candidate.updated",
                {
                    "candidate_id": candidate.id,
                    "chapter_id": candidate.chapter_id,
                    "kind": candidate.kind,
                    "status": candidate.status,
                    "check_summary": json.loads(candidate.check_summary),
                },
                work_id=job.work_id,
                job_id=job.id,
                chapter_no=candidate.chapter_no,
            )

        await self.uow.write(write)
        async with self.uow.read_sessions() as session:
            job = await session.get(Job, job_id)
            should_commit = bool(job and json.loads(job.input_json).get("mode") == "auto")
        if should_commit and value.get("status") == "ready" and value.get("delta") is not None:
            await commit_chapter(self.uow, job_id=job_id, candidate_id=candidate_id)

    async def _fail(self, job_id, candidate_id, exc):
        now = utcnow_iso()

        async def write(ctx):
            job = await ctx.session.get(Job, job_id)
            candidate = await ctx.session.get(ChapterCandidate, candidate_id)
            if job:
                blocked = isinstance(exc, AppError) and exc.code in {
                    ErrorCode.VALIDATION,
                    ErrorCode.WORK_BLOCKED,
                }
                job.status = "waiting_user" if blocked else "failed"
                job.wait_reason = "blocked_needs_resync" if blocked else None
                job.error_code = exc.code.value if isinstance(exc, AppError) else "INTERNAL"
                job.error_json = json.dumps({"reason": str(exc)[:300]}, ensure_ascii=False)
                job.finished_at = job.updated_at = now
                if blocked:
                    from writestory_be.infrastructure.db.models.works import Work
                    from writestory_be.modules.longform.continuity import mark_blocked

                    work = await ctx.session.get(Work, job.work_id)
                    mark_blocked(work, candidate.chapter_no, "STATE_INVALID")
                    chapter = await ctx.session.get(Chapter, candidate.chapter_id)
                    chapter.status = "waiting_user"
                    ctx.add_event(
                        "work.continuity",
                        {
                            "status": work.continuity_status,
                            "chapter_no": work.continuity_chapter_no,
                            "reason": {"reason": "STATE_INVALID"},
                        },
                        work_id=work.id,
                        job_id=job.id,
                        chapter_no=candidate.chapter_no,
                    )
            if candidate and candidate.status == "streaming":
                candidate.status, candidate.decided_at = "partial", now

        await self.uow.write(write)
