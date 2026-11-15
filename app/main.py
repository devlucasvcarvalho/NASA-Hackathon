"""B.I.P — Biomedical Intelligent Partner · backend FastAPI.

Protótipo navegável para a NASA Space Apps. Dados de bordo simulados com
drift fisiológico suave; IA via Google Gemini quando GEMINI_API_KEY existe,
com fallback local curado (offline-friendly) — funciona 100% no demo.
Conteúdo em PT / EN / ES (parâmetro `lang`).
"""

import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import ai, data
from app.exams_data import EXAMS

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


def norm_lang(value) -> str:
    lang = (value or "").lower().split("-")[0]
    return lang if lang in data.LANGS else "en"


app = FastAPI(title="B.I.P — Biomedical Intelligent Partner", version="0.1.0")


@app.middleware("http")
async def no_cache(request, call_next):
    """Sempre revalidar HTML/CSS/JS: evita que o navegador misture versões antigas com novas."""
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static") or path in ("/manifest.json", "/favicon.svg"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------- Sinais vitais simulados ----------------
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
    dose_rate = 0.21 + 0.05 * math.sin(t / 400.0)  # mSv/dia típico entre-órbitas
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
        "ai_ready": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_ready": bool(os.getenv("GEMINI_API_KEY")), "mission": data.MISSION_NAME}


@app.get("/api/vitals")
def vitals():
    return simulated_vitals()


@app.get("/api/routines")
def routines(lang: str = "en"):
    lang = norm_lang(lang)
    return {"periods": data.ROUTINE_TEMPLATE[lang], "lang": lang}


@app.get("/api/achievements")
def achievements(lang: str = "en"):
    lang = norm_lang(lang)
    return {"achievements": data.ACHIEVEMENTS[lang], "lang": lang}


@app.get("/api/stock")
def stock(lang: str = "en"):
    lang = norm_lang(lang)
    return {"items": data.MISSION_STOCK[lang], "lang": lang}


@app.get("/api/exams")
def exams(lang: str = "en"):
    lang = norm_lang(lang)
    return {"exams": EXAMS[lang], "lang": lang}


@app.get("/api/exams/{exam_id}")
def exam_detail(exam_id: str, lang: str = "en"):
    lang = norm_lang(lang)
    for e in EXAMS[lang]:
        if e["id"] == exam_id:
            return e
    return JSONResponse({"error": "exam not found"}, status_code=404)


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []
    context: dict = {}
    lang: str = "en"


@app.post("/api/chat")
def chat(payload: ChatIn):
    lang = norm_lang(payload.lang)
    reply = ai.chat_reply(payload.message, payload.history, payload.context or simulated_vitals(), lang)
    return {"reply": reply, "lang": lang}


class DiagnoseIn(BaseModel):
    text: str
    image: str | None = None
    context: dict = {}
    lang: str = "en"


@app.post("/api/diagnose")
def diagnose_endpoint(payload: DiagnoseIn):
    lang = norm_lang(payload.lang)
    v = simulated_vitals()
    context = dict(payload.context or {})
    context.setdefault("heart_rate", f"{v['heart_rate']} bpm")
    context.setdefault("spo2", f"{v['spo2']}%")
    context.setdefault("bp", f"{v['bp_sys']}/{v['bp_dia']} mmHg")
    context.setdefault("temperature", f"{v['temperature']} °C")
    context.setdefault("sleep_hours", f"{v['sleep_hours']} h")
    context.setdefault("radiation_cumulative", f"{v['radiation_cumulative']} mSv")
    result = ai.diagnose(payload.text, context, payload.image, lang)
    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    result["query"] = payload.text
    if payload.image:
        result["image_attached"] = True
    return result


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.json")
def manifest():
    return JSONResponse({
        "name": "B.I.P — Biomedical Intelligent Partner",
        "short_name": "B.I.P",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0F3E3D",
        "theme_color": "#0F3E3D",
    })


@app.get("/favicon.svg")
def favicon():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")
