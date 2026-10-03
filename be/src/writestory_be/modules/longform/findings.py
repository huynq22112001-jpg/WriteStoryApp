from __future__ import annotations

import json

from sqlalchemy import select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.longform_generation import Finding
from writestory_be.infrastructure.db.models.works import Work


def finding_out(row):
    return {
        "id": row.id,
        "work_id": row.work_id,
        "chapter_id": row.chapter_id,
        "chapter_no": row.chapter_no,
        "candidate_id": row.candidate_id,
        "source": row.source,
        "check_id": row.check_id,
        "kind": row.kind,
        "severity": row.severity,
        "message": row.message,
        "evidence": json.loads(row.evidence),
        "evidence_status": row.evidence_status,
        "suggestion": row.suggestion,
        "refs": json.loads(row.refs),
        "status": row.status,
        "resolution_note": row.resolution_note,
        "created_at": row.created_at,
        "resolved_at": row.resolved_at,
    }


class FindingService:
    def __init__(self, runtime):
        self.uow = runtime.ensure_database_services()

    async def list(self, work_id, *, status=None, chapter=None, severity=None, source=None):
        async def read(session):
            if await session.get(Work, work_id) is None:
                raise AppError(ErrorCode.NOT_FOUND)
            query = select(Finding).where(Finding.work_id == work_id)
            for col, value in (
                (Finding.status, status),
                (Finding.chapter_no, chapter),
                (Finding.severity, severity),
                (Finding.source, source),
            ):
                if value is not None:
                    query = query.where(col == value)
            rows = (await session.scalars(query.order_by(Finding.created_at.desc()))).all()
            return {"items": [finding_out(row) for row in rows], "next_cursor": None}

        return await self.uow.read(read)

    async def decide(self, finding_id, action, note=None):
        async def write(ctx):
            row = await ctx.session.get(Finding, finding_id)
            if row is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if row.status != "open":
                return finding_out(row)
            if action == "dismiss":
                if row.source in {"validator", "check", "schema"}:
                    raise AppError(
                        ErrorCode.VALIDATION,
                        detail={"reason": "deterministic_finding_cannot_be_dismissed"},
                    )
                if row.severity in {"blocker", "major"} and not (note and note.strip()):
                    raise AppError(ErrorCode.VALIDATION, detail={"field": "note"})
                row.status, row.resolution_note = "dismissed", note.strip() if note else None
            else:
                row.status, row.resolution_note, row.resolved_by = "resolved", note, "user"
            row.resolved_at = utcnow_iso()
            ctx.add_event(
                "finding.updated",
                {"finding_id": row.id, "status": row.status},
                work_id=row.work_id,
                job_id=row.job_id,
                chapter_no=row.chapter_no,
            )
            return finding_out(row)

        return await self.uow.write(write)

    async def create_user(self, chapter, *, kind, severity, message, evidence):
        now = utcnow_iso()

        async def write(ctx):
            row = Finding(
                id=new_id(),
                work_id=chapter.work_id,
                chapter_id=chapter.id,
                chapter_no=chapter.chapter_no,
                revision_id=chapter.current_revision_id,
                source="user",
                kind=kind,
                severity=severity,
                message=message,
                evidence=json.dumps(evidence, ensure_ascii=False),
                evidence_status="verified",
                refs="[]",
                params="{}",
                status="open",
                created_at=now,
            )
            ctx.session.add(row)
            ctx.add_event(
                "finding.added",
                {
                    "finding_id": row.id,
                    "chapter_no": row.chapter_no,
                    "severity": row.severity,
                    "kind": row.kind,
                },
                work_id=row.work_id,
                chapter_no=row.chapter_no,
            )
            await ctx.session.flush()
            return finding_out(row)

        return await self.uow.write(write)
