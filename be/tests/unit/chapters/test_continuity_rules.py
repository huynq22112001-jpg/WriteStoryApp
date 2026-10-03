from types import SimpleNamespace

from writestory_be.modules.longform.continuity import mark_blocked, mark_stale


def test_stale_from_keeps_earliest_chapter_and_blocker_dominates_later_edit():
    work = SimpleNamespace(
        continuity_status="ok",
        continuity_chapter_no=None,
        continuity_reason=None,
        continuity_updated_at=None,
    )
    mark_stale(work, 8)
    mark_stale(work, 4)
    assert work.continuity_status == "stale_from"
    assert work.continuity_chapter_no == 4
    mark_blocked(work, 7, "validator")
    mark_stale(work, 9)
    assert work.continuity_status == "blocked_needs_resync"
    assert work.continuity_chapter_no == 7
