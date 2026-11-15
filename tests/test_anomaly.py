import os
import time

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import VitalSample  # noqa: E402
from app.services import anomaly, risk, simulator  # noqa: E402


def test_false_alarm_rate_is_low():
    """No histórico saudável (últimos 3 dias), quase nenhuma amostra deve virar alerta."""
    with TestClient(app):
        with db.SessionLocal() as s:
            now = time.time()
            ts_list = list(s.scalars(select(VitalSample.ts).where(VitalSample.ts > now - 3 * 86400).order_by(VitalSample.ts)))[::4]
            flagged = 0
            for ts in ts_list:
                r = anomaly.evaluate(s, now=ts + 1)
                lvl = {m["status"] for m in r["metrics"].values()} | {r["multivariate"]["level"]}
                if "alerta" in lvl:
                    flagged += 1
            rate = flagged / len(ts_list)
            print(f"false alert rate: {rate:.3%} over {len(ts_list)} samples")
            assert rate < 0.03


def test_scenarios_raise_risk():
    with TestClient(app):
        with db.SessionLocal() as s:
            now = time.time()
            base = risk.compute(s, now)
            assert base["level"] in ("baixo", "moderado")
            for name in simulator.SCENARIOS:
                r = risk.compute(s, now, scenario=name)
                assert r["score"] > base["score"], name
            inf = risk.compute(s, now, scenario="infection")
            assert inf["anomaly"]["multivariate"]["level"] != "normal"
            assert any("Temperatura" in f["name"] for f in inf["factors"])


def test_endpoints():
    with TestClient(app) as c:
        st = c.get("/api/vitals/status").json()
        assert set(st["metrics"]) >= {"heart_rate", "hrv"} and "multivariate" in st
        rk = c.get("/api/risk", params={"scenario": "infection"}).json()
        assert 0 <= rk["score"] <= 100 and rk["factors"] and rk["level"]
