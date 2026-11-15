"""Engine SQLAlchemy + sessão. Mesmo código roda em SQLite (dev) e Postgres (prod)."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app import config

_url = config.database_url()
if _url in ("sqlite://", "sqlite:///:memory:"):
    engine = create_engine(_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
elif _url.startswith("sqlite"):
    engine = create_engine(_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> bool:
    """Cria as tabelas. Nunca derruba o app: sem banco, os endpoints antigos seguem."""
    from app import models  # noqa: F401  (registra as tabelas)

    try:
        Base.metadata.create_all(engine)
        return True
    except Exception as e:  # pragma: no cover
        print(f"[db] indisponível: {e}")
        return False


def db_ok() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
