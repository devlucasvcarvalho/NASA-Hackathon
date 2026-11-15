"""B.I.P — Biomedical Intelligent Partner · backend FastAPI.

Entrada do app: monta os routers, o frontend estático e inicializa o banco.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config, db
from app.routers import ai_routes, content, health, vitals


@asynccontextmanager
async def lifespan(_: FastAPI):
    if db.init_db():
        try:
            from app.services import history

            with db.SessionLocal() as s:
                history.ensure_history(s)
        except Exception as e:  # pragma: no cover
            print(f"[history] backfill falhou: {e}")
    yield


app = FastAPI(title="B.I.P — Biomedical Intelligent Partner", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

for r in (health.router, vitals.router, content.router, ai_routes.router):
    app.include_router(r)


@app.get("/")
def index():
    return FileResponse(config.STATIC_DIR / "index.html")


@app.get("/manifest.json")
def manifest():
    return JSONResponse({
        "name": "B.I.P — Biomedical Intelligent Partner",
        "short_name": "B.I.P",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0F3E3D",
        "theme_color": "#0F3E3D",
    })


@app.get("/favicon.svg")
def favicon():
    return FileResponse(config.STATIC_DIR / "favicon.svg", media_type="image/svg+xml")
