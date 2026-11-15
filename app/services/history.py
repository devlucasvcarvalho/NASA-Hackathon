"""Histórico persistido das métricas do paciente.

- `ensure_history`: backfill inicial (HISTORY_DAYS) e catch-up preguiçoso até "agora".
  Na Vercel não há processo em background, então cada request completa o que falta.
- `series`, `latest_metrics`: leitura para os endpoints.
"""

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SleepNight, VitalSample
from app.services import simulator
from app.services.ranges import METRICS, RANGES, status_for

STEP = simulator.STEP
HISTORY_DAYS = int(os.getenv("HISTORY_DAYS", "30"))


def ensure_history(db: Session, now: float | None = None) -> int:
    """Garante amostras de vitais até `now` e noites de sono até hoje. Retorna linhas novas."""
    now = time.time() if now is None else now
    end = int(now // STEP) * STEP
    floor_ts = end - HISTORY_DAYS * 86400
    added = 0

    last = db.scalar(select(func.max(VitalSample.ts)))
    start = floor_ts if last is None else max(last + STEP, floor_ts)
    rows = [{"ts": t, **simulator.vital_sample(t)} for t in range(start, end + 1, STEP)]
    if rows:
        try:
            db.bulk_insert_mappings(VitalSample, rows)
            db.commit()
            added += len(rows)
        except IntegrityError:  # outra instância inseriu ao mesmo tempo
            db.rollback()

    today = datetime.fromtimestamp(now, tz=timezone.utc).date()
    wanted = [(today - timedelta(days=i)).isoformat() for i in range(HISTORY_DAYS + 1)]
    have = set(db.scalars(select(SleepNight.day).where(SleepNight.day.in_(wanted))))
    nights = [simulator.sleep_night(d) for d in wanted if d not in have]
    if nights:
        try:
            db.bulk_insert_mappings(SleepNight, nights)
            db.commit()
            added += len(nights)
        except IntegrityError:
            db.rollback()
    return added


def series(db: Session, metric: str, hours: int, points: int, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    end = int(now // STEP) * STEP
    since = end - hours * 3600
    col = getattr(VitalSample, metric)
    rows = db.execute(select(VitalSample.ts, col).where(VitalSample.ts >= since, VitalSample.ts <= end).order_by(VitalSample.ts)).all()
    # reduz para no máximo `points` pontos (média por bucket)
    per = max(1, -(-len(rows) // points)) if rows else 1
    out = []
    for i in range(0, len(rows), per):
        chunk = rows[i:i + per]
        out.append({"ts": chunk[-1][0], "value": round(sum(v for _, v in chunk) / len(chunk), 3)})
    vals = [v for _, v in rows]
    return {
        "metric": metric,
        "unit": RANGES[metric]["unit"],
        "step_s": STEP * per,
        "points": out,
        "stats": {"min": min(vals), "max": max(vals), "mean": round(sum(vals) / len(vals), 3)} if vals else None,
    }


def _at(db: Session, ts: int):
    return db.scalar(select(VitalSample).where(VitalSample.ts <= ts).order_by(VitalSample.ts.desc()).limit(1))


def latest_metrics(db: Session, now: float | None = None, scenario: str | None = None) -> dict:
    """Valor atual, status e delta vs. mesmo horário de ontem, por métrica."""
    now = time.time() if now is None else now
    end = int(now // STEP) * STEP
    cur = _at(db, end)
    prev = _at(db, end - 86400)
    out = {}
    if cur is None:
        return out
    shifted = simulator.apply_scenario({m: getattr(cur, m) for m in METRICS}, scenario)
    for m in METRICS:
        v = shifted[m]
        d = None if prev is None else round(v - getattr(prev, m), 2)
        unit = RANGES[m]["unit"]
        out[m] = {
            "value": v,
            "unit": unit,
            "status": status_for(m, v),
            "delta": d,
            "delta_text": None if d is None else f"{d:+g} {unit} vs ontem",
        }
    return out
