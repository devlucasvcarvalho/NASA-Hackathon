from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app import ai
from app.services.simulator import simulated_vitals

router = APIRouter(prefix="/api", tags=["ai"])


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []
    context: dict = {}


@router.post("/chat")
def chat(payload: ChatIn):
    reply = ai.chat_reply(payload.message, payload.history, payload.context or simulated_vitals())
    return {"reply": reply}


class DiagnoseIn(BaseModel):
    text: str
    image: str | None = None
    context: dict = {}


@router.post("/diagnose")
def diagnose_endpoint(payload: DiagnoseIn):
    v = simulated_vitals()
    context = dict(payload.context or {})
    context.setdefault("heart_rate", f"{v['heart_rate']} bpm")
    context.setdefault("spo2", f"{v['spo2']}%")
    context.setdefault("bp", f"{v['bp_sys']}/{v['bp_dia']} mmHg")
    context.setdefault("temperature", f"{v['temperature']} °C")
    context.setdefault("sleep_hours", f"{v['sleep_hours']} h")
    context.setdefault("radiation_cumulative", f"{v['radiation_cumulative']} mSv")
    result = ai.diagnose(payload.text, context, payload.image)
    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    result["query"] = payload.text
    if payload.image:
        result["image_attached"] = True
    return result
