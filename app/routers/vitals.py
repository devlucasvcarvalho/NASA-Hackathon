from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SleepNight
from app.services import anomaly, demo, history, simulator
from app.services import risk as risk_svc
from app.services.ranges import CAREER_LIMIT_MSV, METRICS, RANGES, REFERENCES, SPE_LIMIT_MSV

router = APIRouter(prefix="/api", tags=["vitals"])


def _safe_ensure(db: Session) -> None:
    try:
        history.ensure_history(db)
    except Exception as e:  # banco fora do ar não derruba o endpoint legado
        print(f"[history] {e}")


@router.get("/vitals")
def vitals(scenario: str | None = Query(None, description="demo; without it, the active scenario (/api/demo) applies"), db: Session = Depends(get_db)):
    """Contrato legado + `metrics` (valor, status e delta por métrica, vindos do histórico)."""
    payload = simulator.simulated_vitals()
    sc = demo.resolve(db, scenario)
    try:
        history.ensure_history(db)
        payload["metrics"] = history.latest_metrics(db, scenario=sc)
        # status final = pior entre limite clínico e desvio vs. baseline do horário (mesmo critério do /risk)
        an = anomaly.evaluate(db, scenario=sc)
        for name, d in payload["metrics"].items():
            a = an["metrics"].get(name)
            if a:
                d.update(status=a["status"], z=a["z"], expected=a["expected"])
    except Exception as e:
        print(f"[history] {e}")
        payload["metrics"] = {}
    m = payload["metrics"]
    if sc and m:  # o cenário também vale para os campos legados que o front já lê
        for k in ("spo2", "hydration", "bp_sys", "bp_dia", "hrv"):
            payload[k] = m[k]["value"]
        payload["heart_rate"] = round(m["heart_rate"]["value"])
        payload["temperature"] = round(m["temperature"]["value"], 1)
        payload["radiation_dose_rate"] = round(m["radiation_rate"]["value"], 2)
    payload["scenario"] = sc
    return payload


@router.get("/vitals/history")
def vitals_history(
    metric: str = Query(..., description=f"uma de: {', '.join(METRICS)}"),
    hours: int = Query(24, ge=1, le=24 * 30),
    points: int = Query(96, ge=2, le=1000),
    db: Session = Depends(get_db),
):
    if metric not in METRICS:
        raise HTTPException(422, f"invalid metric; use one of {METRICS}")
    _safe_ensure(db)
    return history.series(db, metric, hours, points)


@router.get("/vitals/status")
def vitals_status(scenario: str | None = Query(None, description=f"demo: {', '.join(simulator.SCENARIOS)}"), db: Session = Depends(get_db)):
    """Por métrica: valor, esperado p/ a hora, z robusto, status; + anomalia multivariada."""
    _safe_ensure(db)
    return anomaly.evaluate(db, scenario=demo.resolve(db, scenario))


@router.get("/risk")
def risk(scenario: str | None = Query(None, description=f"demo: {', '.join(simulator.SCENARIOS)}"), db: Session = Depends(get_db)):
    """Risco global 0–100 com fatores explicáveis."""
    _safe_ensure(db)
    return risk_svc.compute(db, scenario=demo.resolve(db, scenario))


@router.get("/ranges")
def ranges():
    """Faixas de referência com a fonte de cada uma (`source.kind`: space_program | placeholder)."""
    out = {}
    for m, r in RANGES.items():
        lo_a, lo_w, hi_w, hi_a = r["limits"]
        out[m] = {"label": r["label"], "unit": r["unit"], "alert_lo": lo_a, "watch_lo": lo_w, "watch_hi": hi_w, "alert_hi": hi_a, "source": r["source"]}
    return {"ranges": out, "references": REFERENCES,
            "radiation_limits_msv": {"career": CAREER_LIMIT_MSV, "solar_particle_event": SPE_LIMIT_MSV}}


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
