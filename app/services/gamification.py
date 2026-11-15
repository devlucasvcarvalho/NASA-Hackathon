"""Rotinas do dia, histórico, streak e conquistas, calculados no servidor.

Regras idênticas às do front (`computeMetrics`), com uma melhoria: o streak exige
dias de calendário consecutivos.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import data
from app.models import AchievementUnlocked, Diagnosis, RoutineLog

HYDRATION_TASKS = {"m4", "t2", "n2"}
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# IDs de tarefas/conquistas e metas são iguais em todos os idiomas; a lógica usa "en" e só os textos mudam.
TASKS = {t["id"]: p["period"] for p in data.ROUTINE_TEMPLATE["en"] for t in p["tasks"]}
BY_PERIOD: dict[str, set[str]] = defaultdict(set)
for _id, _p in TASKS.items():
    BY_PERIOD[_p].add(_id)
ALL_IDS = set(TASKS)


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def valid_day(day: str | None) -> str:
    """Dia informado pelo cliente (fuso local dele) ou hoje em UTC."""
    if not day:
        return today_utc()
    if not DAY_RE.match(day):
        raise ValueError("day must be YYYY-MM-DD")
    date.fromisoformat(day)  # levanta ValueError se for data inexistente
    return day


def done_ids(db: Session, day: str) -> list[str]:
    return list(db.scalars(select(RoutineLog.task_id).where(RoutineLog.day == day).order_by(RoutineLog.done_at)))


def set_task(db: Session, day: str, task_id: str, done: bool) -> None:
    row = db.scalar(select(RoutineLog).where(RoutineLog.day == day, RoutineLog.task_id == task_id))
    if done and row is None:
        db.add(RoutineLog(day=day, task_id=task_id))
    elif not done and row is not None:
        db.delete(row)
    db.commit()


def score(ids: list[str]) -> int:
    return round(100 * len(set(ids) & ALL_IDS) / len(ALL_IDS)) if ALL_IDS else 0


def _per_day(db: Session) -> dict[str, set[str]]:
    days: dict[str, set[str]] = defaultdict(set)
    for d, t in db.execute(select(RoutineLog.day, RoutineLog.task_id)):
        days[d].add(t)
    return days


def _summ(ids: set[str]) -> dict:
    return {
        "done": len(ids & ALL_IDS),
        "total": len(ALL_IDS),
        "perfect": ALL_IDS <= ids,
        "mornings_full": BY_PERIOD["manha"] <= ids,
        "nights_full": BY_PERIOD["noite"] <= ids,
        "hyd": len(ids & HYDRATION_TASKS),
    }


def history(db: Session, days: int, today: str) -> list[dict]:
    per = _per_day(db)
    start = date.fromisoformat(today) - timedelta(days=days - 1)
    out = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        out.append({"day": d, **_summ(per.get(d, set()))})
    return out


def metrics(db: Session, today: str) -> dict:
    per = _per_day(db)
    summ = {d: _summ(ids) for d, ids in per.items()}
    perfect = {d for d, s in summ.items() if s["perfect"]}
    cur = date.fromisoformat(today)
    if today not in perfect:  # hoje ainda em andamento não quebra o streak
        cur -= timedelta(days=1)
    streak = 0
    while cur.isoformat() in perfect:
        streak += 1
        cur -= timedelta(days=1)
    return {
        "perfect_days": len(perfect),
        "streak": streak,
        "hydration_logs": sum(s["hyd"] for s in summ.values()),
        "mornings_full": sum(1 for s in summ.values() if s["mornings_full"]),
        "nights_full": sum(1 for s in summ.values() if s["nights_full"]),
        "diagnoses": db.scalar(select(func.count()).select_from(Diagnosis)) or 0,
        "image_diagnoses": db.scalar(select(func.count()).select_from(Diagnosis).where(Diagnosis.image_attached.is_(True))) or 0,
    }


def evaluate(db: Session, today: str, lang: str = "en") -> list[dict]:
    """Destrava o que ficou elegível; devolve só as conquistas NOVAS (para o toast do front)."""
    m = metrics(db, today)
    have = set(db.scalars(select(AchievementUnlocked.id)))
    new = []
    for a in data.ACHIEVEMENTS[lang]:
        if a["id"] not in have and m.get(a["metric"], 0) >= a["target"]:
            db.add(AchievementUnlocked(id=a["id"]))
            new.append(a)
    if new:
        db.commit()
    return new


def achievements_view(db: Session, today: str, lang: str = "en") -> dict:
    evaluate(db, today, lang)
    m = metrics(db, today)
    when = {r.id: r.ts for r in db.scalars(select(AchievementUnlocked))}
    items = []
    for a in data.ACHIEVEMENTS[lang]:
        cur = m.get(a["metric"], 0)
        items.append({**a, "unlocked": a["id"] in when, "unlocked_at": when[a["id"]].isoformat() if a["id"] in when else None,
                      "current": cur, "progress": round(min(1.0, cur / a["target"]), 2)})
    return {"achievements": items, "metrics": m}
