"""Simulador fisiológico determinístico.

`vital_sample(ts)` e `sleep_night(day)` dependem só do timestamp/dia (+ SEED), então o
histórico gravado no banco é reproduzível. Modelo: ritmo circadiano + sono (22:30–06:30 UTC)
+ exercício matinal (07:30–08:05) + ruído suave.
"""

import hashlib
import math
import random
from datetime import datetime, timezone

from app import config, data

STEP = 900  # segundos entre amostras (15 min)
SEED = 7


def _rng(*parts) -> random.Random:
    h = hashlib.sha256(f"{SEED}|{'|'.join(map(str, parts))}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def vital_sample(ts: int) -> dict:
    """Métricas do tripulante no instante `ts` (epoch UTC, alinhado ao STEP)."""
    b = int(ts // STEP)
    r = _rng("v", b)
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    h = dt.hour + dt.minute / 60
    day_rng = _rng("d", dt.strftime("%Y-%m-%d"))
    day_shift = day_rng.uniform(-1.5, 1.5)  # variação dia a dia

    asleep = h >= 22.5 or h < 6.5
    exercising = 7.5 <= h < 8.1
    circ = math.sin(2 * math.pi * (h - 9) / 24)

    hr = 68 + 5 * circ + day_shift + r.gauss(0, 1.6)
    if asleep:
        hr -= 9
    if exercising:
        hr += 45 + r.gauss(0, 4)
    hr = _clamp(hr, 42, 175)

    spo2 = _clamp(97.7 + r.gauss(0, 0.35) - (0.4 if asleep else 0), 90, 99.5)

    # hidratação: cai ao longo do dia, recupera nos horários de reidratação
    hyd = 78 - 9 * ((h - 6.5) % 24) / 16 + day_shift * 1.5 + r.gauss(0, 1.2)
    if exercising:
        hyd -= 5
    hyd = _clamp(hyd, 40, 98)

    bp_sys = _clamp(116 + 4 * circ + day_shift + r.gauss(0, 1.8) + (14 if exercising else 0) - (6 if asleep else 0), 85, 190)
    bp_dia = _clamp(76 + 3 * circ + day_shift * 0.5 + r.gauss(0, 1.3) + (5 if exercising else 0) - (5 if asleep else 0), 50, 115)

    temp = 36.5 + 0.3 * math.sin(2 * math.pi * (h - 11) / 24) + r.gauss(0, 0.07) + (0.45 if exercising else 0)
    temp = _clamp(temp, 35.0, 39.5)

    hrv = _clamp(52 - (hr - 66) * 0.55 + (10 if asleep else 0) + r.gauss(0, 3), 8, 110)

    rad = _clamp(0.21 + 0.03 * math.sin(b / 700.0) + r.gauss(0, 0.008), 0.05, 2.0)

    return {
        "heart_rate": round(hr, 1),
        "spo2": round(spo2, 1),
        "hydration": round(hyd, 1),
        "bp_sys": round(bp_sys, 0),
        "bp_dia": round(bp_dia, 0),
        "temperature": round(temp, 2),
        "hrv": round(hrv, 1),
        "radiation_rate": round(rad, 3),
    }


def sleep_night(day: str) -> dict:
    """Noite de sono que termina na manhã de `day` (YYYY-MM-DD)."""
    r = _rng("s", day)
    return {
        "day": day,
        "hours": round(_clamp(r.gauss(7.0, 0.7), 4.5, 9.0), 1),
        "latency_min": int(_clamp(r.gauss(18, 8), 3, 60)),
        "awakenings": int(_clamp(round(r.gauss(1.2, 1.0)), 0, 6)),
        "deep_pct": round(_clamp(r.gauss(18, 3), 8, 28), 1),
        "rem_pct": round(_clamp(r.gauss(21, 3), 10, 30), 1),
        "night_hr": round(_clamp(r.gauss(59, 2.5), 48, 75), 1),
    }


SCENARIOS = {
    # deslocamentos aplicados ao instante atual (demo); não são gravados no histórico
    "infection":   {"temperature": +1.6, "heart_rate": +22, "hrv": -20, "spo2": -2.0, "hydration": -6},
    "dehydration": {"hydration": -28, "heart_rate": +12, "bp_sys": -10, "hrv": -10},
    "stress":      {"heart_rate": +15, "hrv": -18, "bp_sys": +12, "bp_dia": +8},
    "spe":         {"radiation_rate": +2.4},  # evento de partículas solares
}


def apply_scenario(sample: dict, scenario: str | None) -> dict:
    if not scenario or scenario not in SCENARIOS:
        return dict(sample)
    out = dict(sample)
    for k, d in SCENARIOS[scenario].items():
        out[k] = round(out[k] + d, 3)
    return out


def _aligned(ts: float) -> int:
    return int(ts // STEP) * STEP


def simulated_vitals(now: float | None = None) -> dict:
    """Payload legado de /api/vitals (contrato do front), agora baseado no simulador."""
    import time

    t = time.time() if now is None else now
    s = vital_sample(_aligned(t))
    met_seconds = t - datetime(2026, 6, 11, 14, 32, tzinfo=timezone.utc).timestamp()
    days = max(0, int(met_seconds // 86400))
    today = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
    return {
        "heart_rate": round(s["heart_rate"], 0),
        "spo2": s["spo2"],
        "hydration": s["hydration"],
        "radiation_dose_rate": round(s["radiation_rate"], 2),
        "radiation_cumulative": round(days * 0.21, 2),
        "radiation_unit": "mSv",
        "bp_sys": s["bp_sys"],
        "bp_dia": s["bp_dia"],
        "temperature": round(s["temperature"], 1),
        "hrv": s["hrv"],
        "sleep_hours": sleep_night(today)["hours"],
        "met_seconds": int(met_seconds),
        "crew": data.CREW_MEMBER,
        "mission": data.MISSION_NAME,
        "launch_utc": data.LAUNCH_UTC,
        "ai_ready": bool(config.gemini_key()),
    }
