"""WebSocket protocol models and serialization helpers."""

# ruff: noqa: D101

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.core.types import (  # noqa: TC001 - used by Pydantic at runtime
    Difficulty,
    GamePhase,
    LanguageCode,
    PositiveRoundCount,
    PositiveRoundLengthSeconds,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

type Payload = dict[str, object]
type WebSocketMessage = BaseModel | Payload
JOIN_EVENT_TYPE = "join"


class ClientEventModel(BaseModel):
    """Base model for client websocket events."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str

    def to_payload(self) -> Payload:
        """Convert the event model to a JSON-serializable dict."""
        return self.model_dump(by_alias=True, exclude_none=True)


class JoinEvent(ClientEventModel):
    type: Literal["join"]
    player_id: str = Field(alias="playerId")
    name: str


class StartGameEvent(ClientEventModel):
    type: Literal["start_game"]
    difficulty: Difficulty | None = None
    rounds: PositiveRoundCount | None = None
    round_length: PositiveRoundLengthSeconds | None = Field(default=None, alias="roundLength")


class PlayerCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str
    items: list[str]
    alternatives: dict[str, list[str]] | None = None
    is_custom: bool | None = Field(default=None, alias="is_custom")


class StartRoundEvent(ClientEventModel):
    type: Literal["start_round"]
    round: int | None = None
    cards: dict[str, PlayerCardPayload]


class RoundCompleteEvent(ClientEventModel):
    type: Literal["round_complete"]


class GameCompleteEvent(ClientEventModel):
    type: Literal["game_complete"]


class PlayerReadyEvent(ClientEventModel):
    type: Literal["player_ready"]
    player_id: str = Field(alias="playerId")


class StartGuessingEvent(ClientEventModel):
    type: Literal["start_guessing"]


class SubmitGuessEvent(ClientEventModel):
    type: Literal["submit_guess"]
    player_id: str = Field(alias="playerId")
    target_player_id: str = Field(alias="targetPlayerId")
    guesses: list[str] = Field(default_factory=list)


class RestartGameEvent(ClientEventModel):
    type: Literal["restart_game"]


class HeartbeatEvent(ClientEventModel):
    type: Literal["heartbeat"]


class SettingsUpdateEvent(ClientEventModel):
    type: Literal["settings_update"]
    difficulty: Difficulty | None = None
    rounds: PositiveRoundCount | None = None
    round_length: PositiveRoundLengthSeconds | None = Field(default=None, alias="roundLength")


class LanguageUpdateEvent(ClientEventModel):
    type: Literal["language_update"]
    language: LanguageCode = "en"


class DrawStrokeEvent(ClientEventModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: Literal["draw_stroke", "draw_stroke_partial"]
    player_id: str | None = Field(default=None, alias="playerId")


class DrawpadClearEvent(ClientEventModel):
    type: Literal["drawpad_clear"]


class PadVisibilityEvent(ClientEventModel):
    type: Literal["pad_visibility"]
    visible: bool = True


class PrivacyChangedEvent(ClientEventModel):
    type: Literal["privacy_changed"]
    is_private: bool = Field(alias="isPrivate")


class InitiateKickEvent(ClientEventModel):
    type: Literal["initiate_kick"]
    target_player_id: str = Field(alias="targetPlayerId")


class CastKickVoteEvent(ClientEventModel):
    type: Literal["cast_kick_vote"]
    target_player_id: str = Field(alias="targetPlayerId")


class RequestGameStateEvent(ClientEventModel):
    type: Literal["request_game_state"]
    player_id: str | None = Field(default=None, alias="playerId")


ClientEvent = Annotated[
    JoinEvent
    | StartGameEvent
    | StartRoundEvent
    | RoundCompleteEvent
    | GameCompleteEvent
    | PlayerReadyEvent
    | StartGuessingEvent
    | SubmitGuessEvent
    | RestartGameEvent
    | HeartbeatEvent
    | SettingsUpdateEvent
    | LanguageUpdateEvent
    | DrawStrokeEvent
    | DrawpadClearEvent
    | PadVisibilityEvent
    | PrivacyChangedEvent
    | InitiateKickEvent
    | CastKickVoteEvent
    | RequestGameStateEvent,
    Field(discriminator="type"),
]

CLIENT_EVENT_ADAPTER = TypeAdapter(ClientEvent)


def parse_client_event(payload: object) -> ClientEventModel:
    """Validate a JSON websocket payload as a known client event."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        msg = "WebSocket payload must be a JSON object."
        raise TypeError(msg)
    return CLIENT_EVENT_ADAPTER.validate_python(payload)


class ServerEventModel(BaseModel):
    """Base model for server websocket events."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: str

    def to_payload(self) -> Payload:
        """Convert the event model to a JSON-serializable dict."""
        return self.model_dump(by_alias=True, exclude_none=True)


class PlayerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    name: str
    categories: list[str] = Field(default_factory=list)


class PlayerListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class RoomStateEvent(ServerEventModel):
    type: Literal["room_state"] = "room_state"
    players: list[PlayerSnapshot]
    host_id: str | None = Field(default=None, alias="hostId")
    categories: list[str] = Field(default_factory=list)
    game_phase: GamePhase = Field(alias="gamePhase")
    difficulty: Difficulty
    max_rounds: int = Field(alias="maxRounds")
    round_start_time: int | None = Field(default=None, alias="roundStartTime")
    round_length: PositiveRoundLengthSeconds | None = Field(default=None, alias="roundLength")
    pad_visibility: bool = Field(alias="padVisibility")
    language: LanguageCode


class PlayerJoinedEvent(ServerEventModel):
    type: Literal["player_joined"] = "player_joined"
    player_id: str = Field(alias="playerId")
    name: str
    players: list[PlayerListItem]
    is_host: bool = Field(alias="isHost")


class HostRestoredEvent(ServerEventModel):
    type: Literal["host_restored"] = "host_restored"
    message: str


class ProtocolErrorEvent(ServerEventModel):
    """Recoverable in-band protocol error for an accepted websocket."""

    type: Literal[
        "protocol_error",
        "permission_error",
        "player_ready_error",
        "submit_guess_error",
        "join_error",
        "kick_error",
    ]
    error: str
    message: str | None = None


class StartRoundBroadcastEvent(ServerEventModel):
    type: Literal["start_round"] = "start_round"
    round: int | None = None
    cards: dict[str, PlayerCardPayload]
    round_start_time: int = Field(alias="roundStartTime")


class ReadyStatusEvent(ServerEventModel):
    type: Literal["ready_status"] = "ready_status"
    ready_count: int = Field(alias="readyCount")
    total_players: int = Field(alias="totalPlayers")


class HostChangedEvent(ServerEventModel):
    type: Literal["host_changed"] = "host_changed"
    new_host_id: str = Field(alias="newHostId")


class LanguageUpdatedEvent(ServerEventModel):
    type: Literal["language_update"] = "language_update"
    language: str


class PlayerLeftEvent(ServerEventModel):
    type: Literal["player_left"] = "player_left"
    player_id: str = Field(alias="playerId")


class KickVoteStartedEvent(ServerEventModel):
    type: Literal["kick_vote_started"] = "kick_vote_started"
    target_player_id: str = Field(alias="targetPlayerId")
    target_player_name: str = Field(alias="targetPlayerName")
    initiator_id: str = Field(alias="initiatorId")
    required_votes: int = Field(alias="requiredVotes")
    current_votes: int = Field(alias="currentVotes")
    expires_at: float = Field(alias="expiresAt")


class KickVoteUpdatedEvent(ServerEventModel):
    type: Literal["kick_vote_updated"] = "kick_vote_updated"
    target_player_id: str = Field(alias="targetPlayerId")
    current_votes: int = Field(alias="currentVotes")
    required_votes: int = Field(alias="requiredVotes")


class KickVoteExpiredEvent(ServerEventModel):
    type: Literal["kick_vote_expired"] = "kick_vote_expired"
    target_player_id: str = Field(alias="targetPlayerId")


class PlayerKickedEvent(ServerEventModel):
    type: Literal["player_kicked"] = "player_kicked"
    player_id: str = Field(alias="playerId")
    player_name: str = Field(alias="playerName")
    reason: str


class RoundResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    player_id: str = Field(alias="playerId")
    target_player_id: str = Field(alias="targetPlayerId")
    correct_guesses: int = Field(alias="correctGuesses")
    total_items: int = Field(alias="totalItems")
    points_earned: int = Field(alias="pointsEarned")


class RoundCompleteBroadcastEvent(ServerEventModel):
    type: Literal["round_complete"] = "round_complete"
    results: list[RoundResultItem]
    scores: dict[str, int]


class GameCompleteBroadcastEvent(ServerEventModel):
    type: Literal["game_complete"] = "game_complete"
    final_scores: dict[str, int] = Field(alias="finalScores")
    winner: str


def event_payload(event_type: str, /, **fields: object) -> Payload:
    """Fallback helper for lightweight json messages."""
    return {"type": event_type, **fields}


def dump_ws_message(message: WebSocketMessage) -> object:
    """Serialize a websocket message into JSON-compatible data."""
    if isinstance(message, BaseModel):
        return message.model_dump(by_alias=True, exclude_none=True)
    return message


async def send_ws_message(websocket: WebSocket, message: WebSocketMessage) -> None:
    """Send a websocket message as JSON."""
    await websocket.send_json(dump_ws_message(message))
