from datetime import datetime, timezone


def now() -> datetime:
    """Return timezone-aware current datetime in UTC.

    Use this everywhere in the codebase instead of datetime.utcnow() or datetime.now()
    to ensure all timestamps are timezone-aware (UTC).
    """
    return datetime.now(timezone.utc)
