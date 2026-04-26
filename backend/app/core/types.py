"""Shared bounded types for backend domain and API validation."""

from __future__ import annotations

__all__ = [
    "Difficulty",
    "GamePhase",
    "LanguageCode",
    "PositiveRoundCount",
    "PositiveRoundLengthSeconds",
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
type PositiveRoundCount = Annotated[int, Field(ge=1)]
type PositiveRoundLengthSeconds = Annotated[int, Field(ge=1)]
