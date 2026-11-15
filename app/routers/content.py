"""Conteúdo estático da missão: rotinas, conquistas, estoque, exames."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import data

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/routines")
def routines():
    return {"periods": data.ROUTINE_TEMPLATE}


@router.get("/achievements")
def achievements():
    return {"achievements": data.ACHIEVEMENTS}


@router.get("/stock")
def stock():
    return {"items": data.MISSION_STOCK}


@router.get("/exams")
def exams():
    return {"exams": data.EXAMS}


@router.get("/exams/{exam_id}")
def exam_detail(exam_id: str):
    for e in data.EXAMS:
        if e["id"] == exam_id:
            return e
    return JSONResponse({"error": "exam not found"}, status_code=404)
