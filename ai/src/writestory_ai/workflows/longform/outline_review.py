from __future__ import annotations

from collections.abc import Awaitable, Callable

from writestory_ai.contracts.longform import OutlineProposal


def should_review_outline(chapter_no: int, every_k: int, moved_event_count: int) -> bool:
    if every_k < 1:
        raise ValueError("every_k must be positive")
    return chapter_no % every_k == 0 or moved_event_count >= 2


def apply_outline_proposal(proposal: OutlineProposal, events: list[dict]) -> list[dict]:
    by_id = {str(event["id"]): dict(event) for event in events}
    for change in proposal.changes:
        event_id = change.get("story_event_id")
        if change.get("action") == "add":
            proposal_id = str(change.get("change_id", ""))
            by_id[f"proposal:{proposal_id}"] = {
                "id": f"proposal:{proposal_id}",
                "status": "planned",
                "planned_chapter": change.get("to_chapter"),
                "summary": change.get("summary", ""),
                "locked": False,
                "proposed": True,
            }
            continue
        if event_id not in by_id:
            continue
        event = by_id[event_id]
        if event.get("locked"):
            continue
        action = change.get("action")
        if action == "move" and change.get("to_chapter") is not None:
            event["planned_chapter"] = change["to_chapter"]
        elif action == "drop" and event.get("status") != "done":
            event["status"] = "dropped"
        elif action == "edit" and change.get("summary"):
            event["summary"] = change["summary"]
    return list(by_id.values())


async def review_outline_if_due(
    *,
    chapter_no: int,
    every_k: int,
    moved_event_count: int,
    events: list[dict],
    evaluator: Callable[[list[dict]], OutlineProposal | dict | Awaitable],
) -> tuple[list[dict], OutlineProposal | None]:
    """Ask for an outline proposal only at a review boundary, then apply unlocked changes."""
    if not should_review_outline(chapter_no, every_k, moved_event_count):
        return [dict(event) for event in events], None
    proposal = evaluator([dict(event) for event in events])
    if isinstance(proposal, Awaitable):
        proposal = await proposal
    if not isinstance(proposal, OutlineProposal):
        proposal = OutlineProposal.model_validate(proposal)
    return apply_outline_proposal(proposal, events), proposal
