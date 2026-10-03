from writestory_ai.contracts.longform import PacingBudget


def compute_pacing(events_remaining: int, chapters_remaining: int) -> PacingBudget:
    if events_remaining < 0 or chapters_remaining < 0:
        raise ValueError("Remaining counts cannot be negative")
    if chapters_remaining == 0:
        return PacingBudget(
            events_remaining=events_remaining,
            chapters_remaining=0,
            ratio=0,
            recommended_events=(0, 0),
            warning="no_material" if not events_remaining else "crowded",
        )
    ratio = events_remaining / chapters_remaining
    lower = int(ratio)
    upper = lower + (1 if ratio > lower else 0)
    warning = (
        "crowded"
        if ratio > 3
        else "dragging"
        if ratio < 0.25 and events_remaining
        else "no_material"
        if not events_remaining
        else "none"
    )
    return PacingBudget(
        events_remaining=events_remaining,
        chapters_remaining=chapters_remaining,
        ratio=ratio,
        recommended_events=(lower, upper),
        warning=warning,
    )
