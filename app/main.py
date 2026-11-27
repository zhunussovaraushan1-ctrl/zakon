"""FastAPI: API ленты и раздача PWA.

uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, demo, pipeline

log = logging.getLogger("zanwatch")
STATIC = config.BASE_DIR / "static"


async def _scheduler() -> None:
    while True:
        await asyncio.sleep(config.COLLECT_INTERVAL_HOURS * 3600)
        try:
            await asyncio.to_thread(pipeline.run)
        except Exception:
            log.exception("Плановый сбор упал")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    with db.session() as conn:
        if config.SEED_DEMO:
            demo.seed(conn)
        else:
            demo.remove(conn)
    if config.ADMIN_TOKEN == "change-me":
        log.warning("ZW_ADMIN_TOKEN не задан — смените токен по умолчанию!")
    task = asyncio.create_task(_scheduler()) if config.COLLECT_INTERVAL_HOURS > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="ZanWatch", version="0.1.0", lifespan=lifespan)


@app.get("/api/updates")
def list_updates(
    sphere: str | None = None,
    audience: str | None = None,
    importance: str | None = Query(None, pattern="^(high|medium|low)$"),
    source: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with db.session() as conn:
        items, total = db.query_updates(conn, sphere, audience, importance, source, q, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/api/updates/{update_id}")
def get_update(update_id: int):
    with db.session() as conn:
        u = db.get_update(conn, update_id)
    if not u:
        raise HTTPException(404, "Карточка не найдена")
    return u


@app.get("/api/meta")
def meta():
    with db.session() as conn:
        run = db.last_run(conn)
    return {
        "spheres": config.SPHERES,
        "audiences": config.AUDIENCES,
        "sources": {k: {"name": v["name"], "kind": v["kind"], "official": v["official"]}
                    for k, v in config.SOURCES.items()},
        "last_collect": run["finished_at"] if run else None,
        "demo": config.SEED_DEMO,
    }


@app.post("/api/collect", status_code=202)
async def collect(x_admin_token: str | None = Header(None)):
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(401, "Неверный X-Admin-Token")
    asyncio.get_running_loop().run_in_executor(None, pipeline.run)
    return {"status": "started"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # SW отдаётся с корня, чтобы его область действия покрывала всё приложение
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
