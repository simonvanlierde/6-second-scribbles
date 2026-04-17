"""WebSocket protocol models and serialization helpers."""

# ruff: noqa: D101

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.core.types import (
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


class EventCatalogEntry(TypedDict):
    group: str
    summary: str


class ClientEventModel(BaseModel):
    """Base model for client websocket events."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str


class ClientPlayerEventModel(ClientEventModel):
    """Client event with a required player id."""

    player_id: str = Field(alias="playerId")


class ClientTargetPlayerEventModel(ClientEventModel):
    """Client event with a required target player id."""

    target_player_id: str = Field(alias="targetPlayerId")


class JoinEvent(ClientPlayerEventModel):
    type: Literal["join"]
    name: str
    preferred_locale: LanguageCode | None = Field(default=None, alias="preferredLocale")


class GameSettingsEventModel(ClientEventModel):
    """Shared client payload fields for updating game settings."""

    difficulty: Difficulty | None = None
    rounds: PositiveRoundCount | None = None
    drawing_time_limit: PositiveRoundLengthSeconds | None = Field(default=None, alias="drawingTimeLimit")
    guessing_time_limit: PositiveRoundLengthSeconds | None = Field(default=None, alias="guessingTimeLimit")


class StartGameEvent(GameSettingsEventModel):
    type: Literal["start_game"]


class PlayerCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category_id: int | None = Field(default=None, alias="categoryId")
    category: str
    item_ids: list[int] | None = Field(default=None, alias="itemIds")
    items: list[str]
    alternatives: dict[str, list[str]] | None = None


class StartRoundEvent(ClientEventModel):
    type: Literal["start_round"]
    round: int | None = None
    cards: dict[str, PlayerCardPayload]


class RoundCompleteEvent(ClientEventModel):
    type: Literal["round_complete"]


class GameCompleteEvent(ClientEventModel):
    type: Literal["game_complete"]


class PlayerReadyEvent(ClientPlayerEventModel):
    type: Literal["player_ready"]


class StartGuessingEvent(ClientEventModel):
    type: Literal["start_guessing"]
    guessing_start_time: int | None = Field(default=None, alias="guessingStartTime")
    guess_targets: dict[str, str] = Field(default_factory=dict, alias="guessTargets")


class SubmitGuessEvent(ClientPlayerEventModel, ClientTargetPlayerEventModel):
    type: Literal["submit_guess"]
    guesses: list[str] = Field(default_factory=list)


class RestartGameEvent(ClientEventModel):
    type: Literal["restart_game"]


class HeartbeatEvent(ClientEventModel):
    type: Literal["heartbeat"]


class SettingsUpdateEvent(GameSettingsEventModel):
    type: Literal["settings_update"]


class DefaultLocaleUpdateEvent(ClientEventModel):
    type: Literal["default_locale_update"]
    locale: LanguageCode = "en"


class RoomCustomCategoriesUpdateEvent(ClientEventModel):
    type: Literal["room_custom_categories_update"]
    category_ids: list[int] | None = Field(default=None, alias="categoryIds")


class DrawEventModel(ClientEventModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    player_id: str | None = Field(default=None, alias="playerId")


class DrawStrokeEvent(DrawEventModel):
    type: Literal["draw_stroke"]


class DrawStrokePartialEvent(DrawEventModel):
    type: Literal["draw_stroke_partial"]


class DrawpadClearEvent(ClientEventModel):
    type: Literal["drawpad_clear"]


class PadVisibilityEvent(ClientEventModel):
    type: Literal["pad_visibility"]
    visible: bool = True


class PrivacyChangedEvent(ClientEventModel):
    type: Literal["privacy_changed"]
    is_private: bool = Field(alias="isPrivate")


class InitiateKickEvent(ClientTargetPlayerEventModel):
    type: Literal["initiate_kick"]


class CastKickVoteEvent(ClientTargetPlayerEventModel):
    type: Literal["cast_kick_vote"]


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
    | DefaultLocaleUpdateEvent
    | RoomCustomCategoriesUpdateEvent
    | DrawStrokeEvent
    | DrawStrokePartialEvent
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


class ServerPlayerEventModel(ServerEventModel):
    """Server event with a required player id."""

    player_id: str = Field(alias="playerId")


class ServerTargetPlayerEventModel(ServerEventModel):
    """Server event with a required target player id."""

    target_player_id: str = Field(alias="targetPlayerId")


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
    guessing_start_time: int | None = Field(default=None, alias="guessingStartTime")
    drawing_time_limit: PositiveRoundLengthSeconds | None = Field(default=None, alias="drawingTimeLimit")
    guessing_time_limit: PositiveRoundLengthSeconds | None = Field(default=None, alias="guessingTimeLimit")
    guess_targets: dict[str, str] = Field(default_factory=dict, alias="guessTargets")
    pad_visibility: bool = Field(alias="padVisibility")
    is_private: bool = Field(alias="isPrivate")
    default_locale: LanguageCode = Field(alias="defaultLocale")
    custom_category_ids: list[int] | None = Field(default=None, alias="customCategoryIds")


class PlayerJoinedEvent(ServerPlayerEventModel):
    type: Literal["player_joined"] = "player_joined"
    name: str
    players: list[PlayerListItem]
    is_host: bool = Field(alias="isHost")


class HostRestoredEvent(ServerEventModel):
    type: Literal["host_restored"] = "host_restored"
    message: str


class RecoverableErrorEvent(ServerEventModel):
    """Recoverable in-band protocol error for an accepted websocket."""

    error: str
    message: str | None = None


class ProtocolErrorEvent(RecoverableErrorEvent):
    type: Literal["protocol_error"] = "protocol_error"


class PermissionErrorEvent(RecoverableErrorEvent):
    type: Literal["permission_error"] = "permission_error"


class PlayerReadyErrorEvent(RecoverableErrorEvent):
    type: Literal["player_ready_error"] = "player_ready_error"


class SubmitGuessErrorEvent(RecoverableErrorEvent):
    type: Literal["submit_guess_error"] = "submit_guess_error"


class JoinErrorEvent(RecoverableErrorEvent):
    type: Literal["join_error"] = "join_error"


class KickErrorEvent(RecoverableErrorEvent):
    type: Literal["kick_error"] = "kick_error"


class StartRoundServerEvent(ServerEventModel):
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


class DefaultLocaleUpdateServerEvent(ServerEventModel):
    type: Literal["default_locale_update"] = "default_locale_update"
    locale: LanguageCode


class RoomCustomCategoriesUpdateServerEvent(ServerEventModel):
    type: Literal["room_custom_categories_update"] = "room_custom_categories_update"
    category_ids: list[int] | None = Field(default=None, alias="categoryIds")


class PlayerLeftEvent(ServerPlayerEventModel):
    type: Literal["player_left"] = "player_left"


class KickVoteStartedEvent(ServerTargetPlayerEventModel):
    type: Literal["kick_vote_started"] = "kick_vote_started"
    target_player_name: str = Field(alias="targetPlayerName")
    initiator_id: str = Field(alias="initiatorId")
    required_votes: int = Field(alias="requiredVotes")
    current_votes: int = Field(alias="currentVotes")
    expires_at: float = Field(alias="expiresAt")


class KickVoteUpdatedEvent(ServerTargetPlayerEventModel):
    type: Literal["kick_vote_updated"] = "kick_vote_updated"
    current_votes: int = Field(alias="currentVotes")
    required_votes: int = Field(alias="requiredVotes")


class KickVoteExpiredEvent(ServerTargetPlayerEventModel):
    type: Literal["kick_vote_expired"] = "kick_vote_expired"


class PlayerKickedEvent(ServerPlayerEventModel):
    type: Literal["player_kicked"] = "player_kicked"
    player_name: str = Field(alias="playerName")
    reason: str


class RoundResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    player_id: str = Field(alias="playerId")
    target_player_id: str = Field(alias="targetPlayerId")
    correct_guesses: int = Field(alias="correctGuesses")
    total_items: int = Field(alias="totalItems")
    points_earned: int = Field(alias="pointsEarned")


class RoundCompleteServerEvent(ServerEventModel):
    type: Literal["round_complete"] = "round_complete"
    results: list[RoundResultItem]
    scores: dict[str, int]


class GameCompleteServerEvent(ServerEventModel):
    type: Literal["game_complete"] = "game_complete"
    final_scores: dict[str, int] = Field(alias="finalScores")
    winner: str


RelayedClientEvent = Annotated[
    StartGameEvent
    | StartGuessingEvent
    | RestartGameEvent
    | SettingsUpdateEvent
    | DrawStrokeEvent
    | DrawStrokePartialEvent
    | DrawpadClearEvent
    | PadVisibilityEvent,
    Field(discriminator="type"),
]

ServerErrorEvent = Annotated[
    ProtocolErrorEvent
    | PermissionErrorEvent
    | PlayerReadyErrorEvent
    | SubmitGuessErrorEvent
    | JoinErrorEvent
    | KickErrorEvent,
    Field(discriminator="type"),
]

ServerEvent = Annotated[
    RoomStateEvent
    | PlayerJoinedEvent
    | HostRestoredEvent
    | ServerErrorEvent
    | StartRoundServerEvent
    | ReadyStatusEvent
    | HostChangedEvent
    | DefaultLocaleUpdateServerEvent
    | RoomCustomCategoriesUpdateServerEvent
    | PlayerLeftEvent
    | KickVoteStartedEvent
    | KickVoteUpdatedEvent
    | KickVoteExpiredEvent
    | PlayerKickedEvent
    | RoundCompleteServerEvent
    | GameCompleteServerEvent
    | RelayedClientEvent,
    Field(discriminator="type"),
]

SERVER_EVENT_ADAPTER = TypeAdapter(ServerEvent)

type ErrorEventType = Literal[
    "protocol_error",
    "permission_error",
    "player_ready_error",
    "submit_guess_error",
    "join_error",
    "kick_error",
]

ERROR_EVENT_MODELS: dict[ErrorEventType, type[ServerErrorEvent]] = {
    "protocol_error": ProtocolErrorEvent,
    "permission_error": PermissionErrorEvent,
    "player_ready_error": PlayerReadyErrorEvent,
    "submit_guess_error": SubmitGuessErrorEvent,
    "join_error": JoinErrorEvent,
    "kick_error": KickErrorEvent,
}

CLIENT_EVENT_CATALOG: dict[str, EventCatalogEntry] = {
    "heartbeat": {"group": "connection", "summary": "Keep the websocket session alive."},
    "join": {"group": "connection", "summary": "Join a room with the local player identity."},
    "request_game_state": {"group": "connection", "summary": "Request the latest room snapshot."},
    "game_complete": {"group": "gameFlow", "summary": "Signal that the game is complete."},
    "player_ready": {"group": "gameFlow", "summary": "Mark the current player as ready."},
    "restart_game": {"group": "gameFlow", "summary": "Restart the game from the lobby state."},
    "round_complete": {"group": "gameFlow", "summary": "Signal that the current round is complete."},
    "settings_update": {"group": "gameFlow", "summary": "Update shared game settings."},
    "start_game": {"group": "gameFlow", "summary": "Host starts a game with room settings."},
    "start_guessing": {"group": "gameFlow", "summary": "Host transitions the room into guessing."},
    "start_round": {"group": "gameFlow", "summary": "Host starts a drawing round with assigned cards."},
    "submit_guess": {"group": "gameFlow", "summary": "Submit guesses for another player's drawing."},
    "default_locale_update": {"group": "roomSettings", "summary": "Change the room default locale."},
    "room_custom_categories_update": {
        "group": "roomSettings",
        "summary": "Override the host's private category selection for this room.",
    },
    "privacy_changed": {"group": "roomSettings", "summary": "Change the room privacy setting."},
    "draw_stroke": {"group": "drawing", "summary": "Broadcast a completed draw stroke."},
    "draw_stroke_partial": {"group": "drawing", "summary": "Broadcast an in-progress draw stroke."},
    "drawpad_clear": {"group": "drawing", "summary": "Clear the shared drawpad."},
    "pad_visibility": {"group": "drawing", "summary": "Show or hide the shared drawpad."},
    "cast_kick_vote": {"group": "moderation", "summary": "Cast a vote in an active kick vote."},
    "initiate_kick": {"group": "moderation", "summary": "Start a kick vote for a target player."},
}

SERVER_EVENT_CATALOG: dict[str, EventCatalogEntry] = {
    "host_restored": {"group": "connection", "summary": "A reconnecting host regained host status."},
    "join_error": {"group": "connection", "summary": "Join failed but the connection remained valid."},
    "player_joined": {"group": "connection", "summary": "A player joined the room."},
    "player_left": {"group": "connection", "summary": "A player left the room."},
    "room_state": {"group": "connection", "summary": "Current room snapshot."},
    "game_complete": {"group": "gameFlow", "summary": "Game completion results broadcast."},
    "ready_status": {"group": "gameFlow", "summary": "Current ready-player counts."},
    "restart_game": {"group": "gameFlow", "summary": "Game restart broadcast."},
    "round_complete": {"group": "gameFlow", "summary": "Round completion results broadcast."},
    "settings_update": {"group": "gameFlow", "summary": "Game settings updated."},
    "start_game": {"group": "gameFlow", "summary": "Game start broadcast."},
    "start_guessing": {"group": "gameFlow", "summary": "Guessing phase started."},
    "start_round": {"group": "gameFlow", "summary": "Round start broadcast with assigned cards."},
    "default_locale_update": {"group": "roomSettings", "summary": "Room default locale updated."},
    "room_custom_categories_update": {
        "group": "roomSettings",
        "summary": "Room-level private category selection changed.",
    },
    "draw_stroke": {"group": "drawing", "summary": "A completed draw stroke relay."},
    "draw_stroke_partial": {"group": "drawing", "summary": "An in-progress draw stroke relay."},
    "drawpad_clear": {"group": "drawing", "summary": "Drawpad cleared."},
    "pad_visibility": {"group": "drawing", "summary": "Shared drawpad visibility changed."},
    "kick_error": {"group": "moderation", "summary": "Kick workflow error."},
    "kick_vote_expired": {"group": "moderation", "summary": "Kick vote expired."},
    "kick_vote_started": {"group": "moderation", "summary": "Kick vote started."},
    "kick_vote_updated": {"group": "moderation", "summary": "Kick vote tally updated."},
    "player_kicked": {"group": "moderation", "summary": "A player was kicked from the room."},
    "permission_error": {"group": "errors", "summary": "Unauthorized action attempt."},
    "player_ready_error": {"group": "errors", "summary": "Player-ready validation failed."},
    "protocol_error": {"group": "errors", "summary": "Malformed or invalid websocket payload."},
    "submit_guess_error": {"group": "errors", "summary": "Guess submission validation failed."},
    "host_changed": {"group": "gameFlow", "summary": "Host ownership changed."},
}

CONTRACT_EVENT_CATALOG = {
    "client": CLIENT_EVENT_CATALOG,
    "server": SERVER_EVENT_CATALOG,
}


def make_error_event(event_type: ErrorEventType, *, error: str, message: str | None = None) -> ServerErrorEvent:
    """Build a concrete recoverable server error event for one error type."""
    return ERROR_EVENT_MODELS[event_type](error=error, message=message)


def dump_ws_message(message: WebSocketMessage) -> object:
    """Serialize a websocket message into JSON-compatible data."""
    if isinstance(message, BaseModel):
        return message.model_dump(by_alias=True, exclude_none=True, mode="json")
    return message


async def send_ws_message(websocket: WebSocket, message: WebSocketMessage) -> None:
    """Send a websocket message as JSON."""
    await websocket.send_json(dump_ws_message(message))
