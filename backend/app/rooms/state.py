"""Typed room-state models used for persistence and shared room metadata."""

from __future__ import annotations

from time import time

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Difficulty, GamePhase, LanguageCode


class PlayerPromptAssignmentState(BaseModel):
    """Serializable prompt assignment for one player."""

    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    category: str
    item_ids: list[int] = Field(default_factory=list)
    items: list[str]
    alternatives: dict[str, list[str]] = Field(default_factory=dict)


class GuessSubmissionState(BaseModel):
    """Serializable guess submission for one player."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    target_player_id: str
    guesses: list[str]
    submitted_at: int = 0  # ms epoch; used to compute the "speed demon" highlight


class RoomMetadataState(BaseModel):
    """Serializable room metadata stored in Redis."""

    model_config = ConfigDict(extra="forbid")

    categories: list[str] = Field(default_factory=list)
    game_phase: GamePhase = GamePhase.LOBBY
    round_start_time: int | None = None
    guessing_start_time: int | None = None
    drawing_time_limit: int | None = None
    guessing_time_limit: int | None = None
    difficulty: Difficulty = "medium"
    max_rounds: int = 5
    current_round: int = 0
    pad_visibility: bool = True
    ready_players: set[str] = Field(default_factory=set)
    is_private: bool = False
    default_locale: LanguageCode = "en"
    player_locales: dict[str, LanguageCode] = Field(default_factory=dict)
    player_user_ids: dict[str, str] = Field(default_factory=dict)
    custom_category_ids: list[int] | None = None
    player_assignments: dict[str, PlayerPromptAssignmentState] = Field(default_factory=dict)
    guess_targets: dict[str, str] = Field(default_factory=dict)
    guess_submissions: list[GuessSubmissionState] = Field(default_factory=list)
    submitted_players: set[str] = Field(default_factory=set)
    player_scores: dict[str, int] = Field(default_factory=dict)
    # Stable display order: each player keeps the seat assigned on first join,
    # so a reconnect doesn't shuffle them to the end of the roster.
    player_seats: dict[str, int] = Field(default_factory=dict)


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
