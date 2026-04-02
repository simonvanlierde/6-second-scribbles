"""Typed room-state models used for persistence and shared room metadata."""

from __future__ import annotations

from time import time

from pydantic import BaseModel, ConfigDict, Field

from app.domain_types import Difficulty, GamePhase, LanguageCode  # noqa: TC001 - used by Pydantic at runtime


class PlayerCardState(BaseModel):
    """Serializable card assignment for one player."""

    model_config = ConfigDict(extra="forbid")

    category: str
    items: list[str]
    alternatives: dict[str, list[str]] = Field(default_factory=dict)
    is_custom: bool = False


class GuessSubmissionState(BaseModel):
    """Serializable guess submission for one player."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    player_id: str = Field(alias="playerId")
    target_player_id: str = Field(alias="targetPlayerId")
    guesses: list[str]


class RoomMetadataState(BaseModel):
    """Serializable room metadata stored in Redis."""

    model_config = ConfigDict(extra="forbid")

    categories: list[str] = Field(default_factory=list)
    game_phase: GamePhase = "lobby"
    round_start_time: int | None = None
    round_length: int | None = None
    difficulty: Difficulty = "medium"
    max_rounds: int = 5
    current_round: int = 0
    pad_visibility: bool = True
    ready_players: set[str] = Field(default_factory=set)
    is_private: bool = False
    language: LanguageCode = "en"
    player_cards: dict[str, PlayerCardState] = Field(default_factory=dict)
    guess_submissions: list[GuessSubmissionState] = Field(default_factory=list)
    submitted_players: set[str] = Field(default_factory=set)
    player_count_for_scoring: int = 0
    player_scores: dict[str, int] = Field(default_factory=dict)


class RoomState(BaseModel):
    """Serializable room snapshot stored in Redis."""

    model_config = ConfigDict(extra="forbid")

    room_id: str
    host_id: str | None = None
    last_host_id: str | None = None
    created_at: float = Field(default_factory=time)
    emptied_at: float | None = None
    is_hibernated: bool = False
    metadata: RoomMetadataState = Field(default_factory=RoomMetadataState)
