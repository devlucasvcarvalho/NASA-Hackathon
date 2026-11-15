"""Modo demo: cenário global ativo (ex.: infecção) que todos os endpoints respeitam.

Guardado no banco (e não em memória) para valer entre instâncias serverless.
Um `?scenario=` explícito sempre tem prioridade sobre o cenário ativo.
"""

from sqlalchemy.orm import Session

from app.models import AppState
from app.services import simulator

KEY = "demo_scenario"
DESCRIPTIONS = {
    "infection": "Infectious picture: fever, tachycardia, low HRV, slightly reduced SpO₂",
    "dehydration": "Dehydration: low hydration, high HR, reduced systolic BP",
    "stress": "Acute stress: high HR and BP, low HRV",
    "spe": "Solar particle event: radiation rate far above normal",
}


def active(db: Session) -> str | None:
    row = db.get(AppState, KEY)
    return row.value if row and row.value in simulator.SCENARIOS else None


def set_active(db: Session, scenario: str | None) -> str | None:
    if scenario is not None and scenario not in simulator.SCENARIOS:
        raise ValueError(f"invalid scenario; use one of {list(simulator.SCENARIOS)}")
    row = db.get(AppState, KEY)
    if row is None:
        row = AppState(key=KEY, value=scenario or "")
        db.add(row)
    else:
        row.value = scenario or ""
    db.commit()
    return scenario


def resolve(db: Session, explicit: str | None) -> str | None:
    """`?scenario=` explícito vence; senão vale o cenário ativo (se houver)."""
    if explicit:
        return explicit if explicit in simulator.SCENARIOS else None
    try:
        return active(db)
    except Exception:  # banco fora do ar: segue sem cenário
        return None
