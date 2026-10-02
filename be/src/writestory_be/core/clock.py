from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    """ISO 8601 UTC, độ chính xác mili giây, hậu tố `Z` (F01 be.md §A.2)."""
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def utcnow_iso() -> str:
    return to_iso(utcnow())
