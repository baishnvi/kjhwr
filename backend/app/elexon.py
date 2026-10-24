"""Thin client for the Elexon BMRS open-data API (no API key required).

Only two datasets are used:
  * FUELHH  - half-hourly actual generation by fuel type (we keep WIND)
  * WINDFOR - national wind generation forecasts (many forecasts per target time)
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
UA = {"User-Agent": "wind-forecast-monitor/1.0", "Accept": "application/json"}


def _get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def fetch_actuals(start: datetime, end: datetime, chunk_days: int = 7):
    """Actual WIND generation. start/end are inclusive settlement dates (UTC)."""
    out, cur = [], start
    while cur <= end:
        nxt = min(cur + timedelta(days=chunk_days - 1), end)
        q = urllib.parse.urlencode(
            {"settlementDateFrom": cur.strftime("%Y-%m-%d"),
             "settlementDateTo": nxt.strftime("%Y-%m-%d"),
             "fuelType": "WIND", "format": "json"})
        rows = _get(f"{BASE}/FUELHH/stream?{q}")
        out += [r for r in rows if r.get("fuelType") == "WIND"]
        cur = nxt + timedelta(days=1)
    return out


def fetch_forecasts(start: datetime, end: datetime, chunk_days: int = 3):
    """WINDFOR forecasts published in [start, end). Splits the window on HTTP 400."""
    def window(a, b):
        q = urllib.parse.urlencode(
            {"publishDateTimeFrom": _iso(a), "publishDateTimeTo": _iso(b), "format": "json"})
        try:
            return _get(f"{BASE}/WINDFOR/stream?{q}")
        except urllib.error.HTTPError as e:
            if e.code == 400 and (b - a) > timedelta(hours=6):
                mid = a + (b - a) / 2
                return window(a, mid) + window(mid, b)
            raise
    out, cur = [], start
    while cur < end:
        nxt = min(cur + timedelta(days=chunk_days), end)
        out += window(cur, nxt)
        cur = nxt
    return out
