"""Clima espacial real: NASA DONKI (CCMC), previsão de impacto de CMEs em MARTE e eventos SEP.

Dados: https://api.nasa.gov/ (DONKI). Endpoints usados: WSAEnlilSimulations (impactList com
`location: "Mars"`, `arrivalTime`, `isGlancingBlow`, `isMinorImpact`) e SEP.
- Cache no banco (TTL 30 min): a chave pública DEMO_KEY tem cota baixa (~10 chamadas); use NASA_API_KEY.
- Falhou/limitou: devolve o último cache (stale) ou, sem cache, um SNAPSHOT real rotulado como tal.
  Nunca inventa dado: o que é simulado para a demo vem marcado `simulated: true`.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.models import SpaceWeatherCache

log = logging.getLogger("bip.spaceweather")
BASE = "https://api.nasa.gov/DONKI"
TTL = 30 * 60        # segundos até considerar o cache velho
RETRY = 5 * 60       # não retentar a rede antes disso após uma falha
WINDOW_DAYS = 14
SNAPSHOT = Path(__file__).resolve().parent.parent / "snapshots" / "space_weather.json"
WATCH_HOURS = 72     # impacto previsto dentro desta janela => vigilância (escolha do projeto)


def enabled() -> bool:
    return os.getenv("SPACE_WEATHER", "on").lower() != "off"


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _parse(t: str | None) -> float | None:
    if not t:
        return None
    try:
        return datetime.strptime(t, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        try:
            return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None


def _fetch(kind: str, start: str, end: str):
    key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    r = httpx.get(f"{BASE}/{kind}", params={"startDate": start, "endDate": end}, headers={"X-Api-Key": key}, timeout=10)
    r.raise_for_status()
    return r.json()


def _trim_sim(s: dict) -> dict | None:
    mars = [{"arrival": i["arrivalTime"], "glancing": bool(i.get("isGlancingBlow")), "minor": bool(i.get("isMinorImpact"))}
            for i in (s.get("impactList") or []) if i.get("location") == "Mars" and i.get("arrivalTime")]
    if not mars:
        return None
    c = (s.get("cmeInputs") or [{}])[0]
    return {"id": s.get("simulationID"), "completed": s.get("modelCompletionTime"), "link": s.get("link"),
            "cme": {"id": c.get("CMEID"), "start": c.get("cmeStartTime"), "speed": c.get("speed"), "half_angle": c.get("halfAngle")},
            "mars": mars}


def fetch_live(now: float) -> dict:
    start, end = _iso(now - WINDOW_DAYS * 86400), _iso(now + 86400)
    sims = [t for t in (_trim_sim(s) for s in _fetch("WSAEnlilSimulations", start, end)) if t]
    sep = _fetch("SEP", start, end)
    return {"window": {"start": start, "end": end}, "sims": sims, "sep": sep}


def _snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def load(db: Session, now: float | None = None, force: bool = False) -> tuple[dict, dict]:
    """Devolve (dados reduzidos, meta) usando cache -> rede -> cache velho -> snapshot."""
    now = time.time() if now is None else now
    meta = {"snapshot": False, "stale": False, "fetched_at": None, "error": None}
    row = None
    try:
        row = db.get(SpaceWeatherCache, "donki")
    except Exception as e:
        log.warning("cache indisponível: %s", e)

    if row and now - row.fetched_at < TTL and not force:
        return row.payload, {**meta, "fetched_at": row.fetched_at}

    if enabled() and (force or row is None or now - row.attempted_at > RETRY):
        try:
            data = fetch_live(now)
            if row is None:
                row = SpaceWeatherCache(key="donki", payload=data, fetched_at=now, attempted_at=now)
                db.add(row)
            else:
                row.payload, row.fetched_at, row.attempted_at = data, now, now
            db.commit()
            return data, {**meta, "fetched_at": now}
        except Exception as e:
            db.rollback()
            meta["error"] = type(e).__name__
            log.warning("DONKI falhou: %s", type(e).__name__)
            try:
                if row is not None:
                    row.attempted_at = now
                    db.commit()
            except Exception:
                db.rollback()

    if row:  # cache velho é melhor que nada
        return row.payload, {**meta, "stale": True, "fetched_at": row.fetched_at}
    snap = _snapshot()
    return snap, {**meta, "snapshot": True, "stale": True, "fetched_at": _parse(snap.get("captured_at"))}


def _fmt_hours(h: float) -> str:
    return f"~{h:.0f} h" if h >= 2 else f"~{max(1, round(h * 60))} min"


def normalize(data: dict, meta: dict, now: float, scenario: str | None = None) -> dict:
    upcoming, recent, by_arrival = [], [], {}
    for s in data.get("sims", []):
        for m in s["mars"]:
            t = _parse(m["arrival"])
            if t is None:
                continue
            # várias simulações do modelo apontam para a mesma chegada: fica a mais recente
            prev = by_arrival.get(m["arrival"])
            if prev is None or (s.get("completed") or "") > (prev[1].get("completed") or ""):
                by_arrival[m["arrival"]] = (t, s, m)
    for t, s, m in by_arrival.values():
        ev = {"arrival_time": m["arrival"], "hours_until": round((t - now) / 3600, 1), "glancing_blow": m["glancing"],
              "minor_impact": m["minor"], "simulation_id": s["id"], "link": s["link"], "cme": s["cme"], "simulated": False}
        (upcoming if t >= now else recent).append((t, ev))
    upcoming = [e for _, e in sorted(upcoming, key=lambda x: x[0])]
    recent = [e for _, e in sorted(recent, key=lambda x: -x[0]) if e["hours_until"] > -7 * 24][:10]

    sep = []
    for e in data.get("sep", []):
        t = _parse(e.get("eventTime") or e.get("startTime"))
        sep.append({"id": e.get("sepID") or e.get("activityID"), "time": e.get("eventTime") or e.get("startTime"), "link": e.get("link"),
                    "hours_ago": None if t is None else round((now - t) / 3600, 1)})

    if scenario == "spe":  # demo: evento SIMULADO, sempre rotulado como tal
        upcoming.insert(0, {"arrival_time": datetime.fromtimestamp(now + 3 * 3600, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                            "hours_until": 3.0, "glancing_blow": False, "minor_impact": False, "simulation_id": "DEMO-SIMULATED",
                            "link": None, "cme": {"id": "DEMO", "start": None, "speed": 1200, "half_angle": 45}, "simulated": True})

    level, message = "none", "No CME impact on Mars is forecast in NASA's recent simulations."
    recent_sep = [s for s in sep if s["hours_ago"] is not None and 0 <= s["hours_ago"] <= 24]
    near = [e for e in upcoming if e["hours_until"] <= WATCH_HOURS]
    strong = [e for e in near if not e["minor_impact"] and not e["glancing_blow"]]
    tag = " (SIMULATED for the demo)" if any(e["simulated"] for e in near) else ""
    if recent_sep or strong:
        first = strong[0] if strong else None
        level = "warning"
        message = (f"CME impact forecast on Mars in {_fmt_hours(first['hours_until'])}{tag}" if first else "Solar energetic particle (SEP) event in the last 24 h")
        message += ". Confirm with MCC and consider radiation shelter per the mission protocol."
    elif near:
        level = "watch"
        message = f"Minor/glancing CME impact forecast on Mars in {_fmt_hours(near[0]['hours_until'])}. Monitor the dose."
    elif upcoming:
        level, message = "info", f"An impact is forecast on Mars, but beyond {WATCH_HOURS} h ({_fmt_hours(upcoming[0]['hours_until'])})."

    return {"source": "NASA DONKI (CCMC) — WSA-ENLIL and SEP", "location": "Mars", "now": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "alert": {"level": level, "message": message}, "upcoming_impacts": upcoming[:10], "recent_impacts": recent, "sep_events": sep[:10],
            "window": data.get("window"), **meta}


def get(db: Session, now: float | None = None, scenario: str | None = None, force: bool = False) -> dict:
    now = time.time() if now is None else now
    data, meta = load(db, now, force)
    return normalize(data, meta, now, scenario)
