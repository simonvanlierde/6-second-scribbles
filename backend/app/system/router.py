"""System and diagnostics routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.core import redis as redis_module
from app.core.database import get_session_maker
from app.rooms.manager import room_manager
from app.system.schemas import AppInfoResponse, StatsResponse

router = APIRouter(tags=["system"])

logger = logging.getLogger(__name__)

OK_STATUS = "ok"


@router.get("/health", response_model=AppInfoResponse)
async def health() -> AppInfoResponse:
    """Health check endpoint including Redis and database connectivity."""
    db_status = "ok"
    cache_status = "ok"

    try:
        session_maker = get_session_maker()
        async with session_maker() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database connectivity failed")
        db_status = "error"

    try:
        redis_client = await redis_module.get_redis()
        ping_result = redis_client.ping()
        if not isinstance(ping_result, bool):
            await ping_result
    except Exception:
        logger.exception("Health check: Redis connectivity failed")
        cache_status = "error"

    all_ok = db_status == OK_STATUS and cache_status == OK_STATUS
    return AppInfoResponse(
        status="ok" if all_ok else "degraded",
        service="Six Second Scribbles API",
        version="2.0.0",
        database=db_status,
        cache=cache_status,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Get server statistics including room and player counts."""
    stats = room_manager.get_stats()
    return StatsResponse(
        status="ok",
        total_rooms=stats.total_rooms,
        active_rooms=stats.active_rooms,
        hibernated_rooms=stats.hibernated_rooms,
        empty_rooms=stats.empty_rooms,
        total_players=stats.total_players,
    )
