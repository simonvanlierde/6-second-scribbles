"""Typed room-state models used for persistence and shared room metadata."""

from __future__ import annotations

from time import time
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Difficulty, GamePhase, LanguageCode

if TYPE_CHECKING:
    from collections.abc import Iterable
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
        {"player_locales", "player_user_ids", "player_rejoin_keys", "player_seats", "player_departed_at"},
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
    # Unused; stays until 0.4 because extra="forbid" would reject rooms saved in Redis with it.
    custom_category_ids: list[int] | None = None
    player_assignments: dict[str, PlayerPromptAssignmentState] = Field(default_factory=dict)
    guess_targets: dict[str, str] = Field(default_factory=dict)
    guess_submissions: list[GuessSubmissionState] = Field(default_factory=list)
    submitted_players: set[str] = Field(default_factory=set)
    player_scores: dict[str, int] = Field(default_factory=dict)
    # Stable display order: each player keeps the seat assigned on first join,
    # so a reconnect doesn't shuffle them to the end of the roster.
    player_seats: dict[str, int] = Field(default_factory=dict)
    # When each departed player who still holds a binding left (unix seconds).
    # Rooms saved before this field load with none and get stamped on the next trim.
    # Left out of the JSON while empty, so such a room still loads in the release before.
    player_departed_at: dict[str, float] = Field(default_factory=dict, exclude_if=lambda v: not v)

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
            self._drop_identity(player_id)
        # Dropping the assignment matters most: the rejoin gate uses it to
        # recognise round participants, so a kicked player could otherwise
        # rejoin the active round.
        self.player_assignments.pop(player_id, None)
        self.guess_targets.pop(player_id, None)
        self.submitted_players.discard(player_id)
        self.ready_players.discard(player_id)

    def absent_identities(self, present: set[str]) -> list[str]:
        """Return the players not in `present` who still hold an identity binding."""
        return [pid for pid in {**self.player_rejoin_keys, **self.player_user_ids} if pid not in present]

    def trim_absent_identities(self, present: set[str], *, keep: int, now: float, grace: float) -> None:
        """Keep the identity bindings of at most `keep` departed players, dropping the earliest departures.

        A binding younger than `grace` seconds is never dropped, so a burst of
        throwaway joins cannot free the seat of a player who is refreshing. The
        caller bounds the total by refusing new players instead.
        """
        absent = self.absent_identities(present)
        self.player_departed_at = {pid: self.player_departed_at.get(pid, now) for pid in absent}
        expired = sorted(
            (pid for pid in absent if now - self.player_departed_at[pid] >= grace),
            key=self.player_departed_at.__getitem__,
        )
        for pid in expired[: max(0, len(absent) - keep)]:
            self._drop_identity(pid)

    def _drop_identity(self, player_id: str) -> None:
        self.player_user_ids.pop(player_id, None)
        self.player_rejoin_keys.pop(player_id, None)
        self.player_departed_at.pop(player_id, None)

    def reset_round(self, *, cards: dict[str, PlayerPromptAssignmentState] | None = None) -> None:
        """Clear every round field; `cards` become the new round's prompts."""
        self.round_start_time = None
        self.guessing_start_time = None
        self.ready_players = set()
        self.player_assignments = cards or {}
        self.guess_targets = {}
        self.guess_submissions = []
        self.submitted_players = set()

    def reset_game(self, player_ids: Iterable[str]) -> None:
        """Return to the lobby with no round and a zero score for each given player.

        Scores from an earlier game are dropped, including those of players who
        have left. Anyone who joins later gets a score when a round is scored.
        """
        self.reset_round()
        self.game_phase = GamePhase.LOBBY
        self.current_round = 0
        self.player_scores = dict.fromkeys(player_ids, 0)

    def seat_player(
        self,
        player_id: str,
        *,
        locale: LanguageCode,
        user_id: str | None,
        rejoin_key_hash: str | None,
    ) -> None:
        """Record a join: seat, locale, account, and the rejoin key on first use."""
        # Reconnects keep their original seat, so the roster order holds for everyone.
        if player_id not in self.player_seats:
            self.player_seats[player_id] = (max(self.player_seats.values()) + 1) if self.player_seats else 0
        self.player_locales[player_id] = locale
        self.player_departed_at.pop(player_id, None)
        if rejoin_key_hash is not None:
            self.player_rejoin_keys.setdefault(player_id, rejoin_key_hash)
        if user_id is not None:
            self.player_user_ids[player_id] = user_id
        else:
            self.player_user_ids.pop(player_id, None)

    def mark_ready(self, player_id: str) -> None:
        """Record that a player is done drawing."""
        self.ready_players.add(player_id)

    def start_guessing(self, guess_targets: dict[str, str], *, started_at: int) -> None:
        """Enter the guessing phase with each guesser's target drawing."""
        self.guessing_start_time = started_at
        self.game_phase = GamePhase.GUESSING
        self.guess_targets = guess_targets
        self.ready_players = set()

    def record_guess(self, submission: GuessSubmissionState) -> None:
        """Store a player's guesses; the caller checks for duplicates and the target."""
        self.guess_submissions.append(submission)
        self.submitted_players.add(submission.player_id)

    def add_round_points(self, round_points: dict[str, int]) -> None:
        """Add one round's points to each player's running score."""
        for player_id, points in round_points.items():
            self.player_scores[player_id] = self.player_scores.get(player_id, 0) + points


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
