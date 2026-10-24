"""All forecast-vs-actual maths. Pure Python, no heavy dependencies.

Convention: error = forecast - actual  (MW).
  error > 0  -> wind was OVER-forecast  -> buyer is short and must buy extra power
  error < 0  -> wind was UNDER-forecast -> buyer over-bought
"""
import math
from datetime import datetime, timedelta

from .data import DECISION_END, DECISION_START, Dataset

HALF_HOUR_H = 0.5


def quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * q
    f, c = math.floor(k), math.ceil(k)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def metrics(pairs):
    """pairs: list of (forecast, actual). Returns None when empty."""
    if not pairs:
        return None
    errs = [f - a for f, a in pairs]
    n = len(errs)
    abs_sorted = sorted(abs(e) for e in errs)
    err_sorted = sorted(errs)
    mean_actual = sum(a for _, a in pairs) / n
    mae = sum(abs_sorted) / n
    nz = [(f, a) for f, a in pairs if a > 0]
    return {
        "n": n,
        "mae": mae,
        "rmse": math.sqrt(sum(e * e for e in errs) / n),
        "bias": sum(errs) / n,
        "mape": 100 * sum(abs(f - a) / a for f, a in nz) / len(nz) if nz else None,
        "nmae": 100 * mae / mean_actual if mean_actual else None,
        "p50_abs": quantile(abs_sorted, 0.5),
        "p90_abs": quantile(abs_sorted, 0.9),
        "p95_abs": quantile(abs_sorted, 0.95),
        "q10": quantile(err_sorted, 0.10),
        "q90": quantile(err_sorted, 0.90),
        "mean_actual": mean_actual,
    }


def cutoff_for(delivery_day: datetime, cutoff_hour: float) -> datetime:
    """Decision gate: `cutoff_hour` (UTC == UK time in January) on the day before delivery."""
    d = delivery_day - timedelta(days=1)
    return d.replace(hour=int(cutoff_hour), minute=int(round((cutoff_hour % 1) * 60)))


def _z(d: datetime) -> str:
    return d.isoformat().replace("+00:00", "Z")


def day_ahead_rows(ds: Dataset, delivery_day: datetime, cutoff_hour: float):
    """One row per half-hour of the delivery day with the forecast that was
    available at decision time (latest publish <= cutoff)."""
    cutoff = cutoff_for(delivery_day, cutoff_hour)
    rows = []
    for i in range(48):
        t = delivery_day + timedelta(minutes=30 * i)
        fc = ds.latest_before(t, cutoff)
        rows.append({"t": _z(t), "actual": ds.actuals.get(t),
                     "forecast": fc[1] if fc else None,
                     "published": _z(fc[0]) if fc else None})
    return rows


def delivery_days():
    d, out = DECISION_START + timedelta(days=1), []
    while d <= DECISION_END + timedelta(days=1):
        out.append(d)
        d += timedelta(days=1)
    return out


def day_ahead_pairs(ds: Dataset, cutoff_hour: float):
    out = []
    for d in delivery_days():
        pairs = [(r["forecast"], r["actual"], r["t"]) for r in day_ahead_rows(ds, d, cutoff_hour)
                 if r["forecast"] is not None and r["actual"] is not None]
        out.append((d, pairs))
    return out


def decision_view(ds: Dataset, decision_day: datetime, cutoff_hour: float):
    delivery = decision_day + timedelta(days=1)
    rows = day_ahead_rows(ds, delivery, cutoff_hour)
    overall = accuracy(ds, cutoff_hour)["overall"] or {}
    q10, q90 = overall.get("q10"), overall.get("q90")
    for r in rows:
        f = r["forecast"]
        if f is not None and q10 is not None:
            # actual = forecast - error  ->  P10..P90 band for the actual
            r["low"], r["high"] = max(0.0, f - q90), max(0.0, f - q10)
        else:
            r["low"] = r["high"] = None
    have = [r for r in rows if r["forecast"] is not None]
    paired = [(r["forecast"], r["actual"]) for r in rows
              if r["forecast"] is not None and r["actual"] is not None]
    pubs = sorted({r["published"] for r in have})
    return {
        "decisionDay": decision_day.date().isoformat(),
        "deliveryDay": delivery.date().isoformat(),
        "cutoff": _z(cutoff_for(delivery, cutoff_hour)),
        "points": rows,
        "forecastPublishedRange": [pubs[0], pubs[-1]] if pubs else None,
        "forecastMWh": sum(r["forecast"] for r in have) * HALF_HOUR_H if have else None,
        "actualMWh": sum(a for _, a in paired) * HALF_HOUR_H if paired else None,
        "peakForecastMW": max((r["forecast"] for r in have), default=None),
        "minForecastMW": min((r["forecast"] for r in have), default=None),
        "metrics": metrics(paired),
        "bufferP90MW": q90,  # wind shortfall vs forecast to plan for (90% of half-hours)
        "errorQ10": q10, "errorQ90": q90,
    }


_acc_cache = {}


def accuracy(ds: Dataset, cutoff_hour: float):
    key = (id(ds), cutoff_hour)
    if key in _acc_cache:
        return _acc_cache[key]
    days = day_ahead_pairs(ds, cutoff_hour)
    allp = [(f, a) for _, ps in days for f, a, _ in ps]
    daily = []
    for d, ps in days:
        m = metrics([(f, a) for f, a, _ in ps])
        daily.append({"date": d.date().isoformat(), **(m or {"n": 0})})
    hourly = []
    for h in range(24):
        ps = [(f, a) for _, ps_ in days for f, a, t in ps_
              if int(t[11:13]) == h]
        hourly.append({"hour": h, **(metrics(ps) or {"n": 0})})
    width, hist = 500, {}
    for e in sorted(f - a for f, a in allp):
        b = math.floor(e / width) * width
        hist[b] = hist.get(b, 0) + 1
    res = {"cutoffHour": cutoff_hour, "overall": metrics(allp), "daily": daily, "hourly": hourly,
           "histogram": [{"from": b, "to": b + width, "count": c} for b, c in sorted(hist.items())]}
    _acc_cache[key] = res
    return res


def horizon_accuracy(ds: Dataset, bucket_h: int = 6, max_h: int = 48):
    """Error vs how far ahead the forecast was made (all published forecasts)."""
    buckets = {}
    for t, p, g in ds.all_forecasts():
        a = ds.actuals.get(t)
        h = (t - p).total_seconds() / 3600
        if a is None or h < 0 or h >= max_h:
            continue
        buckets.setdefault(int(h // bucket_h), []).append((g, a))
    return [{"from": b * bucket_h, "to": (b + 1) * bucket_h,
             "label": f"{b * bucket_h}-{(b + 1) * bucket_h}h", **metrics(buckets[b])}
            for b in sorted(buckets)]
