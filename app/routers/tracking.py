"""Estado do usuário: rotinas, conquistas, humor (PHQ-2) e estoque de bordo."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import data
from app.db import get_db
from app.routers.content import norm_lang
from app.models import Mood, StockMove
from app.services import gamification as gm

router = APIRouter(prefix="/api", tags=["tracking"])


def _day(day: str | None) -> str:
    try:
        return gm.valid_day(day)
    except ValueError as e:
        raise HTTPException(422, str(e))


# ---------------- Rotinas ----------------
@router.get("/routines/today")
def routines_today(day: str | None = Query(None, description="YYYY-MM-DD in the client time zone; default: today (UTC)"), lang: str = "en", db: Session = Depends(get_db)):
    d = _day(day)
    lang = norm_lang(lang)
    ids = set(gm.done_ids(db, d))
    periods = []
    for p in data.ROUTINE_TEMPLATE[lang]:
        tasks = [{**t, "done": t["id"] in ids} for t in p["tasks"]]
        periods.append({**p, "tasks": tasks, "done": sum(t["done"] for t in tasks), "total": len(tasks)})
    return {"day": d, "lang": lang, "periods": periods, "score": gm.score(list(ids)), "done_ids": sorted(ids)}


def _toggle(db: Session, task_id: str, day: str | None, done: bool, lang: str = "en") -> dict:
    d = _day(day)
    if task_id not in gm.TASKS:
        raise HTTPException(404, "unknown task")
    gm.set_task(db, d, task_id, done)
    new = gm.evaluate(db, d, norm_lang(lang))
    ids = gm.done_ids(db, d)
    return {"day": d, "task_id": task_id, "done": done, "done_ids": ids, "score": gm.score(ids),
            "newly_unlocked": [{"id": a["id"], "title": a["title"]} for a in new]}


@router.post("/routines/{task_id}/complete")
def complete_task(task_id: str, day: str | None = None, lang: str = "en", db: Session = Depends(get_db)):
    return _toggle(db, task_id, day, True, lang)


@router.delete("/routines/{task_id}/complete")
def uncomplete_task(task_id: str, day: str | None = None, lang: str = "en", db: Session = Depends(get_db)):
    return _toggle(db, task_id, day, False, lang)


@router.get("/routines/history")
def routines_history(days: int = Query(14, ge=1, le=90), today: str | None = None, db: Session = Depends(get_db)):
    t = _day(today)
    return {"days": gm.history(db, days, t), "metrics": gm.metrics(db, t)}


# ---------------- Conquistas (calculadas no servidor; mantém a chave legada `achievements`) ----------------
@router.get("/achievements")
def achievements(today: str | None = None, lang: str = "en", db: Session = Depends(get_db)):
    lang = norm_lang(lang)
    return {**gm.achievements_view(db, _day(today), lang), "lang": lang}


# ---------------- Humor (PHQ-2) ----------------
class MoodIn(BaseModel):
    q1: int = Field(ge=0, le=3, description="Little interest or pleasure in doing things (0–3)")
    q2: int = Field(ge=0, le=3, description="Feeling down, depressed or hopeless (0–3)")


@router.post("/mood")
def add_mood(body: MoodIn, db: Session = Depends(get_db)):
    m = Mood(q1=body.q1, q2=body.q2, score=body.q1 + body.q2)
    db.add(m)
    db.commit()
    return {"id": m.id, "score": m.score, "positive_screen": m.score >= 3, "ts": m.ts.isoformat()}


@router.get("/mood")
def list_mood(days: int = Query(14, ge=1, le=90), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.scalars(select(Mood).where(Mood.ts >= since).order_by(Mood.ts)).all()
    entries = [{"ts": r.ts.isoformat(), "q1": r.q1, "q2": r.q2, "score": r.score, "positive_screen": r.score >= 3} for r in rows]
    return {"entries": entries, "latest": entries[-1] if entries else None,
            "avg_score": round(sum(e["score"] for e in entries) / len(entries), 2) if entries else None}


# ---------------- Ship stock (names/units differ per language; the index and quantities do not) ----------------
CANON = data.MISSION_STOCK["en"]  # movements are stored under the canonical (English) item name


def _stock_view(db: Session, lang: str = "en") -> list[dict]:
    deltas = dict(db.execute(select(StockMove.item, func.sum(StockMove.delta)).group_by(StockMove.item)).all())
    out = []
    for i, it in enumerate(data.MISSION_STOCK[lang]):
        base = it["qty"]
        cur = None if base is None else max(0, int(base + deltas.get(CANON[i]["name"], 0)))
        low = base is not None and cur <= max(1, int(base * 0.2))
        out.append({**it, "qty": cur, "initial": base, "low": low})
    return out


@router.get("/stock")
def stock(lang: str = "en", db: Session = Depends(get_db)):
    lang = norm_lang(lang)
    return {"items": _stock_view(db, lang), "lang": lang}


class ConsumeIn(BaseModel):
    item: str
    qty: int = Field(gt=0, le=1000)
    reason: str = ""


@router.post("/stock/consume")
def consume(body: ConsumeIn, lang: str = "en", db: Session = Depends(get_db)):
    lang = norm_lang(lang)
    view = _stock_view(db, lang)
    q = body.item.strip().lower()
    names = [{data_lang: data.MISSION_STOCK[data_lang][i]["name"].lower() for data_lang in data.LANGS} for i in range(len(view))]
    exact = [i for i, n in enumerate(names) if q in n.values()]
    hits = exact or [i for i, n in enumerate(names) if any(q in v for v in n.values())]
    if not hits:
        raise HTTPException(404, "item not found in stock")
    if len(hits) > 1:
        raise HTTPException(422, f"ambiguous item: {[view[i]['name'] for i in hits]}")
    i = hits[0]
    it = view[i]
    if it["qty"] is None:
        raise HTTPException(400, "item has no quantity control (equipment/kit)")
    if it["qty"] < body.qty:
        raise HTTPException(409, f"insufficient stock: {it['qty']} left")
    db.add(StockMove(item=CANON[i]["name"], delta=-body.qty, reason=body.reason[:200]))
    db.commit()
    left = it["qty"] - body.qty
    return {"item": it["name"], "consumed": body.qty, "left": left, "low": left <= max(1, int(it["initial"] * 0.2))}


@router.get("/stock/moves")
def stock_moves(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.scalars(select(StockMove).order_by(StockMove.id.desc()).limit(limit)).all()
    return {"moves": [{"ts": r.ts.isoformat(), "item": r.item, "delta": r.delta, "reason": r.reason} for r in rows]}
