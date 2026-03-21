from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.v1.endpoints.cameras import stream_router
from app.api.v1.router import api_router
from app.cache.redis_client import redis_client
from app.core.config import get_settings
from app.core.exceptions import SIVException, error_response
from app.core.logging import get_logger, setup_logging
from app.core.security import get_password_hash
from app.db.crud import alert_crud, camera_crud, settings_crud, user_crud
from app.db.database import AsyncSessionLocal, engine, init_db
from app.db.models import UserRole
from app.vision.camera_manager import camera_manager
from app.vision.frame_processor import frame_processor
from app.websocket.manager import websocket_manager


settings = get_settings()
setup_logging(settings.DEBUG)
logger = get_logger("main")


class RateLimitMiddleware:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        path = request.url.path
        ip = request.client.host if request.client else "unknown"
        limit = 10 if path.startswith("/stream") else 100
        key = f"rate:{ip}:{path.startswith('/stream')}:{int(time.time() // 60)}"
        try:
            count = await redis_client.incr_with_expiry(key, 70)
        except Exception:
            count = 1
        if count > limit:
            response = JSONResponse(status_code=429, content=error_response("rate_limited", "Too many requests.", {"limit": limit}))
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("startup_begin")
    startup_tasks_enabled = not settings.SKIP_STARTUP_TASKS
    if startup_tasks_enabled:
        await init_db()
        async with AsyncSessionLocal() as db:
            await _ensure_bootstrap_data(db)
            await _ensure_camera_rows(db)
        try:
            await redis_client.connect()
        except Exception as exc:
            logger.warning("redis_unavailable", error=str(exc))
        await camera_manager.initialize()
        await frame_processor.start()
        await websocket_manager.start(stats_provider=_system_stats)
    else:
        logger.warning("startup_tasks_skipped")
    yield
    if startup_tasks_enabled:
        await websocket_manager.stop()
        await frame_processor.stop()
        await camera_manager.shutdown()
    await redis_client.disconnect()
    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("request_failed", path=request.url.path, method=request.method, request_id=request_id, error=str(exc))
        raise
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )
    return response


app.include_router(api_router, prefix="/api/v1")
app.include_router(stream_router)


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket, token: str, client_id: str | None = None) -> None:
    actual_client_id = client_id or str(uuid4())
    await websocket_manager.connect(websocket, actual_client_id, token)
    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("action") == "subscribe":
                await websocket_manager.subscribe(actual_client_id, set(payload.get("types", [])))
    except WebSocketDisconnect:
        await websocket_manager.disconnect(actual_client_id)


@app.get("/health")
async def health() -> dict:
    redis_status = "ok"
    try:
        await asyncio.wait_for(redis_client.connect(), timeout=1.0)
    except Exception:
        redis_status = "degraded"
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "db": "ok",
        "redis": redis_status,
        "cameras": {camera_id: stats.status for camera_id, stats in camera_manager.stats.items()},
    }


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    stats = await _system_stats()
    lines = [
        f'siv_frames_total {stats.get("frame_count", 0)}',
        f'siv_active_alerts {stats.get("active_alerts", 0)}',
        f'siv_cameras_online {stats.get("cameras_online", 0)}',
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")


@app.exception_handler(SIVException)
async def siv_exception_handler(_: Request, exc: SIVException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message, exc.details))


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else error_response("http_error", str(exc.detail))
    if "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content=error_response("http_error", str(detail)))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content=error_response("validation_error", "Request validation failed.", {"errors": exc.errors()}))


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(status_code=500, content=error_response("internal_server_error", "Unexpected server error."))


async def _ensure_bootstrap_data(db) -> None:
    admin = await user_crud.get_by_username(db, "admin")
    if not admin:
        await user_crud.create(
            db,
            obj_in={
                "username": "admin",
                "email": "admin@siv.example.com",
                "hashed_password": get_password_hash("admin123"),
                "role": UserRole.ADMIN,
                "is_active": True,
            },
        )
    if not await settings_crud.get(db, "demo_mode"):
        await settings_crud.create(db, obj_in={"key": "demo_mode", "value": True, "description": "Enable demo endpoints.", "updated_by": "system"})


async def _ensure_camera_rows(db) -> None:
    for camera in settings.configured_cameras:
        existing = await camera_crud.get(db, camera["id"])
        if existing:
            continue
        await camera_crud.create(
            db,
            obj_in={
                "id": camera["id"],
                "name": camera["name"],
                "zone": camera["zone"],
                "stream_url": camera["url"],
                "status": "offline",
                "resolution_width": 1280,
                "resolution_height": 720,
                "fps_processing": settings.CAMERA_PROCESSING_FPS,
                "metadata_json": {"source": camera["url"]},
            },
        )


async def _system_stats() -> dict:
    async with AsyncSessionLocal() as db:
        active_alerts = len(await alert_crud.get_active(db))
    return {
        "frame_count": sum(stats.frames_captured for stats in camera_manager.stats.values()),
        "cameras_online": sum(1 for stats in camera_manager.stats.values() if stats.status == "online"),
        "active_alerts": active_alerts,
        "camera_health": {camera_id: stats.status for camera_id, stats in camera_manager.stats.items()},
    }
