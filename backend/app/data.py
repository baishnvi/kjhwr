"""Dataset loading. A snapshot JSON (committed to the repo) is preferred so the
deployed app is fast and does not depend on Elexon being reachable. If it is
missing, data is fetched live and cached in a temp dir."""
import json
import os
import tempfile
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from . import elexon

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path(os.environ.get("DATA_FILE", ROOT / "data" / "wind_jan2026.json"))
CACHE = Path(tempfile.gettempdir()) / "wind_jan2026_cache.json"

# Purchase decisions made in January 2026 (D-1) -> delivery days 2 Jan .. 1 Feb 2026
DECISION_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DECISION_END = datetime(2026, 1, 31, tzinfo=timezone.utc)


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class Dataset:
    def __init__(self, actuals, forecasts, meta=None):
        # actuals: [[startTime, MW]]; forecasts: [[startTime, publishTime, MW]]
        self.meta = meta or {}
        self.actuals = {parse(s): float(g) for s, g in actuals}
        by_target = {}
        for s, p, g in forecasts:
            by_target.setdefault(parse(s), []).append((parse(p), float(g)))
        self.fc = {t: sorted(v) for t, v in by_target.items()}
        self._pub = {t: [p for p, _ in v] for t, v in self.fc.items()}

    def latest_before(self, target: datetime, cutoff: datetime):
        """Most recent forecast for `target` published at or before `cutoff`."""
        pubs = self._pub.get(target)
        if not pubs:
            return None
        i = bisect_right(pubs, cutoff)
        return self.fc[target][i - 1] if i else None

    def all_forecasts(self):
        for t, v in self.fc.items():
            for p, g in v:
                yield t, p, g


def build_snapshot(path: Path = SNAPSHOT):
    a_from = DECISION_START + timedelta(days=1)
    a_to = DECISION_END + timedelta(days=1)
    actuals = elexon.fetch_actuals(a_from, a_to)
    forecasts = elexon.fetch_forecasts(DECISION_START - timedelta(days=2),
                                       DECISION_END + timedelta(days=1))
    lo, hi = a_from, a_to + timedelta(days=1)
    fc = [[r["startTime"], r["publishTime"], r["generation"]] for r in forecasts
          if lo <= parse(r["startTime"]) < hi]
    ac = [[r["startTime"], r["generation"]] for r in actuals]
    snap = {"meta": {"fetchedAt": datetime.now(timezone.utc).isoformat(),
                     "source": "Elexon BMRS FUELHH (WIND) + WINDFOR",
                     "actualRows": len(ac), "forecastRows": len(fc)},
            "actuals": ac, "forecasts": fc}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, separators=(",", ":")))
    return snap


@lru_cache(maxsize=1)
def get_dataset() -> Dataset:
    for p in (SNAPSHOT, CACHE):
        if p.exists():
            snap = json.loads(p.read_text())
            return Dataset(snap["actuals"], snap["forecasts"], snap.get("meta"))
    snap = build_snapshot(CACHE)  # live fetch fallback
    return Dataset(snap["actuals"], snap["forecasts"], snap.get("meta"))
