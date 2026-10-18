"""Typed room-state models used for persistence and shared room metadata."""

from __future__ import annotations

from time import time
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Difficulty, GamePhase, LanguageCode

if TYPE_CHECKING:
    from typing import ClassVar


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
    """Serializable room metadata stored in Redis.

    The fields stay flat, under their original names, because rooms saved by one
    deploy must load in the next one and in a rollback. Every field belongs to
    exactly one of the groups below, which says which writer resets it.
    """

    model_config = ConfigDict(extra="forbid")

    # Per-player bindings kept for as long as the player holds a seat.
    SEAT_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"player_locales", "player_user_ids", "player_rejoin_keys", "player_seats"},
    )
    # Cleared at the start of every round.
    ROUND_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "round_start_time",
            "guessing_start_time",
            "ready_players",
            "player_assignments",
            "guess_targets",
            "guess_submissions",
            "submitted_players",
        },
    )
    # Cleared when a new game starts or the room returns to the lobby.
    GAME_FIELDS: ClassVar[frozenset[str]] = frozenset({"game_phase", "current_round", "player_scores"})
    # Host-chosen options; they survive across games.
    SETTINGS_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "drawing_time_limit",
            "guessing_time_limit",
            "difficulty",
            "max_rounds",
            "pad_visibility",
            "is_private",
            "default_locale",
            "custom_category_ids",
        },
    )

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
    # sha256 of each player's rejoin key, set on first join and checked on every later one.
    player_rejoin_keys: dict[str, str] = Field(default_factory=dict)
    custom_category_ids: list[int] | None = None
    player_assignments: dict[str, PlayerPromptAssignmentState] = Field(default_factory=dict)
    guess_targets: dict[str, str] = Field(default_factory=dict)
    guess_submissions: list[GuessSubmissionState] = Field(default_factory=list)
    submitted_players: set[str] = Field(default_factory=set)
    player_scores: dict[str, int] = Field(default_factory=dict)
    # Stable display order: each player keeps the seat assigned on first join,
    # so a reconnect doesn't shuffle them to the end of the roster.
    player_seats: dict[str, int] = Field(default_factory=dict)

    def forget_player(self, player_id: str, *, forget_identity: bool) -> None:
        """Drop a player from every seat and round field.

        The identity binding (account and rejoin key) is kept unless
        `forget_identity` is set, so nobody can claim the player_id while its
        owner reconnects. Scores are kept so a player who left still shows up in
        the results. Guess submissions stay too: they are a record of the round
        and still credit the player whose drawing was guessed.
        """
        self.player_locales.pop(player_id, None)
        self.player_seats.pop(player_id, None)
        if forget_identity:
            self.player_user_ids.pop(player_id, None)
            self.player_rejoin_keys.pop(player_id, None)
        # Dropping the assignment matters most: the rejoin gate uses it to
        # recognise round participants, so a kicked player could otherwise
        # rejoin the active round.
        self.player_assignments.pop(player_id, None)
        self.guess_targets.pop(player_id, None)
        self.submitted_players.discard(player_id)
        self.ready_players.discard(player_id)


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
