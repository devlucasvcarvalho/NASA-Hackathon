"""Faixas de referência por métrica e classificação de status.

(alert_lo, watch_lo, watch_hi, alert_hi): dentro de [watch_lo, watch_hi] = normal;
entre alert e watch = vigilância; fora de alert = alerta. None = sem limite.
Valores de adulto saudável em missão (ordem de grandeza ISS/HRP; ajustar com fonte NASA).
"""

RANGES = {
    "heart_rate":     {"unit": "bpm",     "label": "Frequência cardíaca", "limits": (45, 50, 100, 115)},
    "spo2":           {"unit": "%",       "label": "SpO₂",                "limits": (92, 95, None, None)},
    "hydration":      {"unit": "%",       "label": "Hidratação",          "limits": (50, 60, None, None)},
    "bp_sys":         {"unit": "mmHg",    "label": "PA sistólica",        "limits": (85, 90, 130, 140)},
    "bp_dia":         {"unit": "mmHg",    "label": "PA diastólica",       "limits": (55, 60, 85, 90)},
    "temperature":    {"unit": "°C",      "label": "Temperatura",         "limits": (35.3, 35.8, 37.3, 38.0)},
    "hrv":            {"unit": "ms",      "label": "HRV (RMSSD)",         "limits": (20, 30, None, None)},
    "radiation_rate": {"unit": "mSv/dia", "label": "Taxa de radiação",    "limits": (None, None, 0.5, 1.0)},
}

# no ritmo circadiano e no exercício a FC/PA sobem legitimamente; o status usa tolerância maior
METRICS = list(RANGES)


def status_for(metric: str, value: float) -> str:
    alert_lo, watch_lo, watch_hi, alert_hi = RANGES[metric]["limits"]
    if (alert_lo is not None and value < alert_lo) or (alert_hi is not None and value > alert_hi):
        return "alerta"
    if (watch_lo is not None and value < watch_lo) or (watch_hi is not None and value > watch_hi):
        return "vigilancia"
    return "normal"
