"""Shared bounded types for backend domain and API validation."""

from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import Field, StringConstraints

type Difficulty = Literal["easy", "medium", "hard"]
type GamePhase = Literal["lobby", "drawing", "guessing", "scoring", "complete"]

LOBBY_PHASE: Final = "lobby"
GUESSING_PHASE: Final = "guessing"
type LanguageCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,5}$", to_lower=True)]
type PositiveRoundCount = Annotated[int, Field(ge=1)]
type PositiveRoundLengthSeconds = Annotated[int, Field(ge=1)]
