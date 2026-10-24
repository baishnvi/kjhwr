import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import analysis
from .data import DECISION_END, DECISION_START, get_dataset

app = FastAPI(title="Wind Forecast Monitor", version="1.0.0")
DEFAULT_CUTOFF_HOUR = 9.0  # day-ahead gate closure is mid-morning UK time; adjustable in the UI


def ds():
    try:
        return get_dataset()
    except Exception as e:  # network / missing snapshot
        raise HTTPException(503, f"Data unavailable: {e}")


def parse_day(s: str) -> datetime:
    try:
        d = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(422, "date must be YYYY-MM-DD")
    if not (DECISION_START <= d <= DECISION_END):
        raise HTTPException(422, "decision date must be within January 2026")
    return d


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    d = ds()
    return {"decisionFrom": DECISION_START.date().isoformat(),
            "decisionTo": DECISION_END.date().isoformat(),
            "defaultCutoffHour": DEFAULT_CUTOFF_HOUR,
            "actualPoints": len(d.actuals),
            "forecastPoints": sum(len(v) for v in d.fc.values()),
            **d.meta}


@app.get("/api/decision")
def decision(date: str, cutoff: float = Query(DEFAULT_CUTOFF_HOUR, ge=0, le=23.5)):
    """Forecast available when buying for the day after `date` (D-1 decision)."""
    return analysis.decision_view(ds(), parse_day(date), cutoff)


@app.get("/api/accuracy")
def accuracy(cutoff: float = Query(DEFAULT_CUTOFF_HOUR, ge=0, le=23.5)):
    return analysis.accuracy(ds(), cutoff)


@app.get("/api/horizon")
def horizon(bucket: int = Query(6, ge=1, le=24)):
    return analysis.horizon_accuracy(ds(), bucket_h=bucket)


# Serve the built React app when present (Docker single-container deploy)
DIST = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if f.is_file() else DIST / "index.html")
