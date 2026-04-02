"""Shared message types between client and server."""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel


class Player(TypedDict):
    id: str
    name: str


class Stroke(TypedDict):
    color: str
    width: float
    points: list[dict[str, float]]


# Message types
class JoinMessage(BaseModel):
    type: Literal["join"]
    player_id: str
    name: str


class PlayerJoinedMessage(BaseModel):
    type: Literal["player_joined"]
    player_id: str
    name: str
    players: list[Player]


class PlayerLeftMessage(BaseModel):
    type: Literal["player_left"]
    player_id: str


class HostChangedMessage(BaseModel):
    type: Literal["host_changed"]
    new_host_id: str


class StartGameMessage(BaseModel):
    type: Literal["start_game"]
    difficulty: str
    rounds: int
    round_length: int


class StartRoundMessage(BaseModel):
    type: Literal["start_round"]
    round: int
    round_start_time: int
    cards: dict[str, dict[str, Any]]


class SubmitGuessMessage(BaseModel):
    type: Literal["submit_guess"]
    player_id: str
    target_player_id: str
    guesses: list[str]


class RoundCompleteMessage(BaseModel):
    type: Literal["round_complete"]
    scores: dict[str, int]
    results: Any | None = None


class GameCompleteMessage(BaseModel):
    type: Literal["game_complete"]
    final_scores: dict[str, int]


class RequestGameStateMessage(BaseModel):
    type: Literal["request_game_state"]
    player_id: str


class PlayerReadyMessage(BaseModel):
    type: Literal["player_ready"]
    player_id: str


class RestartGameMessage(BaseModel):
    type: Literal["restart_game"]


class HeartbeatMessage(BaseModel):
    type: Literal["heartbeat"]
    player_id: str


class SettingsUpdateMessage(BaseModel):
    type: Literal["settings_update"]
    difficulty: str
    rounds: int
    roundLength: int


class DrawStrokeMessage(BaseModel):
    type: Literal["draw_stroke"]
    player_id: str
    stroke: Stroke


class DrawpadClearMessage(BaseModel):
    type: Literal["drawpad_clear"]
    player_id: str


class DrawStrokePartialMessage(BaseModel):
    type: Literal["draw_stroke_partial"]
    player_id: str
    stroke: Stroke


class PadVisibilityMessage(BaseModel):
    type: Literal["pad_visibility"]
    player_id: str
    visible: bool


class DrawingCompleteMessage(BaseModel):
    type: Literal["drawing_complete"]
    player_id: str
    drawing: Any


class StartGuessingMessage(BaseModel):
    type: Literal["start_guessing"]
    roundStartTime: int


GameMessage = (
    JoinMessage
    | PlayerJoinedMessage
    | PlayerLeftMessage
    | HostChangedMessage
    | StartGameMessage
    | StartRoundMessage
    | SubmitGuessMessage
    | RoundCompleteMessage
    | GameCompleteMessage
    | RequestGameStateMessage
    | PlayerReadyMessage
    | RestartGameMessage
    | HeartbeatMessage
    | SettingsUpdateMessage
    | DrawStrokeMessage
    | DrawpadClearMessage
    | DrawStrokePartialMessage
    | PadVisibilityMessage
    | DrawingCompleteMessage
    | StartGuessingMessage
)
