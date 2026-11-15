from fastapi import APIRouter

from app.services.simulator import simulated_vitals

router = APIRouter(prefix="/api", tags=["vitals"])


@router.get("/vitals")
def vitals():
    return simulated_vitals()
