from app.utils import normalize_plate, make_etag, now_utc_iso
from datetime import datetime
import re


def test_normalize_plate():
    assert normalize_plate(" ab12 ") == "AB12"
    assert normalize_plate("xyZ") == "XYZ"


def test_make_etag_and_format():
    ts = "2026-02-03T12:00:00+00:00"
    etag = make_etag(ts)
    assert etag.startswith('"') and etag.endswith('"')


def test_now_utc_iso_returns_iso():
    s = now_utc_iso()
    # simple ISO-ish pattern check
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", s)
