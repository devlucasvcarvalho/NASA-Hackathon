import os

os.environ["DATABASE_URL"] = "sqlite://"  # tem de vir antes de importar o app
os.environ["SPACE_WEATHER"] = "off"       # testes nunca chamam a NASA (usam snapshot ou monkeypatch)

import pytest  # noqa: E402

from app import db  # noqa: E402

# estado do usuário; vitais/sono (histórico simulado) são mantidos entre testes por serem caros de gerar
USER_TABLES = ["routine_log", "mood", "diagnoses", "chat", "stock_moves", "achievements_unlocked", "app_state", "space_weather_cache"]


@pytest.fixture(autouse=True)
def clean_user_state():
    from sqlalchemy import text

    db.init_db()
    with db.engine.begin() as c:
        for t in USER_TABLES:
            c.execute(text(f"DELETE FROM {t}"))
    yield
