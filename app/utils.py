from datetime import datetime, timezone


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_etag(updated_at: str) -> str:
    # Use a simple ETag quoting the updated_at
    return f'"{updated_at}"'


def normalize_plate(plate: str) -> str:
    return plate.strip().upper()
