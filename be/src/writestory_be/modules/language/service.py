from __future__ import annotations

import json

from sqlalchemy import select

from writestory_ai.languages.contracts import CheckContext, ParagraphInput
from writestory_ai.languages.registry import get_language_pack
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.models.chapters import (
    Chapter,
    ChapterRevision,
    ChapterWorkingCopy,
)
from writestory_be.infrastructure.db.models.system import Setting
from writestory_be.infrastructure.db.models.works import StyleProfile, Work
from writestory_be.modules.language.domain import (
    finding_to_dict,
    merge_slop_entries,
    normalize,
    validate_slop_entries,
)

_SLOP_KEY = "language.vi.slop_user"


def _pack(code: str):
    try:
        return get_language_pack(code)
    except (ValueError, KeyError) as exc:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "language", "code": code}) from exc


class LanguageService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()

    async def genre_presets(self, code: str):
        pack = _pack(code)
        return list(pack.genre_presets.values())

    async def slop_list(self, code: str):
        pack = _pack(code)

        async def read(session):
            row = await session.get(Setting, _SLOP_KEY)
            user = (
                json.loads(row.value_json)
                if row
                else {"additions": [], "disabled": [], "version": 1}
            )
            return {
                "builtin": [entry.__dict__ for entry in pack.slop_list],
                "user": {"additions": user["additions"], "disabled": user["disabled"]},
                "version": int(user["version"]),
            }

        return await self.uow.read(read)

    async def put_slop_list(self, code: str, body):
        _pack(code)
        additions = [entry.model_dump() for entry in body.additions]
        validate_slop_entries(additions)
        if len(body.disabled) != len(set(body.disabled)):
            raise AppError(ErrorCode.VALIDATION, detail={"field": "disabled"})

        async def write(ctx):
            row = await ctx.session.get(Setting, _SLOP_KEY)
            current = (
                json.loads(row.value_json)
                if row
                else {"additions": [], "disabled": [], "version": 1}
            )
            if int(current["version"]) != body.expected_version:
                raise AppError(
                    ErrorCode.REVISION_CONFLICT,
                    detail={"current_version": current["version"]},
                )
            value = {
                "additions": additions,
                "disabled": body.disabled,
                "version": body.expected_version + 1,
            }
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            now = utcnow_iso()
            if row:
                row.value_json, row.revision, row.updated_at = encoded, value["version"], now
            else:
                ctx.session.add(
                    Setting(
                        key=_SLOP_KEY, value_json=encoded, revision=value["version"], updated_at=now
                    )
                )
            return {"version": value["version"]}

        return await self.uow.write(write)

    async def normalize_text(self, code: str, body):
        pack = _pack(code)
        if len(body.text.encode("utf-8")) > 1_000_000:
            raise AppError(ErrorCode.VALIDATION, detail={"field": "text", "max_bytes": 1_000_000})
        normalized, changes = normalize(body.text, pack)
        return {"text": normalized, "changes": changes, "legacy_encoding": None}

    async def check_text(self, work_id: str, body):
        async def read(session):
            work = await session.get(Work, work_id)
            if work is None or work.deleted_at:
                raise AppError(ErrorCode.NOT_FOUND)
            pack = _pack(work.language)
            profile = await session.scalar(
                select(StyleProfile).where(StyleProfile.work_id == work_id)
            )
            chapter_no = 1
            paragraphs = body.paragraphs
            if body.chapter_id:
                chapter = await session.get(Chapter, body.chapter_id)
                if chapter is None or chapter.work_id != work_id or chapter.deleted_at:
                    raise AppError(ErrorCode.NOT_FOUND)
                chapter_no = chapter.chapter_no
                if paragraphs is None:
                    working = await session.get(ChapterWorkingCopy, chapter.id)
                    revision = (
                        await session.get(ChapterRevision, chapter.current_revision_id)
                        if chapter.current_revision_id
                        else None
                    )
                    document = json.loads(
                        working.doc_json
                        if working
                        else revision.doc_json
                        if revision
                        else '{"type":"doc","content":[]}'
                    )
                    from writestory_be.modules.chapters.domain import project_doc

                    paragraphs = [
                        ParagraphInput(paragraph_id=item["id"], text=item["text"])
                        for item in project_doc(document)[0]
                    ]
            if paragraphs is None:
                raise AppError(ErrorCode.VALIDATION, detail={"field": "paragraphs"})
            if len({paragraph.paragraph_id for paragraph in paragraphs}) != len(paragraphs):
                raise AppError(
                    ErrorCode.VALIDATION,
                    detail={"field": "paragraphs", "reason": "duplicate_paragraph_id"},
                )
            total_units = sum(pack.count_length(item.text) for item in paragraphs)
            if total_units > 50_000:
                raise AppError(
                    ErrorCode.VALIDATION, detail={"field": "paragraphs", "max_units": 50_000}
                )
            genre = pack.genre_presets.get(work.genre or "", {})
            profile_data = {
                "tone_mark_style": profile.tone_mark_style if profile else "new",
                "dialogue_style": profile.dialogue_style if profile else "dash",
                "vocab_register": profile.vocab_register if profile else "balanced",
                "anachronism_allow": [],
                "slop": [],
            }
            setting = await session.get(Setting, _SLOP_KEY)
            app_slop = (
                json.loads(setting.value_json) if setting else {"additions": [], "disabled": []}
            )
            profile_data["slop"] = merge_slop_entries(
                pack.slop_list,
                app_slop,
                [],
                json.loads(profile.banned_phrases) if profile else [],
            )
            context = CheckContext(
                work_id=work_id,
                chapter_no=chapter_no,
                genre_preset=genre,
                profile=profile_data,
                paragraphs=[
                    ParagraphInput(paragraph_id=p.paragraph_id, text=p.text) for p in paragraphs
                ],
            )
            findings = []
            requested = set(body.checks or [])
            known = {
                check_id for check in pack.deterministic_checks for check_id in _check_ids(check)
            }
            if requested - known:
                raise AppError(
                    ErrorCode.VALIDATION,
                    detail={"field": "checks", "unknown": sorted(requested - known)},
                )
            for check in pack.deterministic_checks:
                if requested and not (requested & _check_ids(check)):
                    continue
                results = check(context)
                findings.extend(finding_to_dict(result) for result in results)
            return {
                "findings": findings,
                "length": {"units": total_units, "chars": sum(len(p.text) for p in paragraphs)},
            }

        return await self.uow.read(read)


def _check_ids(check):
    # Check functions may emit more than one stable id; the IDs are documented by F08.
    return {
        "check_address": {"vi.address"},
        "check_name_variants": {"vi.name_variant"},
        "check_lexicon": {"vi.lexicon"},
        "check_slop": {"vi.slop"},
        "check_spelling": {"vi.spelling"},
        "check_accent_mix": {"vi.accent_mix"},
        "check_dialogue": {"vi.dialogue"},
    }.get(check.__name__, set())
