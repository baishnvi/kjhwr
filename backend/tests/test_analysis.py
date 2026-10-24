import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import analysis  # noqa: E402
from app.data import Dataset  # noqa: E402

D = datetime(2026, 1, 10, tzinfo=timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def make():
    pubs = [D - timedelta(days=1, hours=5), D - timedelta(days=1, hours=2), D - timedelta(hours=2)]
    return Dataset([[iso(D), 1000]], [[iso(D), iso(p), g] for p, g in zip(pubs, [900, 1100, 5000])])


def test_latest_before_cutoff_ignores_later_forecasts():
    pub, gen = make().latest_before(D, datetime(2026, 1, 9, 9, tzinfo=timezone.utc))
    assert gen == 1100  # 07:00 vintage, not the 22:00 one


def test_metrics_and_sign_convention():
    m = analysis.metrics([(1100, 1000), (900, 1000), (1300, 1000)])
    assert m["mae"] == 500 / 3
    assert m["bias"] == 300 / 3  # forecast - actual
    assert m["n"] == 3


def test_day_ahead_rows_use_cutoff():
    rows = analysis.day_ahead_rows(make(), D, 9)
    assert rows[0]["forecast"] == 1100 and rows[0]["actual"] == 1000
    assert rows[1]["forecast"] is None


def test_quantile():
    assert analysis.quantile([1, 2, 3, 4, 5], 0.5) == 3
    assert analysis.quantile([], 0.5) is None
