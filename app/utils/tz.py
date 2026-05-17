from datetime import datetime, timezone


def now() -> datetime:
    """Return timezone-aware current datetime in UTC.

    Use this everywhere in the codebase instead of datetime.utcnow() or datetime.now()
    to ensure all timestamps are timezone-aware (UTC).
    """
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime.

    PostgreSQL TIMESTAMP columns can return naive datetimes even when the
    application originally saved aware UTC values. Treat naive values as UTC so
    comparisons stay consistent.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
