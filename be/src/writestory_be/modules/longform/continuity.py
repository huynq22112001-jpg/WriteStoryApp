from __future__ import annotations

import json

from writestory_be.core.clock import utcnow_iso


def mark_stale(work, chapter_no: int, *, reason: str = "content_changed") -> None:
    if work.continuity_status == "blocked_needs_resync":
        blocked_at = work.continuity_chapter_no
        if blocked_at is not None and chapter_no >= blocked_at:
            return
    if work.continuity_status != "stale_from" or work.continuity_chapter_no is None:
        work.continuity_status = "stale_from"
        work.continuity_chapter_no = chapter_no
    else:
        work.continuity_chapter_no = min(work.continuity_chapter_no, chapter_no)
    work.continuity_reason = json.dumps({"reason": reason}, ensure_ascii=False)
    work.continuity_updated_at = utcnow_iso()


def mark_blocked(work, chapter_no: int, reason: str) -> None:
    work.continuity_status = "blocked_needs_resync"
    work.continuity_chapter_no = chapter_no
    work.continuity_reason = json.dumps({"reason": reason}, ensure_ascii=False)
    work.continuity_updated_at = utcnow_iso()


def clear_continuity(work) -> None:
    work.continuity_status = "ok"
    work.continuity_chapter_no = None
    work.continuity_reason = None
    work.continuity_updated_at = utcnow_iso()
