from datetime import datetime, timezone


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_etag(updated_at: str) -> str:
    # Use a simple ETag quoting the updated_at
    return f'"{updated_at}"'


def normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def truncate_to_milliseconds(dt):
    """Truncate microseconds to milliseconds (3 digits instead of 6).
    
    MongoDB stores datetimes with millisecond precision, so we truncate
    microseconds to avoid precision loss on round-trip.
    """
    if dt is None or not isinstance(dt, datetime):
        return dt
    # Keep only milliseconds (3 decimal places)
    return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)


def serialize_datetime(dt) -> str:
    """Serialize a datetime to ISO format string with UTC timezone info.
    
    Handles both timezone-aware and naive datetimes.
    MongoDB returns naive datetimes (stored as UTC), so we add timezone info back.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
