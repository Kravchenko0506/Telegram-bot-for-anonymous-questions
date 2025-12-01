"""Time formatting utilities for admin timezone display.

"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
import logging

_logger = logging.getLogger(__name__)


def _load_admin_tz() -> ZoneInfo:
    tz_name = os.getenv("ADMIN_TIMEZONE", "UTC")
    try:
        return ZoneInfo(tz_name)
    except Exception:  # pragma: no cover
        _logger.warning(f"Invalid ADMIN_TIMEZONE '{tz_name}', fallback to UTC")
        return ZoneInfo("UTC")


ADMIN_TZ: ZoneInfo = _load_admin_tz()


def ensure_utc(dt: datetime) -> datetime:
    """Return dt as UTC-aware datetime.

    If naive -> assume it is already UTC and attach timezone.utc.
    If tz-aware -> convert to UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_admin_time(dt: datetime, pattern: str = "%d.%m.%Y %H:%M") -> str:
    """Format datetime for admin in configured timezone."""
    try:
        dt_utc = ensure_utc(dt)
        return dt_utc.astimezone(ADMIN_TZ).strftime(pattern)
    except Exception as e:  # pragma: no cover
        _logger.error(f"Time format error: {e}")
        return "--"


__all__ = [
    "format_admin_time",
    "ensure_utc",
    "ADMIN_TZ",
]
