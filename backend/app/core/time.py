"""Time utilities for consistent UTC handling."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time as a naive datetime for DB compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
