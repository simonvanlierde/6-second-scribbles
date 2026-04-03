"""Shared bounded types for backend domain and API validation."""

from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import Field, StringConstraints

type Difficulty = Literal["easy", "medium", "hard"]
type GamePhase = Literal["lobby", "drawing", "guessing", "scoring", "complete"]

LOBBY_PHASE: Final = "lobby"
DRAWING_PHASE: Final = "drawing"
GUESSING_PHASE: Final = "guessing"
SCORING_PHASE: Final = "scoring"
COMPLETE_PHASE: Final = "complete"
type LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,5}$", to_lower=True)]
type PositiveRoundCount = Annotated[int, Field(ge=1)]
type PositiveRoundLengthSeconds = Annotated[int, Field(ge=1)]
