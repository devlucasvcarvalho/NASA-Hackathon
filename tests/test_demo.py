from fastapi.testclient import TestClient

from app.main import app


def test_scenario_switch_affects_everything(monkeypatch):
    monkeypatch.delenv("DEMO_TOKEN", raising=False)
    with TestClient(app) as c:
        base_v = c.get("/api/vitals").json()
        base_r = c.get("/api/risk").json()["score"]
        assert base_v["scenario"] is None and c.get("/api/demo").json()["active"] is None

        assert c.post("/api/demo/scenario", json={"scenario": "infection"}).json()["active"] == "infection"
        v = c.get("/api/vitals").json()  # sem ?scenario= : vale o ativo
        assert v["scenario"] == "infection"
        assert v["temperature"] > 37.8 and v["temperature"] > base_v["temperature"] + 1  # campo legado reflete o cenário
        assert v["metrics"]["temperature"]["status"] in ("vigilancia", "alerta")
        assert v["metrics"]["heart_rate"]["status"] == "alerta"  # 93 bpm é normal "em geral", mas anômalo p/ este horário
        assert {"z", "expected"} <= set(v["metrics"]["heart_rate"])
        assert c.get("/api/risk").json()["score"] > base_r + 30
        assert c.get("/api/context").json()["flat"]["demo_scenario"] == "infection"
        d = c.post("/api/diagnose", json={"text": "febre e calafrios"}).json()
        assert d["risk_score"] > base_r + 30

        # ?scenario= explícito vence o ativo
        assert c.get("/api/vitals", params={"scenario": "dehydration"}).json()["scenario"] == "dehydration"

        # desligar volta ao normal
        assert c.post("/api/demo/scenario", json={"scenario": None}).json()["active"] is None
        assert c.get("/api/vitals").json()["scenario"] is None
        assert c.get("/api/risk").json()["score"] <= base_r + 5


def test_invalid_scenario_and_token(monkeypatch):
    with TestClient(app) as c:
        monkeypatch.delenv("DEMO_TOKEN", raising=False)
        assert c.post("/api/demo/scenario", json={"scenario": "zumbi"}).status_code == 422
        monkeypatch.setenv("DEMO_TOKEN", "segredo")
        assert c.post("/api/demo/scenario", json={"scenario": "stress"}).status_code == 401
        ok = c.post("/api/demo/scenario", json={"scenario": "stress"}, headers={"X-Demo-Token": "segredo"})
        assert ok.status_code == 200 and c.get("/api/demo").json()["active"] == "stress"  # leitura continua pública
