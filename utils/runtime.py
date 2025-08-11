"""Runtime utilities: track process start time and uptime."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

START_TIME = datetime.now(timezone.utc)


def uptime() -> timedelta:
    """Return process uptime as timedelta (UTC based)."""
    return datetime.now(timezone.utc) - START_TIME


def format_timedelta(td: timedelta) -> str:
    """Format timedelta as H:MM:SS (no days)."""
    total_seconds = int(td.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"
