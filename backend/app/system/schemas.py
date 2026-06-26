"""HTTP schemas for system and diagnostics routes."""

from __future__ import annotations

from pydantic import BaseModel


class ApiStatusResponse(BaseModel):
    """Generic status response for health and stats endpoints."""

    status: str


class AppInfoResponse(ApiStatusResponse):
    """Root endpoint response."""

    service: str
    version: str
    database: str = "ok"
    cache: str = "ok"


class StatsResponse(ApiStatusResponse):
    """Server statistics response."""

    total_rooms: int
    active_rooms: int
    hibernated_rooms: int
    empty_rooms: int
    total_players: int
