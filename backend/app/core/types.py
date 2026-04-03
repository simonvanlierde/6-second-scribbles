"""Shared bounded types for backend domain and API validation."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

type Difficulty = Literal["easy", "medium", "hard"]


class GamePhase(StrEnum):
    """Valid room lifecycle phases for game flow state."""

    LOBBY = "lobby"
    DRAWING = "drawing"
    GUESSING = "guessing"
    SCORING = "scoring"
    COMPLETE = "complete"


type LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,5}$", to_lower=True)]
type PositiveRoundCount = Annotated[int, Field(ge=1)]
type PositiveRoundLengthSeconds = Annotated[int, Field(ge=1)]
