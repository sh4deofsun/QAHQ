import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, auth, results, tasks, workers, ws
from .core.config import settings
from .db import models
from .db.seed import seed
from .db.session import SessionLocal, engine
from .mcp.server import mcp
from .services.dispatcher import worker_state
from .services.hub import hub
from .services.registry import registry

log = logging.getLogger(__name__)


def setup_logging() -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(settings.log_dir / "qahq.log", maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


async def heartbeat_checker() -> None:
    """Mark workers offline when their heartbeat goes stale, close zombie sockets."""
    while True:
        await asyncio.sleep(settings.heartbeat_check_interval_seconds)
        try:
            cutoff = datetime.utcnow() - timedelta(seconds=settings.heartbeat_timeout_seconds)
            with SessionLocal() as db:
                stale = (
                    db.query(models.Worker)
                    .filter(models.Worker.status == "online", models.Worker.last_heartbeat < cutoff)
                    .all()
                )
                for worker in stale:
                    log.warning("Worker %s heartbeat stale, marking offline", worker.client_id)
                    zombie = registry.connections.get(worker.client_id)
                    if zombie:
                        await zombie.close(code=4408)
                        registry.remove(worker.client_id)
                    worker.status = "offline"
                    db.commit()
                    await hub.broadcast(
                        {
                            "event": "worker_status",
                            "worker": {
                                "id": worker.id,
                                "client_id": worker.client_id,
                                "status": worker_state(db, worker),
                                "capabilities": worker.capabilities or [],
                            },
                        }
                    )
        except Exception as e:
            log.error("Heartbeat checker error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    models.Base.metadata.create_all(bind=engine)  # dev convenience; Alembic is canonical in prod
    with SessionLocal() as db:
        seed(db)
    checker = asyncio.create_task(heartbeat_checker())
    async with mcp.session_manager.run():
        yield
    checker.cancel()


app = FastAPI(
    title="QAHQ",
    description="Quality Assurance Headquarters",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def process_time_and_mcp_guard(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        if not settings.mcp_api_key:
            return JSONResponse(status_code=404, content={"detail": "MCP is not enabled"})
        if request.headers.get("x-api-key") != settings.mcp_api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.perf_counter() - start)
    response.headers["Signature"] = "SQAA-T64572-BY"
    return response


app.include_router(auth.router)
app.include_router(workers.router)
app.include_router(tasks.router)
app.include_router(results.router)
app.include_router(admin.router)
app.include_router(ws.router)
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}
