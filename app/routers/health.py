from fastapi import APIRouter

from app import config, data, db

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "ai_ready": bool(config.gemini_key()),
        "db_ok": db.db_ok(),
        "mission": data.MISSION_NAME,
    }
