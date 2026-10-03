import pytest

from writestory_be.modules.works.domain import compute_library_badge


@pytest.mark.parametrize(
    ("work", "job", "expected"),
    [
        ({"continuity_status": "blocked_needs_resync"}, None, "blocked"),
        ({"continuity_status": "ok"}, {"state": "blocked"}, "blocked"),
        ({"continuity_status": "ok"}, {"state": "running"}, "running"),
        ({"continuity_status": "ok"}, {"state": "waiting_user"}, "waiting_user"),
        ({"continuity_status": "ok"}, {"state": "waiting_slot"}, "waiting_slot"),
        ({"continuity_status": "ok"}, {"state": "queued"}, "queued"),
        ({"continuity_status": "ok"}, {"state": "interrupted"}, "interrupted"),
        ({"continuity_status": "ok"}, {"state": "failed"}, "failed"),
        ({"continuity_status": "stale_from"}, None, "stale"),
        ({"continuity_status": "ok", "status": "draft"}, None, "draft"),
        ({"continuity_status": "ok", "status": "ready", "target_chapters": 3}, None, "done"),
        ({"continuity_status": "ok", "status": "ready"}, None, "ready"),
    ],
)
def test_library_badge_priority(work, job, expected):
    badge = compute_library_badge(
        continuity_status=work.get("continuity_status", "ok"),
        status=work.get("status", "ready"),
        wizard_step=work.get("wizard_step"),
        target_chapters=work.get("target_chapters"),
        committed_chapters=3 if expected == "done" else 0,
        continuity_chapter_no=8 if expected == "stale" else None,
        job=job,
    )
    assert badge["kind"] == expected
