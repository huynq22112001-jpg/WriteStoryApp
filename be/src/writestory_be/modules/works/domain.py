from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FoundationReadiness:
    ready: bool
    missing: list[str]


class FoundationReadinessPort:
    async def check(self, work_id: str) -> FoundationReadiness:
        return FoundationReadiness(False, ["foundation"])


def validate_length_range(minimum: int, maximum: int) -> bool:
    return minimum > 0 and maximum > minimum


async def validate_ready_transition(work: Any, foundation: FoundationReadinessPort) -> list[str]:
    missing: list[str] = []
    if not work.title.strip():
        missing.append("title")
    if not (work.genre or work.genre_label_custom):
        missing.append("genre")
    if not work.brief or not work.brief.strip():
        missing.append("brief")
    if work.target_chapters is None or work.target_chapters < 1:
        missing.append("target_chapters")
    if not validate_length_range(work.chapter_length_min, work.chapter_length_max):
        missing.append("chapter_length")
    readiness = await foundation.check(work.id)
    missing.extend(readiness.missing)
    return list(dict.fromkeys(missing))


def compute_library_badge(
    *,
    continuity_status: str,
    status: str,
    wizard_step: str | None,
    target_chapters: int | None,
    committed_chapters: int,
    job: dict[str, Any] | None = None,
    continuity_chapter_no: int | None = None,
) -> dict[str, Any]:
    if continuity_status == "blocked_needs_resync" or (job and job.get("state") == "blocked"):
        return {"kind": "blocked", "label_key": "library.badge.blocked", "params": {}}
    if job:
        priority = {
            "running": ("running", "library.badge.running"),
            "waiting_user": ("waiting_user", "library.badge.waiting_user"),
            "waiting_slot": ("waiting_slot", "library.badge.waiting_slot"),
            "queued": ("queued", "library.badge.queued"),
            "interrupted": ("interrupted", "library.badge.interrupted"),
            "failed": ("failed", "library.badge.failed"),
        }
        if job.get("state") in priority:
            kind, label_key = priority[job["state"]]
            return {"kind": kind, "label_key": label_key, "params": job}
    if continuity_status == "stale_from":
        return {
            "kind": "stale",
            "label_key": "library.badge.stale",
            "params": {"chapter_no": continuity_chapter_no},
        }
    if status == "draft":
        return {
            "kind": "draft",
            "label_key": "library.badge.draft",
            "params": {"step": wizard_step},
        }
    if target_chapters and committed_chapters >= target_chapters:
        return {"kind": "done", "label_key": "library.badge.done", "params": {}}
    return {"kind": "ready", "label_key": "library.badge.ready", "params": {}}
