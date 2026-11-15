import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.services import spaceweather


def _t(offset_h):
    return (datetime.now(timezone.utc) + timedelta(hours=offset_h)).strftime("%Y-%m-%dT%H:%MZ")


def _sim(sid, hours, glancing=False, minor=False):
    return {"id": sid, "completed": _t(-5), "link": "https://ccmc.gsfc.nasa.gov/DONKI/view/WSA-ENLIL/1/-1",
            "cme": {"id": "c", "start": _t(-30), "speed": 900.0, "half_angle": 40.0},
            "mars": [{"arrival": _t(hours), "glancing": glancing, "minor": minor}]}


def _live(sims, sep=None):
    return lambda now: {"window": {"start": "x", "end": "y"}, "sims": sims, "sep": sep or []}


def test_snapshot_when_disabled_is_real_data_and_labeled():
    with TestClient(app) as c:
        d = c.get("/api/space-weather").json()
        assert d["snapshot"] is True and d["stale"] is True and "NASA DONKI" in d["source"]
        assert d["alert"]["level"] in ("none", "info")  # snapshot é de outubro: nada iminente
        assert all(e["hours_until"] < 0 for e in d["recent_impacts"])


def test_alert_levels(monkeypatch):
    monkeypatch.setattr(spaceweather, "enabled", lambda: True)
    with TestClient(app):
        with db.SessionLocal() as s:
            cases = [
                ([], "none"),
                ([_sim("a", 30, minor=True)], "watch"),
                ([_sim("b", 20)], "warning"),
                ([_sim("c", 200)], "info"),
                ([_sim("d", 10, glancing=True)], "watch"),
            ]
            for sims, level in cases:
                monkeypatch.setattr(spaceweather, "fetch_live", _live(sims))
                assert spaceweather.get(s, force=True)["alert"]["level"] == level, (sims, level)
            monkeypatch.setattr(spaceweather, "fetch_live", _live([], [{"sepID": "x", "eventTime": _t(-2)}]))
            assert spaceweather.get(s, force=True)["alert"]["level"] == "warning"  # SEP nas últimas 24 h


def test_cache_ttl_and_stale_fallback(monkeypatch):
    monkeypatch.setattr(spaceweather, "enabled", lambda: True)
    calls = []

    def ok(now):
        calls.append(1)
        return {"window": {}, "sims": [_sim("a", 20)], "sep": []}

    with TestClient(app):
        with db.SessionLocal() as s:
            monkeypatch.setattr(spaceweather, "fetch_live", ok)
            now = time.time()
            assert spaceweather.get(s, now)["stale"] is False
            spaceweather.get(s, now + 60)
            assert len(calls) == 1  # TTL: a segunda chamada vem do cache

            def boom(now):
                raise RuntimeError("429")

            monkeypatch.setattr(spaceweather, "fetch_live", boom)
            r = spaceweather.get(s, now + spaceweather.TTL + 10)  # cache vencido + rede falhando
            assert r["stale"] is True and r["snapshot"] is False and r["error"] == "RuntimeError"
            assert r["upcoming_impacts"] or r["recent_impacts"]  # serviu o cache velho, não o snapshot


def test_spe_scenario_is_simulated_labeled_and_feeds_risk_and_context():
    with TestClient(app) as c:
        base = c.get("/api/risk").json()["score"]
        d = c.get("/api/space-weather", params={"scenario": "spe"}).json()
        assert d["upcoming_impacts"][0]["simulated"] is True
        assert d["alert"]["level"] == "warning" and "SIMULATED" in d["alert"]["message"]
        rk = c.get("/api/risk", params={"scenario": "spe"}).json()
        assert any(f["name"].startswith("Space weather") for f in rk["factors"]) and rk["score"] > base
        assert "space_weather" in c.get("/api/context", params={"scenario": "spe"}).json()["flat"]


def test_duplicate_arrivals_from_several_simulations_are_merged():
    a = _sim("old", 20)
    b = {**_sim("new", 20), "completed": _t(-1)}
    b["mars"] = a["mars"]  # mesma chegada, simulação mais recente
    d = spaceweather.normalize({"sims": [a, b], "sep": []}, {"snapshot": False, "stale": False, "fetched_at": None, "error": None}, time.time())
    assert len(d["upcoming_impacts"]) == 1 and d["upcoming_impacts"][0]["simulation_id"] == "new"


def test_refresh_requires_token(monkeypatch):
    monkeypatch.setenv("DEMO_TOKEN", "t")
    with TestClient(app) as c:
        assert c.get("/api/space-weather", params={"refresh": True}).status_code == 401
