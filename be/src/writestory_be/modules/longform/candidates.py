from __future__ import annotations

import json

from sqlalchemy import select

from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.models.chapters import (
    Chapter,
    ChapterRevision,
    ChapterWorkingCopy,
)
from writestory_be.infrastructure.db.models.longform_generation import ChapterCandidate, Finding
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.modules.chapters.service import ChapterService
from writestory_be.modules.longform.continuity import mark_stale


class CandidateService:
    def __init__(self, runtime):
        self.uow = runtime.ensure_database_services()

    async def list_for_chapter(self, chapter_id, status=None):
        async def read(session):
            chapter = await session.get(Chapter, chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            query = select(ChapterCandidate).where(ChapterCandidate.chapter_id == chapter_id)
            if status:
                query = query.where(ChapterCandidate.status == status)
            rows = (await session.scalars(query.order_by(ChapterCandidate.created_at.desc()))).all()
            return [self._summary(row) for row in rows]

        return await self.uow.read(read)

    async def get(self, candidate_id):
        async def read(session):
            row = await session.get(ChapterCandidate, candidate_id)
            if row is None:
                raise AppError(ErrorCode.NOT_FOUND)
            base = (
                await session.get(ChapterRevision, row.base_revision_id)
                if row.base_revision_id
                else None
            )
            return {
                **self._summary(row),
                "work_id": row.work_id,
                "job_id": row.job_id,
                "scope": json.loads(row.scope),
                "paragraphs": json.loads(row.paragraphs_json),
                "ops": json.loads(row.ops_json),
                "proposed_delta": json.loads(row.proposed_delta or "null"),
                "base_paragraphs": json.loads(base.paragraphs_json) if base else [],
            }

        return await self.uow.read(read)

    async def reject(self, candidate_id, reason=None):
        async def write(ctx):
            row = await ctx.session.get(ChapterCandidate, candidate_id)
            if row is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if row.status not in {"ready", "partial"}:
                raise AppError(ErrorCode.CANDIDATE_CLOSED)
            row.status, row.decided_at = "rejected", utcnow_iso()
            ctx.add_event(
                "candidate.updated",
                {"candidate_id": row.id, "status": row.status},
                work_id=row.work_id,
                job_id=row.job_id,
                chapter_no=row.chapter_no,
            )
            return {"status": row.status, "reason": reason}

        return await self.uow.write(write)

    async def accept(self, candidate_id, *, expected_revision_id, paragraph_ids=None, note=None):
        selected = set(paragraph_ids) if paragraph_ids is not None else None

        async def write(ctx):
            s = ctx.session
            candidate = await s.get(ChapterCandidate, candidate_id)
            if candidate is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if candidate.status != "ready" and not (candidate.status == "partial" and selected):
                raise AppError(
                    ErrorCode.CANDIDATE_NOT_READY
                    if candidate.status in {"partial", "streaming"}
                    else ErrorCode.CANDIDATE_CLOSED
                )
            chapter = await s.get(Chapter, candidate.chapter_id)
            if chapter is None or chapter.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            locked = await s.scalar(
                select(Job.id)
                .where(
                    Job.work_id == candidate.work_id,
                    Job.type == "write",
                    Job.status == "running",
                    Job.id != candidate.job_id,
                    Job.base_revision_id == chapter.current_revision_id,
                )
                .limit(1)
            )
            if locked:
                raise AppError(ErrorCode.CHAPTER_IS_BASE)
            working = await s.get(ChapterWorkingCopy, chapter.id)
            base = (
                await s.get(ChapterRevision, candidate.base_revision_id)
                if candidate.base_revision_id
                else None
            )
            base_paras = json.loads(base.paragraphs_json) if base else []
            current = (
                await s.get(ChapterRevision, chapter.current_revision_id)
                if chapter.current_revision_id
                else None
            )
            current_paras = json.loads(current.paragraphs_json) if current else []
            candidate_paras = json.loads(candidate.paragraphs_json)
            if chapter.current_revision_id != expected_revision_id or (
                working and working.has_changes
            ):
                base_text = {
                    p.get("id", p.get("paragraph_id")): p.get("text", "") for p in base_paras
                }
                current_text = {
                    p.get("id", p.get("paragraph_id")): p.get("text", "") for p in current_paras
                }
                proposed_text = {
                    p.get("paragraph_id", p.get("id")): p.get("text", "") for p in candidate_paras
                }
                conflict_ids = sorted(
                    pid
                    for pid in set(base_text) | set(current_text) | set(proposed_text)
                    if base_text.get(pid) != current_text.get(pid)
                    and proposed_text.get(pid) != current_text.get(pid)
                )
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={
                        "current_revision_id": chapter.current_revision_id,
                        "candidate_base_revision_id": candidate.base_revision_id,
                        "base": base_paras,
                        "current": current_paras,
                        "candidate": candidate_paras,
                        "conflicts": [
                            {
                                "paragraph_id": pid,
                                "kind": "both_modified",
                                "base_text": base_text.get(pid),
                                "current_text": current_text.get(pid),
                                "candidate_text": proposed_text.get(pid),
                            }
                            for pid in conflict_ids
                        ],
                        "clean_paragraph_ids": sorted(
                            (set(base_text) | set(current_text) | set(proposed_text))
                            - set(conflict_ids)
                        ),
                        "working_copy": json.loads(working.doc_json)
                        if working and working.has_changes
                        else None,
                    },
                )
            validator_blocker = await s.scalar(
                select(Finding.id)
                .where(
                    Finding.candidate_id == candidate.id,
                    Finding.source.in_(("validator", "check")),
                    Finding.severity == "blocker",
                    Finding.status == "open",
                )
                .limit(1)
            )
            if validator_blocker:
                raise AppError(ErrorCode.WORK_BLOCKED, detail={"reason": "STATE_INVALID"})
            if candidate.kind == "draft" and base is None:
                merged = candidate_paras
            else:
                base_map = {
                    p.get("paragraph_id", p.get("id")): p.get("text", "") for p in base_paras
                }
                cur_map = {
                    p.get("paragraph_id", p.get("id")): p.get("text", "") for p in current_paras
                }
                cand_map = {
                    p.get("paragraph_id", p.get("id")): p.get("text", "") for p in candidate_paras
                }
                targets = selected if selected is not None else set(cand_map)
                conflicts = []
                for pid in targets:
                    if (
                        pid in base_map
                        and cur_map.get(pid) != base_map[pid]
                        and cand_map.get(pid) != cur_map.get(pid)
                    ):
                        conflicts.append(
                            {
                                "paragraph_id": pid,
                                "kind": "both_modified",
                                "base_text": base_map[pid],
                                "current_text": cur_map.get(pid),
                                "candidate_text": cand_map.get(pid),
                            }
                        )
                if conflicts:
                    raise AppError(
                        ErrorCode.REVISION_CONFLICT,
                        detail={
                            "current_revision_id": chapter.current_revision_id,
                            "candidate_base_revision_id": candidate.base_revision_id,
                            "base": base_paras,
                            "current": current_paras,
                            "candidate": candidate_paras,
                            "conflicts": conflicts,
                            "clean_paragraph_ids": sorted(
                                targets - {c["paragraph_id"] for c in conflicts}
                            ),
                        },
                    )
                merged = [
                    dict(
                        p, text=cand_map.get(p.get("paragraph_id", p.get("id")), p.get("text", ""))
                    )
                    if p.get("paragraph_id", p.get("id")) in targets
                    and p.get("paragraph_id", p.get("id")) in cand_map
                    else p
                    for p in current_paras
                ]
                known = {p.get("paragraph_id", p.get("id")) for p in merged}
                merged.extend(
                    p
                    for p in candidate_paras
                    if p.get("paragraph_id", p.get("id")) in targets
                    and p.get("paragraph_id", p.get("id")) not in known
                )
            doc = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"paragraph_id": p.get("paragraph_id", p.get("id"))},
                        "content": [{"type": "text", "text": p.get("text", "")}]
                        if p.get("text")
                        else [],
                    }
                    for p in merged
                ],
            }
            revision = await ChapterService.__new__(ChapterService)._make_revision(
                s, chapter, doc, source="ai_accept", reason=note or "candidate_accept"
            )
            candidate.status, candidate.accepted_revision_id = "accepted", revision.id
            candidate.accepted_paragraph_ids = json.dumps(
                sorted(
                    selected
                    or {
                        p.get("paragraph_id", p.get("id"))
                        for p in json.loads(candidate.paragraphs_json)
                    }
                )
            )
            candidate.decided_at = utcnow_iso()
            work = await s.get(Work, candidate.work_id)
            latest = await s.scalar(
                select(Chapter.chapter_no)
                .where(
                    Chapter.work_id == work.id,
                    Chapter.deleted_at.is_(None),
                    Chapter.status == "committed",
                )
                .order_by(Chapter.chapter_no.desc())
                .limit(1)
            )
            if latest and candidate.chapter_no <= latest:
                mark_stale(work, candidate.chapter_no)
                ctx.add_event(
                    "work.continuity",
                    {
                        "status": work.continuity_status,
                        "chapter_no": work.continuity_chapter_no,
                        "reason": json.loads(work.continuity_reason or "{}"),
                    },
                    work_id=work.id,
                )
            ctx.add_event(
                "candidate.updated",
                {"candidate_id": candidate.id, "status": "accepted"},
                work_id=work.id,
                job_id=candidate.job_id,
                chapter_no=chapter.chapter_no,
            )
            return {
                "chapter_id": chapter.id,
                "revision_id": revision.id,
                "candidate_status": candidate.status,
                "continuity": {
                    "status": work.continuity_status,
                    "chapter_no": work.continuity_chapter_no,
                },
            }

        return await self.uow.write(write)

    @staticmethod
    def _summary(row):
        return {
            "id": row.id,
            "chapter_id": row.chapter_id,
            "chapter_no": row.chapter_no,
            "kind": row.kind,
            "mode": row.mode,
            "status": row.status,
            "base_revision_id": row.base_revision_id,
            "check_summary": json.loads(row.check_summary),
            "created_at": row.created_at,
        }
