from fastapi.testclient import TestClient

from app.main import app
from app.services.ranges import RANGES, REFERENCES


def test_every_range_declares_an_honest_source():
    for m, r in RANGES.items():
        src = r["source"]
        assert src["kind"] in ("space_program", "placeholder"), m
        assert all(ref in REFERENCES for ref in src["refs"]), m  # nenhuma referência inventada
        if src["kind"] == "space_program":
            assert src["refs"], f"{m} diz ter fonte espacial mas não cita nenhuma"
        else:
            assert "placeholder" in src["note"] or "App" in src["note"] or "app value" in src["note"] or "No space-agency" in src["note"], m


def test_references_are_space_agencies_only():
    for key, ref in REFERENCES.items():
        assert any(d in ref["url"] for d in ("nasa.gov", "ntrs.nasa.gov", "elib.dlr.de", "esa.int")), key


def test_ranges_endpoint_and_nasa_radiation_limits():
    with TestClient(app) as c:
        d = c.get("/api/ranges").json()
        assert d["radiation_limits_msv"] == {"career": 600, "solar_particle_event": 250}
        assert d["ranges"]["radiation_rate"]["source"]["kind"] == "space_program"
        assert d["ranges"]["heart_rate"]["source"]["kind"] == "placeholder"
        assert "180" not in c.get("/api/context").json()["flat"]["radiation_cumulative"]


def test_exercise_aware_heart_rate_status():
    from app.services.ranges import status_for

    assert status_for("heart_rate", 125) == "alerta"                      # em repouso: acima do limite
    assert status_for("heart_rate", 125, exercising=True) == "normal"     # no exercício programado é esperado
    assert status_for("heart_rate", 170, exercising=True) == "alerta"     # acima do pico relatado pela NASA (~163)
    assert status_for("spo2", 90, exercising=True) == "alerta"            # outras métricas não são afrouxadas


def test_multivariate_thresholds_are_calibrated_and_exposed():
    from app import db
    from app.services import anomaly

    with TestClient(app):
        with db.SessionLocal() as s:
            mv = anomaly.evaluate(s)["multivariate"]
            assert mv["watch_at"] >= anomaly.D2_WATCH and mv["alert_at"] >= anomaly.D2_ALERT and mv["alert_at"] > mv["watch_at"]
