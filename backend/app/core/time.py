"""Time helpers shared by persistence and application services."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time without a timezone marker.

    Existing SQLite ``DateTime`` columns store naive UTC values. Keeping that
    representation preserves compatibility while avoiding ``datetime.utcnow``.
    """

    return datetime.now(UTC).replace(tzinfo=None)
