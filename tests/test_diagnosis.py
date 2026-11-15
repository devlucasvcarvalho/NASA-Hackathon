import os

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient  # noqa: E402

from app import ai  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import validate_diagnosis  # noqa: E402

GOOD = {
    "title": "Cefaleia tensional (tension-type headache)",
    "severity": "leve",
    "summary": "Dor de cabeça compatível com tensão, associada a sono curto e cortisol alto.",
    "causes": [{"name": "Tensional", "likelihood": "70", "why": "sono"}, {"name": "Desidratação", "likelihood": 30, "why": "hidratação"}],
    "prescription": [{"item": "Paracetamol 500 mg", "dose": "500 mg", "frequency": "6/6h", "duration": "2 dias", "instructions": "após refeição"}],
    "procedures": ["Hidratar", "Repouso"],
    "monitoring": "Reavaliar em 6 h",
    "red_flags": ["rigidez de nuca"],
    "factors_used": ["sono"],
}


def test_schema_accepts_and_normalizes():
    out = validate_diagnosis(GOOD)
    assert out and out["triage_action"] == "onboard"  # derivado da gravidade
    assert out["causes"][0]["likelihood"] == 70


def test_schema_rejects_bad_or_forbidden():
    assert validate_diagnosis({"title": "x"}) is None
    assert validate_diagnosis("texto") is None
    assert validate_diagnosis({**GOOD, "severity": "gravissimo"}) is None
    assert validate_diagnosis({**GOOD, "procedures": ["Procure um médico imediatamente"]}) is None
    assert validate_diagnosis({**GOOD, "procedures": ["Vá ao hospital"]}) is None
    g = validate_diagnosis({**GOOD, "severity": "grave", "triage_action": "onboard"})
    assert g["triage_action"] == "abort"  # grave sempre aborta


def test_gemini_invalid_falls_back_after_retry(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    calls = []
    monkeypatch.setattr(ai, "_call_gemini", lambda *a, **k: calls.append(1) or '{"severity": "leve"}')  # inválido
    out = ai.diagnose("dor de cabeça", {})
    assert len(calls) == ai.GEMINI_ATTEMPTS and out["source"] == "offline-fallback" and out["severity"]


def test_gemini_valid_is_used(monkeypatch):
    import json

    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setattr(ai, "_call_gemini", lambda *a, **k: json.dumps(GOOD))
    out = ai.diagnose("dor de cabeça", {})
    assert out["source"] == "gemini" and out["title"].startswith("Cefaleia")


def test_endpoints_persist_and_context():
    with TestClient(app) as c:
        ctx = c.get("/api/context", params={"scenario": "infection"}).json()
        assert "risk" in ctx["flat"] and ctx["structured"]["risk"]["score"] > 40
        assert ctx["flat"]["demo_scenario"] == "infection"

        d = c.post("/api/diagnose", json={"text": "febre e calafrios", "context": {"routine_score": "3/10"}, "scenario": "infection"}).json()
        assert d["severity"] and d["source"] == "offline" and d["id"] and d["risk_score"] > 40
        assert c.get("/api/diagnoses").json()["diagnoses"][0]["id"] == d["id"]
        assert c.get(f"/api/diagnoses/{d['id']}").json()["query"] == "febre e calafrios"
        assert c.get("/api/diagnoses/99999").status_code == 404

        c.post("/api/chat", json={"message": "oi bip"})
        msgs = c.get("/api/chat/history").json()["messages"]
        assert [m["role"] for m in msgs[-2:]] == ["user", "bip"]


def test_server_context_overrides_client():
    from app.db import SessionLocal
    from app.services import context

    with TestClient(app):
        with SessionLocal() as s:
            flat = context.build(s)["flat"]
            merged = context.merge_with_client(flat, {"exams": "TEXTO FALSO DO FRONT", "routine_score": "5/9"})
            assert merged["flagged_exams"] == flat["flagged_exams"]
            assert "exams" not in merged  # texto fixo do front é descartado
            assert merged["routine_score"] == "5/9"  # campos que só o cliente conhece entram
