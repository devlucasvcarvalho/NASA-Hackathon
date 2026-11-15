"""Clima espacial real (NASA DONKI) para a Base Ares, em Marte."""

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import demo, spaceweather

router = APIRouter(prefix="/api", tags=["space-weather"])


@router.get("/space-weather")
def space_weather(
    scenario: str | None = Query(None, description="demo: `spe` injects a SIMULATED (labelled) event"),
    refresh: bool = Query(False, description="force a fresh NASA query (uses quota; needs X-Demo-Token when DEMO_TOKEN is set)"),
    x_demo_token: str | None = Header(None),
    db: Session = Depends(get_db),
):
    if refresh:
        token = os.getenv("DEMO_TOKEN")
        if token and x_demo_token != token:
            raise HTTPException(401, "refresh requires X-Demo-Token")
    return spaceweather.get(db, scenario=demo.resolve(db, scenario), force=refresh)
