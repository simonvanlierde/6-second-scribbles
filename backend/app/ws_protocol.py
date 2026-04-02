"""Typed websocket protocol models for realtime room events."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ClientEventModel(BaseModel):
    """Base model for client websocket events."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str

    def to_payload(self) -> dict[str, Any]:
        """Serialize the event back to the wire format."""
        return self.model_dump(by_alias=True, exclude_none=True)


class UnknownEvent(ClientEventModel):
    """Fallback model for forward-compatible pass-through events."""


class JoinEvent(ClientEventModel):
    type: Literal["join"]
    player_id: str = Field(alias="playerId")
    name: str


class StartGameEvent(ClientEventModel):
    type: Literal["start_game"]
    difficulty: str | None = None
    rounds: int | None = None
    round_length: int | None = Field(default=None, alias="roundLength")


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
    difficulty: str | None = None
    rounds: int | None = None
    round_length: int | None = Field(default=None, alias="roundLength")


class LanguageUpdateEvent(ClientEventModel):
    type: Literal["language_update"]
    language: str = "en"


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


EVENT_MODELS: dict[str, type[ClientEventModel]] = {
    "join": JoinEvent,
    "start_game": StartGameEvent,
    "start_round": StartRoundEvent,
    "round_complete": RoundCompleteEvent,
    "game_complete": GameCompleteEvent,
    "player_ready": PlayerReadyEvent,
    "start_guessing": StartGuessingEvent,
    "submit_guess": SubmitGuessEvent,
    "restart_game": RestartGameEvent,
    "heartbeat": HeartbeatEvent,
    "settings_update": SettingsUpdateEvent,
    "language_update": LanguageUpdateEvent,
    "draw_stroke": DrawStrokeEvent,
    "draw_stroke_partial": DrawStrokeEvent,
    "drawpad_clear": DrawpadClearEvent,
    "pad_visibility": PadVisibilityEvent,
    "privacy_changed": PrivacyChangedEvent,
    "initiate_kick": InitiateKickEvent,
    "cast_kick_vote": CastKickVoteEvent,
    "request_game_state": RequestGameStateEvent,
}


def parse_client_event(data: str) -> ClientEventModel:
    """Parse a websocket payload into a typed client event."""
    payload = json.loads(data)
    if not isinstance(payload, dict):
        msg = "WebSocket payload must be a JSON object."
        raise ValueError(msg)

    event_type = payload.get("type")
    if not isinstance(event_type, str) or not event_type:
        msg = "WebSocket payload must include a string type."
        raise ValueError(msg)

    model = EVENT_MODELS.get(event_type, UnknownEvent)
    return model.model_validate(payload)


__all__ = [
    "ClientEventModel",
    "DrawStrokeEvent",
    "JoinEvent",
    "PlayerReadyEvent",
    "SettingsUpdateEvent",
    "StartGameEvent",
    "StartRoundEvent",
    "SubmitGuessEvent",
    "ValidationError",
    "parse_client_event",
]
