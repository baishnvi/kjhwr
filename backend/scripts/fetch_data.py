"""Download January-2026 wind data from Elexon into backend/data/wind_jan2026.json.

  python -m scripts.fetch_data                 # real data (needs internet)
  python -m scripts.fetch_data --demo out.json # synthetic data, offline development only
"""
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import data  # noqa: E402

F = "%Y-%m-%dT%H:%M:%SZ"


def demo(path: Path):
    rnd = random.Random(7)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    n = 33 * 48
    truth, v = [], 8000.0
    for _ in range(n):
        v = max(300, min(18000, v + rnd.gauss(0, 350) + 0.01 * (9000 - v)))
        truth.append(v)
    actuals = [[(start + timedelta(minutes=30 * i)).strftime(F), round(truth[i])] for i in range(n)]
    fc = []
    for p in range(32 * 24):
        pub = start + timedelta(hours=p)
        for h in range(1, 49):
            i = p * 2 + h * 2
            if i >= n:
                break
            g = max(0, truth[i] * 1.03 + rnd.gauss(0, 300 + 270 * math.sqrt(h)))
            fc.append([(start + timedelta(minutes=30 * i)).strftime(F), pub.strftime(F), round(g)])
    path.write_text(json.dumps({"meta": {"source": "SYNTHETIC DEMO DATA"}, "actuals": actuals, "forecasts": fc}))


if __name__ == "__main__":
    if "--demo" in sys.argv:
        out = Path(sys.argv[-1]) if sys.argv[-1].endswith(".json") else Path("demo.json")
        demo(out)
        print("wrote synthetic data to", out)
    else:
        s = data.build_snapshot()
        print("saved", data.SNAPSHOT, s["meta"])
