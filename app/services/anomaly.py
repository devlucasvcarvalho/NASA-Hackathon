"""Detecção de anomalia nos vitais do paciente.

Duas camadas, ambas calculadas contra o PRÓPRIO histórico do tripulante:
1. Univariada: z-score robusto (mediana/MAD) vs. baseline da mesma hora do dia
   (respeita o ritmo circadiano) + limites clínicos de `ranges.py`.
2. Multivariada: distância de Mahalanobis dos resíduos (captura correlação, ex.: FC alta
   com HRV baixa e temperatura alta ao mesmo tempo). Só numpy, leve para serverless.
"""

import time

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import VitalSample
from app.services import simulator
from app.services.ranges import METRICS, RANGES, status_for

STEP = simulator.STEP
Z_WATCH, Z_ALERT = 3.5, 5.0          # z robusto por métrica
D2_WATCH, D2_ALERT = 20.0, 30.0      # Mahalanobis² (8 graus de liberdade: p≈0,01 / p≈0,0002)
_ORDER = {"normal": 0, "vigilancia": 1, "alerta": 2}
_cache: dict = {}


def _worse(a: str, b: str) -> str:
    return a if _ORDER[a] >= _ORDER[b] else b


def _build_baseline(db: Session, now: float) -> dict:
    end = int(now // STEP) * STEP
    cols = [getattr(VitalSample, m) for m in METRICS]
    # baseline exclui as últimas 24 h, para um evento recente não "normalizar" a si mesmo
    rows = db.execute(select(VitalSample.ts, *cols).where(VitalSample.ts < end - 86400).order_by(VitalSample.ts)).all()
    if len(rows) < 24 * 4 * 3:
        return {}
    arr = np.array(rows, dtype=float)
    hours = ((arr[:, 0] // 3600) % 24).astype(int)
    X = arr[:, 1:]
    med = np.zeros((24, len(METRICS)))
    scale = np.zeros((24, len(METRICS)))
    for h in range(24):
        sel = X[hours == h]
        med[h] = np.median(sel, axis=0)
        mad = np.median(np.abs(sel - med[h]), axis=0) * 1.4826
        scale[h] = np.maximum(mad, np.maximum(0.01 * np.abs(med[h]), 1e-3))
    R = (X - med[hours]) / scale[hours]
    cov = np.cov(R.T) + 1e-3 * np.eye(len(METRICS))
    return {"med": med, "scale": scale, "cinv": np.linalg.pinv(cov), "n": len(rows)}


def _baseline(db: Session, now: float) -> dict:
    key = int(now // 3600)
    if _cache.get("key") != key or _cache.get("db") is not id(db.get_bind()):
        _cache.update(key=key, db=id(db.get_bind()), base=_build_baseline(db, now))
    return _cache["base"]


def _sample_at(db: Session, ts: int) -> dict | None:
    r = db.scalar(select(VitalSample).where(VitalSample.ts <= ts).order_by(VitalSample.ts.desc()).limit(1))
    return None if r is None else {m: getattr(r, m) for m in METRICS}


def evaluate_sample(db: Session, sample: dict, now: float) -> dict:
    """Avalia um conjunto de métricas no instante `now`."""
    base = _baseline(db, now)
    hour = int((now // 3600) % 24)
    metrics = {}
    r_vec = None
    if base:
        r_vec = (np.array([sample[m] for m in METRICS]) - base["med"][hour]) / base["scale"][hour]
    for i, m in enumerate(METRICS):
        v = sample[m]
        clinical = status_for(m, v)
        z = float(r_vec[i]) if r_vec is not None else 0.0
        stat = "alerta" if abs(z) >= Z_ALERT else "vigilancia" if abs(z) >= Z_WATCH else "normal"
        metrics[m] = {
            "value": v,
            "unit": RANGES[m]["unit"],
            "expected": None if not base else round(float(base["med"][hour][i]), 2),
            "z": round(z, 2),
            "clinical_status": clinical,
            "stat_status": stat,
            "status": _worse(clinical, stat),
        }
    multi = {"d2": 0.0, "level": "normal", "drivers": []}
    if r_vec is not None:
        d2 = float(r_vec @ base["cinv"] @ r_vec)
        # "drivers": métricas que mais puxam a distância (explicabilidade)
        contrib = np.abs(r_vec) * np.abs(base["cinv"] @ r_vec)
        order = np.argsort(-contrib)[:3]
        multi = {
            "d2": round(d2, 2),
            "level": "alerta" if d2 >= D2_ALERT else "vigilancia" if d2 >= D2_WATCH else "normal",
            "drivers": [METRICS[j] for j in order if contrib[j] > 1.0],
        }
    return {"metrics": metrics, "multivariate": multi, "baseline_n": base.get("n", 0) if base else 0}


def evaluate(db: Session, now: float | None = None, scenario: str | None = None) -> dict:
    now = time.time() if now is None else now
    ts = int(now // STEP) * STEP
    cur = _sample_at(db, ts)
    if cur is None:
        return {"metrics": {}, "multivariate": {"d2": 0.0, "level": "normal", "drivers": []}, "baseline_n": 0}
    cur = simulator.apply_scenario(cur, scenario)
    out = evaluate_sample(db, cur, ts)
    out["scenario"] = scenario if scenario in simulator.SCENARIOS else None
    out["ts"] = ts
    return out
