"""Score de risco do tripulante (0–100) com fatores explicáveis."""

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import data
from app.models import Mood, SleepNight
from app.services import anomaly, simulator
from app.services.ranges import RANGES

LEVELS = [(25, "baixo"), (50, "moderado"), (75, "alto"), (101, "critico")]


def _level(score: float) -> str:
    return next(name for lim, name in LEVELS if score < lim)


def compute(db: Session, now: float | None = None, scenario: str | None = None) -> dict:
    now = time.time() if now is None else now
    factors: list[dict] = []

    def add(name: str, points: float, detail: str):
        if points > 0:
            factors.append({"name": name, "points": round(points, 1), "detail": detail})

    # 1) vitais atuais (clínico + estatístico) e multivariado
    an = anomaly.evaluate(db, now, scenario)
    vit_pts = 0.0
    for m, d in an["metrics"].items():
        p = {"alerta": 12, "vigilancia": 5}.get(d["status"], 0)
        if p:
            vit_pts += p
            add(f"{RANGES[m]['label']} {d['status']}", p, f"{d['value']} {d['unit']} (esperado ~{d['expected']}, z={d['z']})")
    mv = an["multivariate"]
    add("Padrão multivariado anômalo", {"alerta": 15, "vigilancia": 8}.get(mv["level"], 0),
        f"distância {mv['d2']} · fatores: {', '.join(mv['drivers']) or '—'}")

    # 2) sono: últimas 3 noites
    nights = db.scalars(select(SleepNight).order_by(SleepNight.day.desc()).limit(3)).all()
    if nights:
        avg = sum(n.hours for n in nights) / len(nights)
        add("Privação de sono", 10 if avg < 6 else 4 if avg < 7 else 0, f"média de {avg:.1f} h nas últimas {len(nights)} noites")
        add("Noite muito curta", 5 if nights[0].hours < 5.5 else 0, f"última noite: {nights[0].hours} h")

    # 3) radiação acumulada vs limite da missão (180 mSv)
    v = simulator.simulated_vitals(now)
    pct = v["radiation_cumulative"] / 180 * 100
    add("Radiação acumulada", 10 if pct > 75 else 5 if pct > 50 else 0, f"{v['radiation_cumulative']} mSv ({pct:.0f}% do limite)")

    # 4) exames alterados
    flagged = [(e["name"], x["name"], x["flag"]) for e in data.EXAMS for x in e.get("values", []) if x.get("flag") in ("alto", "baixo", "atencao")]
    add("Exames alterados", min(15, 5 * len(flagged)), "; ".join(f"{x} {f}" for _, x, f in flagged[:4]))

    # 5) humor (PHQ-2 ≥ 3 nos últimos 7 dias)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    mood = db.scalar(select(Mood).where(Mood.ts >= since).order_by(Mood.ts.desc()).limit(1))
    if mood is not None:
        add("Humor (PHQ-2)", 8 if mood.score >= 3 else 0, f"score {mood.score}/6")

    score = min(100.0, sum(f["points"] for f in factors))
    factors.sort(key=lambda f: -f["points"])
    return {
        "score": round(score, 1),
        "level": _level(score),
        "factors": factors,
        "anomaly": {"multivariate": mv, "scenario": an.get("scenario")},
        "ts": an.get("ts"),
    }
