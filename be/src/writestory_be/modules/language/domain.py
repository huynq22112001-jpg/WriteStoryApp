from __future__ import annotations

import re
from typing import Any

from writestory_be.core.errors import AppError, ErrorCode

_UNSAFE_REGEX = re.compile(r"\\[1-9]|\(\?<[=!]|\(\?P=|\(\?R|\(\?0|\([^)]*[+*][^)]*\)[+*{]")


def validate_slop_entries(entries: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    for entry in entries:
        entry_id = str(entry.get("id", ""))
        pattern = str(entry.get("pattern", ""))
        if not entry_id or entry_id in ids:
            raise AppError(
                ErrorCode.VALIDATION, detail={"field": "additions", "reason": "duplicate_id"}
            )
        ids.add(entry_id)
        if entry.get("is_regex"):
            if len(pattern) > 200 or _UNSAFE_REGEX.search(pattern):
                raise AppError(
                    ErrorCode.VALIDATION, detail={"field": "pattern", "entry_id": entry_id}
                )
            try:
                re.compile(pattern)
            except re.error as exc:
                raise AppError(
                    ErrorCode.VALIDATION,
                    detail={"field": "pattern", "entry_id": entry_id, "position": exc.pos},
                ) from exc


def merge_slop_entries(builtin, app_user: dict, work_disabled: list[str], work_phrases: list[str]):
    disabled = set(app_user.get("disabled", [])) | set(work_disabled)
    fields = ("id", "pattern", "is_regex", "scope", "max_per_1000_units", "note")
    entries = [
        {field: getattr(entry, field) for field in fields}
        for entry in builtin
        if entry.id not in disabled
    ]
    entries.extend(app_user.get("additions", []))
    entries.extend(
        {
            "id": f"work:{index}",
            "pattern": phrase,
            "is_regex": False,
            "scope": "anywhere",
            "max_per_1000_units": None,
            "note": "",
        }
        for index, phrase in enumerate(work_phrases)
        if phrase
    )
    return entries


def normalize(text: str, pack) -> tuple[str, list[dict[str, Any]]]:
    normalized = pack.normalize(text)
    changes = []
    if normalized != text:
        changes.append({"kind": "unicode_and_whitespace", "count": 1})
    return normalized, changes


def finding_to_dict(finding) -> dict[str, Any]:
    return finding.model_dump()
