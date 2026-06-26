"""HTTP schemas for the rooms domain."""

from __future__ import annotations

from typing import Literal  # noqa: TC003 - Pydantic needs runtime Literal for model_rebuild

from pydantic import BaseModel

from app.core.types import GamePhase


class RandomRoomResponse(BaseModel):
    """Response for finding a random joinable room."""

    room_code: str
    player_count: int
    max_players: int


class RoomStatusResponse(BaseModel):
    """Response for room status checks."""

    exists: bool
    players: int | None = None
    game_phase: GamePhase | None = None


class CreateRoomResponse(BaseModel):
    """Response for newly created room."""

    room_code: str


class QuickPlayResponse(BaseModel):
    """Response for quick-play: a joinable room, existing or freshly created."""

    room_code: str
    kind: Literal["existing", "created"]
