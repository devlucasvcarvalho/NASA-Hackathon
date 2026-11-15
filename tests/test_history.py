import os

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import SleepNight, VitalSample  # noqa: E402
from app.services import history, simulator  # noqa: E402
from app.services.ranges import status_for  # noqa: E402


def test_simulator_is_deterministic():
    assert simulator.vital_sample(1_800_000_000) == simulator.vital_sample(1_800_000_000)
    assert simulator.sleep_night("2026-11-01") == simulator.sleep_night("2026-11-01")


def test_status_ranges():
    assert status_for("heart_rate", 70) == "normal"
    assert status_for("heart_rate", 105) == "vigilancia"
    assert status_for("heart_rate", 130) == "alerta"
    assert status_for("spo2", 90) == "alerta"
    assert status_for("temperature", 37.6) == "vigilancia"


def test_backfill_and_catchup():
    with TestClient(app):  # dispara o lifespan (backfill)
        with db.SessionLocal() as s:
            n = s.scalar(select(func.count()).select_from(VitalSample))
            assert n >= history.HISTORY_DAYS * 86400 // history.STEP
            assert s.scalar(select(func.count()).select_from(SleepNight)) >= history.HISTORY_DAYS
            last = s.scalar(select(func.max(VitalSample.ts)))
            # "avançar o relógio" 1h: catch-up adiciona 4 amostras, sem duplicar
            added = history.ensure_history(s, now=last + 3600)
            assert added >= 4
            assert history.ensure_history(s, now=last + 3600) == 0


def test_history_endpoints():
    with TestClient(app) as c:
        v = c.get("/api/vitals").json()
        assert {"heart_rate", "sleep_hours"} <= set(v)  # contrato legado
        assert set(v["metrics"]) >= {"heart_rate", "spo2", "temperature"}
        m = v["metrics"]["heart_rate"]
        assert m["status"] in {"normal", "vigilancia", "alerta"} and "delta_text" in m

        h = c.get("/api/vitals/history", params={"metric": "heart_rate", "hours": 24, "points": 48}).json()
        assert 0 < len(h["points"]) <= 48 and h["stats"]["min"] <= h["stats"]["max"]
        assert c.get("/api/vitals/history", params={"metric": "nope"}).status_code == 422

        sl = c.get("/api/sleep", params={"days": 7}).json()
        assert len(sl["nights"]) == 7 and sl["avg_hours"]
