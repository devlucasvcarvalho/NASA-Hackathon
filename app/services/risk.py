"""Score de risco do tripulante (0–100) com fatores explicáveis."""

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exams_data import EXAMS
from app.models import Mood, SleepNight
from app.services import anomaly, gamification, simulator, spaceweather
from app.services.ranges import CAREER_LIMIT_MSV, RANGES

_STATUS_EN = {"alerta": "alert", "vigilancia": "watch"}
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
        p = {"alerta": 12, "vigilancia": 5}.get(d["status"], 0)  # enum values stay in Portuguese (API contract)
        if p:
            vit_pts += p
            add(f"{RANGES[m]['label']}: {_STATUS_EN.get(d['status'], d['status'])}", p, f"{d['value']} {d['unit']} (expected ~{d['expected']}, z={d['z']})")
    mv = an["multivariate"]
    add("Anomalous multivariate pattern", {"alerta": 15, "vigilancia": 8}.get(mv["level"], 0),
        f"distance {mv['d2']} · drivers: {', '.join(mv['drivers']) or '—'}")

    # 2) sono: últimas 3 noites
    nights = db.scalars(select(SleepNight).order_by(SleepNight.day.desc()).limit(3)).all()
    if nights:
        avg = sum(n.hours for n in nights) / len(nights)
        add("Sleep deprivation", 10 if avg < 6 else 4 if avg < 7 else 0, f"average of {avg:.1f} h over the last {len(nights)} nights")
        add("Very short night", 5 if nights[0].hours < 5.5 else 0, f"last night: {nights[0].hours} h")

    # 3) radiação acumulada vs limite de carreira da NASA (600 mSv, NASA-STD-3001 Vol.1 [V1 4030])
    v = simulator.simulated_vitals(now)
    pct = v["radiation_cumulative"] / CAREER_LIMIT_MSV * 100
    add("Accumulated radiation", 10 if pct > 75 else 5 if pct > 50 else 0, f"{v['radiation_cumulative']} mSv ({pct:.0f}% of the {CAREER_LIMIT_MSV} mSv career limit)")

    # 3b) clima espacial real (NASA DONKI): impacto de CME em Marte / SEP
    try:
        sw = spaceweather.get(db, now, scenario)
        add(f"Space weather ({sw['alert']['level']})", {"warning": 15, "watch": 5}.get(sw["alert"]["level"], 0), sw["alert"]["message"])
    except Exception as e:  # clima espacial nunca derruba o risco
        print(f"[spaceweather] {e}")

    # 4) exames alterados
    flagged = [(e["name"], x["name"], x["flag"]) for e in EXAMS["en"] for x in e.get("values", []) if x.get("flag") in ("alto", "baixo", "atencao")]
    add("Abnormal exams", min(15, 5 * len(flagged)), "; ".join(f"{x} {f}" for _, x, f in flagged[:4]))

    # 5) humor (PHQ-2 ≥ 3 nos últimos 7 dias)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    mood = db.scalar(select(Mood).where(Mood.ts >= since).order_by(Mood.ts.desc()).limit(1))
    if mood is not None:
        add("Mood (PHQ-2)", 8 if mood.score >= 3 else 0, f"score {mood.score}/6")

    # 6) aderência à rotina nos últimos 3 dias fechados (só se já há registros no servidor)
    today = datetime.fromtimestamp(now, tz=timezone.utc).date()
    past = [gamification.done_ids(db, (today - timedelta(days=i)).isoformat()) for i in (1, 2, 3)]
    if any(past):
        avg = sum(gamification.score(p) for p in past) / 3
        add("Low routine adherence", 5 if avg < 50 else 0, f"average of {avg:.0f}% over the last 3 days")

    score = min(100.0, sum(f["points"] for f in factors))
    factors.sort(key=lambda f: -f["points"])
    return {
        "score": round(score, 1),
        "level": _level(score),
        "factors": factors,
        "anomaly": {"multivariate": mv, "scenario": an.get("scenario")},
        "ts": an.get("ts"),
    }
