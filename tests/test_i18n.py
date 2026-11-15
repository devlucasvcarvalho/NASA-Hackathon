from fastapi.testclient import TestClient

from app.main import app
from app.schemas import validate_diagnosis


def test_content_follows_lang_but_logic_is_language_independent():
    with TestClient(app) as c:
        en = c.get("/api/routines", params={"lang": "en"}).json()
        pt = c.get("/api/routines", params={"lang": "pt"}).json()
        ids = lambda d: [t["id"] for p in d["periods"] for t in p["tasks"]]
        assert ids(en) == ids(pt) and en["periods"][0]["label"] != pt["periods"][0]["label"]
        assert c.get("/api/routines", params={"lang": "xx"}).json()["lang"] == "en"  # idioma inválido cai no padrão

        stock = {l: c.get("/api/stock", params={"lang": l}).json()["items"] for l in ("pt", "en", "es")}
        assert [i["qty"] for i in stock["pt"]] == [i["qty"] for i in stock["en"]] == [i["qty"] for i in stock["es"]]

        # consumir pelo nome em PT reflete no estoque em EN (movimento guardado sob o nome canônico)
        pt_name = next(i["name"] for i, e in zip(stock["pt"], stock["en"]) if "fever" in e["for"].lower() and i["qty"])
        before = next(i for i in c.get("/api/stock", params={"lang": "en"}).json()["items"] if "fever" in i["for"].lower())
        r = c.post("/api/stock/consume", params={"lang": "pt"}, json={"item": pt_name, "qty": 1})
        assert r.status_code in (200, 422), r.text  # 422 se o nome casar com mais de um item
        if r.status_code == 200:
            after = {i["for"]: i for i in c.get("/api/stock", params={"lang": "en"}).json()["items"]}
            assert after[before["for"]]["qty"] == before["qty"] - 1

        a_en = c.get("/api/achievements", params={"lang": "en"}).json()["achievements"]
        a_pt = c.get("/api/achievements", params={"lang": "pt"}).json()["achievements"]
        assert [a["id"] for a in a_en] == [a["id"] for a in a_pt] and a_en[0]["title"] != a_pt[0]["title"]


def test_severity_is_always_in_the_classes_the_ui_understands():
    """O front só entende leve/moderado/grave; o conteúdo em EN/ES não pode vazar 'severe/mild'."""
    with TestClient(app) as c:
        for lang in ("pt", "en", "es"):
            emergency = {"pt": "dor no peito", "en": "chest pain", "es": "dolor en el pecho"}[lang]
            for text in (emergency, "headache", "nausea", "xyz"):
                d = c.post("/api/diagnose", json={"text": text, "lang": lang}).json()
                assert d["severity"] in ("leve", "moderado", "grave"), (lang, text, d["severity"])
                assert validate_diagnosis(d) is not None
            assert c.post("/api/diagnose", json={"text": emergency, "lang": lang}).json()["severity"] == "grave"


def test_fever_syndrome_in_every_language():
    with TestClient(app) as c:
        for lang, text in (("pt", "febre e calafrios"), ("en", "fever and chills"), ("es", "fiebre y escalofríos")):
            d = c.post("/api/diagnose", json={"text": text, "lang": lang}).json()
            assert d["triage_action"] == "telemedicine" and d["source"] == "offline", (lang, d["title"])


def test_static_assets_are_not_cached():
    with TestClient(app) as c:
        assert c.get("/").headers["cache-control"] == "no-cache"
        assert c.get("/static/js/app.js").headers["cache-control"] == "no-cache"
        assert "cache-control" not in c.get("/api/health").headers or c.get("/api/health").headers["cache-control"] != "no-cache"
