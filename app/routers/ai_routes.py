import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ai, config
from app.routers.content import norm_lang
from app.db import get_db
from app.models import ChatMessage, Diagnosis
from app.services import context as ctx_svc
from app.services import demo, gamification, history, simulator

router = APIRouter(prefix="/api", tags=["ai"])


def _ready(db: Session) -> None:
    try:
        history.ensure_history(db)
    except Exception as e:
        print(f"[history] {e}")


def _server_context(db: Session, scenario: str | None = None) -> dict | None:
    """Contexto clínico do servidor; se o banco falhar, devolve None e o chamador segue sem ele."""
    try:
        _ready(db)
        return ctx_svc.build(db, scenario=demo.resolve(db, scenario))
    except Exception as e:
        print(f"[context] {e}")
        return None


@router.get("/context")
def clinical_context(scenario: str | None = Query(None, description=f"demo: {', '.join(simulator.SCENARIOS)}"), db: Session = Depends(get_db)):
    """O que a IA enxerga: contexto clínico montado no servidor (debug/demo)."""
    c = _server_context(db, scenario)
    if c is None:
        raise HTTPException(503, "database unavailable")
    return c


# ---------------- Chat ----------------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=config.MAX_CHAT_CHARS)
    history: list[dict] = []
    context: dict = {}
    lang: str = "en"


@router.post("/chat")
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    sc = _server_context(db)
    base = payload.context or simulated_or_empty()
    context = ctx_svc.merge_with_client(sc["flat"], base) if sc else base
    lang = norm_lang(payload.lang)
    reply = ai.chat_reply(payload.message, payload.history, context, lang)
    try:
        db.add_all([ChatMessage(role="user", text=payload.message), ChatMessage(role="bip", text=reply)])
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[chat] não persistiu: {e}")
    return {"reply": reply, "lang": lang}


def simulated_or_empty() -> dict:
    return simulator.simulated_vitals()


@router.get("/chat/history")
def chat_history(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.scalars(select(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit)).all()
    return {"messages": [{"role": r.role, "text": r.text, "ts": r.ts.isoformat()} for r in reversed(rows)]}


# ---------------- Diagnóstico ----------------
IMAGE_RE = re.compile(r"^data:image/(png|jpe?g|webp|gif|heic|heif);base64,", re.IGNORECASE)


class DiagnoseIn(BaseModel):
    text: str = Field(min_length=1, max_length=config.MAX_TEXT_CHARS)
    image: str | None = None
    context: dict = {}
    scenario: str | None = None  # demo
    lang: str = "en"


@router.post("/diagnose")
def diagnose_endpoint(payload: DiagnoseIn, db: Session = Depends(get_db)):
    if payload.image:
        if not IMAGE_RE.match(payload.image):
            raise HTTPException(422, "image must be an image data URL (png, jpeg, webp, gif, heic)")
        approx_bytes = (len(payload.image) - payload.image.find(",") - 1) * 3 // 4
        if approx_bytes > config.max_image_bytes():
            raise HTTPException(413, f"image exceeds the {config.max_image_bytes() // (1024 * 1024)} MB limit")
    sc = _server_context(db, payload.scenario)
    if sc:
        context = ctx_svc.merge_with_client(sc["flat"], payload.context)
    else:  # sem banco: comportamento antigo (vitais simulados + contexto do cliente)
        v = simulator.simulated_vitals()
        context = dict(payload.context or {})
        context.setdefault("heart_rate", f"{v['heart_rate']} bpm")
        context.setdefault("spo2", f"{v['spo2']}%")
        context.setdefault("bp", f"{v['bp_sys']}/{v['bp_dia']} mmHg")
        context.setdefault("temperature", f"{v['temperature']} °C")
        context.setdefault("sleep_hours", f"{v['sleep_hours']} h")
        context.setdefault("radiation_cumulative", f"{v['radiation_cumulative']} mSv")

    lang = norm_lang(payload.lang)
    result = ai.diagnose(payload.text, context, payload.image, lang)
    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    result["query"] = payload.text
    if sc:
        result["risk_score"] = sc["structured"]["risk"]["score"]
        result["risk_level"] = sc["structured"]["risk"]["level"]
    if payload.image:
        result["image_attached"] = True
    try:
        row = Diagnosis(query=payload.text, image_attached=bool(payload.image), result=result)
        db.add(row)
        db.commit()
        result["id"] = row.id
        new = gamification.evaluate(db, gamification.today_utc(), lang)
        result["newly_unlocked"] = [{"id": a["id"], "title": a["title"]} for a in new]
    except Exception as e:
        db.rollback()
        print(f"[diagnose] não persistiu: {e}")
    return result


@router.get("/diagnoses")
def list_diagnoses(limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.scalars(select(Diagnosis).order_by(Diagnosis.id.desc()).limit(limit)).all()
    return {"diagnoses": [{**r.result, "id": r.id} for r in rows]}


@router.get("/diagnoses/{diag_id}")
def get_diagnosis(diag_id: int, db: Session = Depends(get_db)):
    r = db.get(Diagnosis, diag_id)
    if r is None:
        raise HTTPException(404, "diagnosis not found")
    return {**r.result, "id": r.id}
