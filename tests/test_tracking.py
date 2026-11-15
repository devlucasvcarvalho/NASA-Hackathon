from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import data
from app.main import app

ALL = [t["id"] for p in data.ROUTINE_TEMPLATE["en"] for t in p["tasks"]]
D0 = date(2026, 10, 1)


def day(n):
    return (D0 + timedelta(days=n)).isoformat()


def complete_all(c, d):
    last = None
    for tid in ALL:
        last = c.post(f"/api/routines/{tid}/complete", params={"day": d}).json()
    return last


def test_routine_toggle_and_score():
    with TestClient(app) as c:
        r = c.post("/api/routines/m1/complete", params={"day": day(0)}).json()
        assert r["done"] and "m1" in r["done_ids"] and r["score"] > 0
        c.post("/api/routines/m1/complete", params={"day": day(0)})  # idempotente
        assert c.get("/api/routines/today", params={"day": day(0)}).json()["done_ids"] == ["m1"]
        r = c.delete("/api/routines/m1/complete", params={"day": day(0)}).json()
        assert r["done_ids"] == [] and r["score"] == 0
        assert c.post("/api/routines/zzz/complete").status_code == 404
        assert c.get("/api/routines/today", params={"day": "2026-13-45"}).status_code == 422
        assert c.get("/api/routines/today", params={"day": "ontem"}).status_code == 422


def test_streak_is_consecutive_and_unlocks():
    with TestClient(app) as c:
        first = complete_all(c, day(0))
        assert "first-day" in {a["id"] for a in first["newly_unlocked"]}
        complete_all(c, day(1))
        third = complete_all(c, day(2))
        assert "streak-3" in {a["id"] for a in third["newly_unlocked"]}

        view = c.get("/api/achievements", params={"today": day(2)}).json()
        unlocked = {a["id"] for a in view["achievements"] if a["unlocked"]}
        assert {"first-day", "streak-3"} <= unlocked and "mornings-5" not in unlocked
        m = view["metrics"]
        assert (m["streak"], m["perfect_days"], m["hydration_logs"], m["nights_full"]) == (3, 3, 9, 3)

        # pular um dia quebra o streak; o dia corrente incompleto não quebra
        complete_all(c, day(4))
        streak = lambda today: c.get("/api/routines/history", params={"days": 7, "today": day(today)}).json()["metrics"]["streak"]
        assert streak(4) == 1
        assert streak(5) == 1  # dia 5 ainda vazio: conta até o dia 4
        assert streak(6) == 0


def test_mood_feeds_risk_and_context():
    with TestClient(app) as c:
        assert c.post("/api/mood", json={"q1": 4, "q2": 0}).status_code == 422
        r = c.post("/api/mood", json={"q1": 2, "q2": 2}).json()
        assert r["score"] == 4 and r["positive_screen"]
        assert c.get("/api/mood").json()["latest"]["score"] == 4
        assert any(f["name"].startswith("Mood") for f in c.get("/api/risk").json()["factors"])
        assert "PHQ-2 4/6" in c.get("/api/context").json()["flat"]["mood"]


def test_stock_consume():
    with TestClient(app) as c:
        items = {i["name"]: i for i in c.get("/api/stock").json()["items"]}
        assert all("initial" in i and "low" in i for i in items.values())
        start = items["Paracetamol 500 mg"]["qty"]
        r = c.post("/api/stock/consume", json={"item": "paracetamol", "qty": 4, "reason": "febre"}).json()
        assert r["left"] == start - 4
        after = {i["name"]: i for i in c.get("/api/stock").json()["items"]}
        assert after["Paracetamol 500 mg"]["qty"] == start - 4

        assert c.post("/api/stock/consume", json={"item": "paracetamol", "qty": 5000}).status_code == 422  # acima do limite
        assert c.post("/api/stock/consume", json={"item": "paracetamol", "qty": 1000}).status_code == 409  # sem estoque
        assert c.post("/api/stock/consume", json={"item": "oxigênio", "qty": 1}).status_code == 400  # sem controle de qty
        assert c.post("/api/stock/consume", json={"item": "xyz", "qty": 1}).status_code == 404
        assert c.post("/api/stock/consume", json={"item": "azitro", "qty": 1}).status_code == 200
        assert c.get("/api/stock/moves").json()["moves"][0]["item"].startswith("Azithromycin")


def test_diagnosis_unlocks_achievement_once():
    with TestClient(app) as c:
        d = c.post("/api/diagnose", json={"text": "dor de cabeça forte"}).json()
        assert "first-dx" in {a["id"] for a in d["newly_unlocked"]}
        again = c.post("/api/diagnose", json={"text": "dor de cabeça forte"}).json()
        assert again["newly_unlocked"] == []  # só notifica uma vez


def test_low_adherence_raises_risk():
    with TestClient(app) as c:
        from datetime import datetime, timedelta, timezone

        base = c.get("/api/risk").json()["score"]
        y = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        c.post("/api/routines/m1/complete", params={"day": y})  # ontem: 1 tarefa só
        rk = c.get("/api/risk").json()
        assert any(f["name"] == "Low routine adherence" for f in rk["factors"]) and rk["score"] > base
