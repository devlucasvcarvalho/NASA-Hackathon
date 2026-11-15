"""Controle do modo demo (cenários clínicos simulados)."""

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import demo, simulator

router = APIRouter(prefix="/api/demo", tags=["demo"])


def _auth(x_demo_token: str | None = Header(None)) -> None:
    """Se DEMO_TOKEN estiver definido, exige o header X-Demo-Token (evita que qualquer visitante mude a demo)."""
    token = os.getenv("DEMO_TOKEN")
    if token and x_demo_token != token:
        raise HTTPException(401, "invalid X-Demo-Token")


@router.get("")
def state(db: Session = Depends(get_db)):
    return {"active": demo.active(db), "available": [{"id": k, "description": v} for k, v in demo.DESCRIPTIONS.items()]}


class ScenarioIn(BaseModel):
    scenario: str | None = None  # null/"" desativa


@router.post("/scenario", dependencies=[Depends(_auth)])
def set_scenario(body: ScenarioIn, db: Session = Depends(get_db)):
    try:
        sc = demo.set_active(db, body.scenario or None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"active": sc, "affects": ["/api/vitals", "/api/vitals/status", "/api/risk", "/api/context", "/api/diagnose", "/api/chat"],
            "scenarios": list(simulator.SCENARIOS)}
