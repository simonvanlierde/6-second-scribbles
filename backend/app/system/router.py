"""System and diagnostics routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.rooms.manager import room_manager
from app.system.schemas import AppInfoResponse, StatsResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=AppInfoResponse)
async def health() -> AppInfoResponse:
    """Health check endpoint."""
    return AppInfoResponse(status="ok", service="Six Second Scribbles API", version="2.0.0")


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Get server statistics including room and player counts."""
    stats = room_manager.get_stats()
    return StatsResponse(status="ok", **stats)
