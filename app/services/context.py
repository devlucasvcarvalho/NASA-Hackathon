"""Contexto clínico montado NO SERVIDOR para a IA (vitais, tendências, anomalias, sono,
exames, humor, rotina, risco). Substitui a string hardcoded que o front enviava.
"""

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import data
from app.exams_data import EXAMS
from app.models import Mood, RoutineLog, SleepNight, VitalSample
from app.services import anomaly, risk, simulator, spaceweather
from app.services.ranges import CAREER_LIMIT_MSV, RANGES, SPE_LIMIT_MSV

# campos que o front monta na mão (texto fixo) e que o servidor agora calcula
CLIENT_OWNED_BY_SERVER = {"exams", "vitals"}
TREND_METRICS =["heart_rate", "spo2", "temperature", "hrv", "hydration"]


def _trends(db: Session, now: float) -> dict:
    end = int(now // simulator.STEP) * simulator.STEP
    out = {}
    for m in TREND_METRICS:
        col = getattr(VitalSample, m)
        cur = db.scalar(select(func.avg(col)).where(VitalSample.ts > end - 86400, VitalSample.ts <= end))
        prev = db.scalar(select(func.avg(col)).where(VitalSample.ts > end - 2 * 86400, VitalSample.ts <= end - 86400))
        if cur is not None and prev is not None:
            out[m] = {"mean_24h": round(cur, 2), "prev_24h": round(prev, 2), "delta": round(cur - prev, 2)}
    return out


def _flagged_exams() -> list[dict]:
    res = []
    for e in EXAMS["en"]:
        for v in e.get("values", []):
            if v.get("flag") in ("alto", "baixo", "atencao"):
                res.append({"exam": e["name"], "date": e["date"], "item": v["name"], "value": f"{v['value']} {v['unit']}".strip(),
                            "ref": v["ref"], "flag": v["flag"]})
    return res


def build(db: Session, now: float | None = None, scenario: str | None = None) -> dict:
    now = time.time() if now is None else now
    v = simulator.simulated_vitals(now)
    an = anomaly.evaluate(db, now, scenario)
    rk = risk.compute(db, now, scenario)
    trends = _trends(db, now)
    nights = db.scalars(select(SleepNight).order_by(SleepNight.day.desc()).limit(3)).all()
    exams = _flagged_exams()
    mood = db.scalar(select(Mood).order_by(Mood.ts.desc()).limit(1))
    today = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
    done_today = db.scalar(select(func.count()).select_from(RoutineLog).where(RoutineLog.day == today)) or 0
    total_tasks = sum(len(p["tasks"]) for p in data.ROUTINE_TEMPLATE["en"])

    cur = {m: d["value"] for m, d in an["metrics"].items()} if an["metrics"] else {}
    if scenario and cur:  # o cenário de demo vale para o contexto também
        v = {**v, "heart_rate": round(cur["heart_rate"]), "spo2": cur["spo2"], "temperature": round(cur["temperature"], 1),
             "bp_sys": cur["bp_sys"], "bp_dia": cur["bp_dia"], "hydration": cur["hydration"]}

    def line(m: str) -> str:
        d = an["metrics"].get(m)
        if not d:
            return "no data"
        return f"{d['value']} {d['unit']} (expected ~{d['expected']} for this time of day; {d['status']})"

    abnormal = [f"{RANGES[m]['label']}: {d['status']} (z={d['z']})" for m, d in an["metrics"].items() if d["status"] != "normal"]
    flat = {
        "crew": f"{data.CREW_MEMBER['name']} · {data.CREW_MEMBER['role']} · {data.MISSION_NAME}",
        "heart_rate": f"{v['heart_rate']} bpm — {line('heart_rate')}",
        "spo2": f"{v['spo2']}% — {line('spo2')}",
        "bp": f"{v['bp_sys']}/{v['bp_dia']} mmHg",
        "temperature": f"{v['temperature']} °C — {line('temperature')}",
        "hrv": line("hrv"),
        "hydration": line("hydration"),
        "radiation_cumulative": f"{v['radiation_cumulative']} mSv (limite de carreira NASA {CAREER_LIMIT_MSV} mSv; evento solar ≤{SPE_LIMIT_MSV} mSv)",
        "sleep_hours": (f"last night {nights[0].hours} h; 3-night average {sum(n.hours for n in nights) / len(nights):.1f} h; "
                        f"{nights[0].awakenings} awakenings") if nights else "no data",
        "anomalies": "; ".join(abnormal) if abnormal else "no metric outside the expected range",
        "multivariate_pattern": f"{an['multivariate']['level']} (distance {an['multivariate']['d2']}; drivers: {', '.join(an['multivariate']['drivers']) or '—'})",
        "trends_24h": "; ".join(f"{RANGES[m]['label']} {t['delta']:+g} {RANGES[m]['unit']} vs previous day" for m, t in trends.items()) or "no data",
        "risk": f"{rk['score']}/100 ({rk['level']}) — " + "; ".join(f"{f['name']}" for f in rk["factors"][:4]),
        "flagged_exams": "; ".join(f"{e['item']} {e['value']} ({e['flag']}, ref {e['ref']}) on {e['date']}" for e in exams) or "none",
        "mood": f"PHQ-2 {mood.score}/6 on {mood.ts:%d/%m}" if mood else "no record",
        "routine_today": f"{done_today}/{total_tasks} tasks logged on the server" if done_today else "nothing logged on the server yet",
    }
    try:
        sw = spaceweather.get(db, now, scenario)
        origem = "NASA snapshot" if sw["snapshot"] else ("cache" if sw["stale"] else "live NASA DONKI")
        flat["space_weather"] = f"{sw['alert']['level']}: {sw['alert']['message']} [{origem}]"
    except Exception as e:
        print(f"[spaceweather] {e}")
    if scenario and an.get("scenario"):
        flat["demo_scenario"] = scenario
    return {
        "flat": flat,
        "structured": {
            "ts": an.get("ts"), "scenario": an.get("scenario"), "vitals": v, "anomaly": an, "risk": rk,
            "trends_24h": trends, "sleep": [{"day": n.day, "hours": n.hours, "awakenings": n.awakenings} for n in nights],
            "flagged_exams": exams, "mood": None if not mood else {"ts": mood.ts.isoformat(), "score": mood.score},
            "routine": {"done_today": done_today, "total": total_tasks},
        },
    }


def merge_with_client(server_flat: dict, client: dict | None) -> dict:
    """O servidor é a fonte da verdade; do cliente só entram campos que o servidor não conhece."""
    merged = dict(server_flat)
    for k, val in (client or {}).items():
        if k in CLIENT_OWNED_BY_SERVER:
            continue
        if k not in merged and val not in (None, ""):
            merged[k] = val
    return merged
