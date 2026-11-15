"""Static mission content (PT / EN / ES via `?lang=`): routine template and exams.

Achievements and stock live in `tracking.py` (they carry server-side state).
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import data
from app.exams_data import EXAMS

router = APIRouter(prefix="/api", tags=["content"])


def norm_lang(value) -> str:
    lang = (value or "").lower().split("-")[0]
    return lang if lang in data.LANGS else "en"


@router.get("/routines")
def routines(lang: str = "en"):
    lang = norm_lang(lang)
    return {"periods": data.ROUTINE_TEMPLATE[lang], "lang": lang}


@router.get("/exams")
def exams(lang: str = "en"):
    lang = norm_lang(lang)
    return {"exams": EXAMS[lang], "lang": lang}


@router.get("/exams/{exam_id}")
def exam_detail(exam_id: str, lang: str = "en"):
    lang = norm_lang(lang)
    for e in EXAMS[lang]:
        if e["id"] == exam_id:
            return e
    return JSONResponse({"error": "exam not found"}, status_code=404)
