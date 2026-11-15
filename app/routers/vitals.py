from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SleepNight
from app.services import history, simulator
from app.services.ranges import METRICS

router = APIRouter(prefix="/api", tags=["vitals"])


def _safe_ensure(db: Session) -> None:
    try:
        history.ensure_history(db)
    except Exception as e:  # banco fora do ar não derruba o endpoint legado
        print(f"[history] {e}")


@router.get("/vitals")
def vitals(db: Session = Depends(get_db)):
    """Contrato legado + `metrics` (valor, status e delta por métrica, vindos do histórico)."""
    payload = simulator.simulated_vitals()
    try:
        history.ensure_history(db)
        payload["metrics"] = history.latest_metrics(db)
    except Exception as e:
        print(f"[history] {e}")
        payload["metrics"] = {}
    return payload


@router.get("/vitals/history")
def vitals_history(
    metric: str = Query(..., description=f"uma de: {', '.join(METRICS)}"),
    hours: int = Query(24, ge=1, le=24 * 30),
    points: int = Query(96, ge=2, le=1000),
    db: Session = Depends(get_db),
):
    if metric not in METRICS:
        raise HTTPException(422, f"metric inválida; use uma de {METRICS}")
    _safe_ensure(db)
    return history.series(db, metric, hours, points)


@router.get("/sleep")
def sleep(days: int = Query(14, ge=1, le=30), db: Session = Depends(get_db)):
    _safe_ensure(db)
    rows = db.scalars(select(SleepNight).order_by(SleepNight.day.desc()).limit(days)).all()
    nights = [
        {c: getattr(r, c) for c in ("day", "hours", "latency_min", "awakenings", "deep_pct", "rem_pct", "night_hr")}
        for r in reversed(rows)
    ]
    avg = round(sum(n["hours"] for n in nights) / len(nights), 2) if nights else None
    return {"nights": nights, "avg_hours": avg}
