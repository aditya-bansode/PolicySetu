"""
PolicySetu — Utilities and Helpers
==================================
Hashing (SHA-256), UTC-to-Local timezone converters, and standardized API response formats.
"""

import hashlib
from datetime import datetime, timezone
import zoneinfo
from flask import jsonify


def hash_content(content: str | None) -> str:
    """Generate a SHA-256 content hash for duplicate detection and version verification."""
    if not content:
        content = ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    """Return the current UTC datetime (stored consistently in UTC in the database)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_datetime_local(dt: datetime | None, tz_name: str = "Asia/Kolkata", fmt: str = "%Y-%m-%d %H:%M:%S") -> str | None:
    """
    Format a UTC datetime into the local timezone (defaults to IST - Asia/Kolkata).
    """
    if dt is None:
        return None
    try:
        # If naive, treat as UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        target_tz = zoneinfo.ZoneInfo(tz_name)
        local_dt = dt.astimezone(target_tz)
        return local_dt.strftime(fmt)
    except Exception:
        return dt.strftime(fmt)


def api_response(data=None, success: bool = True, meta: dict | None = None, error: str | None = None, status_code: int = 200):
    """
    Standardized API response JSON payload:
    {
      "success": True/False,
      "data": ...,
      "meta": { "page": ..., "per_page": ..., "total": ..., "total_pages": ... },
      "error": "..." (or None)
    }
    """
    payload = {
        "success": success,
        "data": data,
        "meta": meta,
        "error": error,
    }
    return jsonify(payload), status_code
