"""
Shared message types between client and server
"""
from typing import Literal, Union, TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel


class Player(TypedDict):
    id: str
    name: str


class Stroke(TypedDict):
    color: str
    width: float
    points: List[Dict[str, float]]


# Message types
class JoinMessage(BaseModel):
    type: Literal["join"]
    playerId: str
    name: str


class PlayerJoinedMessage(BaseModel):
    type: Literal["player_joined"]
    playerId: str
    name: str
    players: List[Player]


class PlayerLeftMessage(BaseModel):
    type: Literal["player_left"]
    playerId: str


class HostChangedMessage(BaseModel):
    type: Literal["host_changed"]
    newHostId: str


class StartGameMessage(BaseModel):
    type: Literal["start_game"]
    difficulty: str
    rounds: int
    roundLength: int


class StartRoundMessage(BaseModel):
    type: Literal["start_round"]
    round: int
    roundStartTime: int
    cards: Dict[str, Dict[str, Any]]


class SubmitGuessMessage(BaseModel):
    type: Literal["submit_guess"]
    playerId: str
    targetPlayerId: str
    guesses: List[str]


class RoundCompleteMessage(BaseModel):
    type: Literal["round_complete"]
    scores: Dict[str, int]
    results: Optional[Any] = None


class GameCompleteMessage(BaseModel):
    type: Literal["game_complete"]
    finalScores: Dict[str, int]


class RequestGameStateMessage(BaseModel):
    type: Literal["request_game_state"]
    playerId: str


class PlayerReadyMessage(BaseModel):
    type: Literal["player_ready"]
    playerId: str


class RestartGameMessage(BaseModel):
    type: Literal["restart_game"]


class HeartbeatMessage(BaseModel):
    type: Literal["heartbeat"]
    playerId: str


class SettingsUpdateMessage(BaseModel):
    type: Literal["settings_update"]
    difficulty: str
    rounds: int
    roundLength: int


class DrawStrokeMessage(BaseModel):
    type: Literal["draw_stroke"]
    playerId: str
    stroke: Stroke


class DrawpadClearMessage(BaseModel):
    type: Literal["drawpad_clear"]
    playerId: str


class DrawStrokePartialMessage(BaseModel):
    type: Literal["draw_stroke_partial"]
    playerId: str
    stroke: Stroke


class PadVisibilityMessage(BaseModel):
    type: Literal["pad_visibility"]
    playerId: str
    visible: bool


class DrawingCompleteMessage(BaseModel):
    type: Literal["drawing_complete"]
    playerId: str
    drawing: Any


class StartGuessingMessage(BaseModel):
    type: Literal["start_guessing"]
    roundStartTime: int


GameMessage = Union[
    JoinMessage,
    PlayerJoinedMessage,
    PlayerLeftMessage,
    HostChangedMessage,
    StartGameMessage,
    StartRoundMessage,
    SubmitGuessMessage,
    RoundCompleteMessage,
    GameCompleteMessage,
    RequestGameStateMessage,
    PlayerReadyMessage,
    RestartGameMessage,
    HeartbeatMessage,
    SettingsUpdateMessage,
    DrawStrokeMessage,
    DrawpadClearMessage,
    DrawStrokePartialMessage,
    PadVisibilityMessage,
    DrawingCompleteMessage,
    StartGuessingMessage,
]
