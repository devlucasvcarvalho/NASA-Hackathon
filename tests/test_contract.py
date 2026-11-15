"""Contrato dos endpoints que o front já consome (não pode quebrar)."""

import os

os.environ["DATABASE_URL"] = "sqlite://"  # em memória, isolado

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

VITAL_KEYS = {"heart_rate", "spo2", "hydration", "radiation_dose_rate", "radiation_cumulative",
              "bp_sys", "bp_dia", "temperature", "sleep_hours", "met_seconds", "crew", "mission", "ai_ready"}


def test_endpoints():
    with TestClient(app) as c:
        assert c.get("/").status_code == 200
        h = c.get("/api/health").json()
        assert h["status"] == "ok" and h["db_ok"] is True
        assert VITAL_KEYS <= set(c.get("/api/vitals").json())
        assert c.get("/api/routines").json()["periods"]
        assert c.get("/api/achievements").json()["achievements"]
        assert c.get("/api/stock").json()["items"]
        exams = c.get("/api/exams").json()["exams"]
        assert exams and c.get(f"/api/exams/{exams[0]['id']}").status_code == 200
        assert c.get("/api/exams/nope").status_code == 404
        assert "reply" in c.post("/api/chat", json={"message": "oi"}).json()
        d = c.post("/api/diagnose", json={"text": "headache and fever"}).json()
        assert d["severity"] and d["query"]
