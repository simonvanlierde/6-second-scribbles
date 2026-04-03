"""Application entrypoint and shared app wiring."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError

from app.categories.router import router as categories_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis
from app.rooms.manager import room_manager
from app.rooms.router import router as rooms_router
from app.rooms.ws_router import router as ws_router
from app.system.router import router as system_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown logic."""
    logger.info("Starting Six Second Scribbles API...")
    await init_db()
    logger.info("Database initialized")

    try:
        await get_redis()
        logger.info("Redis connected")
    except (OSError, RedisError) as exc:
        logger.warning("Redis unavailable — room state will not persist across restarts: %s", exc)

    await room_manager.start()
    logger.info("Room manager started")
    yield
    logger.info("Shutting down...")
    await room_manager.stop()
    logger.info("Room manager stopped")
    await close_db()
    logger.info("Database connections closed")
    await close_redis()
    logger.info("Redis connection closed")


app = FastAPI(
    title="Six Second Scribbles API",
    description="Real-time multiplayer drawing game backend",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(categories_router)
app.include_router(rooms_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.server_host, port=settings.server_port)
