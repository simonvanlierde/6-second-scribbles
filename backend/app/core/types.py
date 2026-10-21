"""Shared bounded types for backend domain and API validation."""

from __future__ import annotations

__all__ = [
    "Difficulty",
    "GamePhase",
    "LanguageCode",
    "PositiveRoundLengthSeconds",
    "RoundCount",
    "RoundLengthSeconds",
]

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

type Difficulty = Literal["easy", "medium", "hard"]


class GamePhase(StrEnum):
    """Valid room lifecycle phases for game flow state."""

    LOBBY = "lobby"
    DRAWING = "drawing"
    GUESSING = "guessing"
    ROUND_RESULTS = "round_results"
    FINAL_RESULTS = "final_results"


type LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$")]
# Same bounds as the lobby's settings controls (frontend/src/config/gameConfig.ts).
type RoundCount = Annotated[int, Field(ge=1, le=10)]
type RoundLengthSeconds = Annotated[int, Field(ge=15, le=180)]
# Looser bound for room snapshots: rooms saved before the bounds above may hold other values.
type PositiveRoundLengthSeconds = Annotated[int, Field(ge=1)]
