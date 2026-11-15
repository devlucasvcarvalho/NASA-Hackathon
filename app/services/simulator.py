"""Simulador de vitais (Fase 0: mesma lógica de antes; Fase 1 vira série determinística)."""

import math
import time
from datetime import datetime, timezone

from app import config, data


def simulated_vitals() -> dict:
    t = time.time()
    hr = 71 + 3.5 * math.sin(t / 47.0) + 1.5 * math.sin(t / 7.3)
    spo2 = round(97.6 + 1.2 * math.sin(t / 63.0 + 1.7), 1)
    hydration = round(max(52, min(96, 71 + 9 * math.sin(t / 210.0 + 0.6))), 1)
    bp_sys = round(118 + 4 * math.sin(t / 120.0), 0)
    bp_dia = round(77 + 3 * math.sin(t / 130.0 + 0.8), 0)
    temp = round(36.4 + 0.2 * math.sin(t / 150.0 + 2.1), 1)
    met_seconds = t - datetime(2026, 6, 11, 14, 32, tzinfo=timezone.utc).timestamp()
    days = max(0, int(met_seconds // 86400))
    dose_rate = 0.21 + 0.05 * math.sin(t / 400.0)
    return {
        "heart_rate": round(hr, 0),
        "spo2": spo2,
        "hydration": hydration,
        "radiation_dose_rate": round(dose_rate, 2),
        "radiation_cumulative": round(days * dose_rate, 2),
        "radiation_unit": "mSv",
        "bp_sys": bp_sys,
        "bp_dia": bp_dia,
        "temperature": temp,
        "sleep_hours": 7.2,
        "met_seconds": int(met_seconds),
        "crew": data.CREW_MEMBER,
        "mission": data.MISSION_NAME,
        "launch_utc": data.LAUNCH_UTC,
        "ai_ready": bool(config.gemini_key()),
    }
