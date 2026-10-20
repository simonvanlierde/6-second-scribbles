"""Coverage for room actions/routes and contract generation helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.types import GamePhase
from app.rooms import actions as room_actions
from app.rooms import router as room_router
from app.rooms.manager import GameRoom
from app.rooms.protocol import (
    CastKickVoteEvent,
    DefaultLocaleUpdateEvent,
    DefaultLocaleUpdateServerEvent,
    DrawpadClearEvent,
    InitiateKickEvent,
    PadVisibilityEvent,
    PlayerReadyEvent,
    PrivacyChangedEvent,
    RestartGameEvent,
    SettingsUpdateEvent,
    StartGameEvent,
    SubmitGuessEvent,
)
from scripts import generate_contracts
from scripts.generate_contracts import _event_type_for_schema as event_type_for_schema

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from fastapi import Request, WebSocket

    from app.rooms.session import RoomWebSocketSession
    from tests.support import TestWebSocket

DEFAULT_LOCALE = "nl"
DIFFICULTY_HARD = "hard"
GENERATED_ROOM_CODE = "BBBBBB"
SCHEMA_ANY_OF_KEY = "anyOf"
SCHEMA_DEFS_KEY = "$defs"


class _Session:
    def __init__(self, room: GameRoom, *, player_id: str | None, host: bool = True) -> None:
        self.room = room
        self.player_id = player_id
        self.is_observer = False
        self.websocket = AsyncMock()
        self.current_user = None
        self._host = host
        self.error_calls: list[tuple[str, str, str]] = []

    def is_host(self) -> bool:
        return self._host

    async def send_error(self, event_type: str, error: str, message: str) -> None:
        self.error_calls.append((event_type, error, message))

    def resolve_join_locale(self, preferred_locale: str | None) -> str:
        return preferred_locale or "en"


async def test_room_action_handlers_cover_validation_and_updates(
    make_ws: Callable[..., TestWebSocket],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Action handlers update room state and reject invalid player ids."""
    room = GameRoom("ROOM-ACTIONS")
    await room.add_player("host", "Host", cast("WebSocket", make_ws()))
    session = _Session(room, player_id="host", host=True)

    broadcast = AsyncMock()
    persist = AsyncMock()
    start_guessing = Mock(return_value=123)
    monkeypatch.setattr(room, "broadcast", broadcast)
    monkeypatch.setattr(room, "persist", persist)
    monkeypatch.setattr(room.scheduler, "schedule_scoring_timeout", Mock())
    monkeypatch.setattr(room, "start_guessing", start_guessing)

    await room_actions.handle_settings_update(
        cast("RoomWebSocketSession", session),
        SettingsUpdateEvent(
            type="settings_update",
            difficulty="hard",
            rounds=5,
            drawingTimeLimit=40,
            guessingTimeLimit=25,
        ),
    )
    await room_actions.handle_default_locale_update(
        cast("RoomWebSocketSession", session),
        DefaultLocaleUpdateEvent(type="default_locale_update", locale="nl"),
    )
    await room_actions.handle_pad_visibility(
        cast("RoomWebSocketSession", session),
        PadVisibilityEvent(type="pad_visibility", visible=False),
    )
    await room_actions.handle_privacy_changed(
        cast("RoomWebSocketSession", session),
        PrivacyChangedEvent(type="privacy_changed", isPrivate=True),
    )

    invalid_ready = _Session(room, player_id="host", host=True)
    await room_actions.handle_player_ready(
        cast("RoomWebSocketSession", invalid_ready),
        PlayerReadyEvent(type="player_ready", playerId="other"),
    )
    invalid_guess = _Session(room, player_id="host", host=True)
    await room_actions.handle_submit_guess(
        cast("RoomWebSocketSession", invalid_guess),
        SubmitGuessEvent(type="submit_guess", playerId="other", targetPlayerId="host", guesses=["cat"]),
    )

    assert room.metadata.difficulty == DIFFICULTY_HARD
    assert room.metadata.max_rounds == 5
    assert room.metadata.drawing_time_limit == 40
    assert room.metadata.guessing_time_limit == 25
    assert room.metadata.default_locale == DEFAULT_LOCALE
    assert room.metadata.pad_visibility is False
    assert room.metadata.is_private is True
    assert any(isinstance(call.args[0], DefaultLocaleUpdateServerEvent) for call in broadcast.await_args_list)
    assert invalid_ready.error_calls == [
        ("player_ready_error", "invalid_player", "Ready updates must match your connection."),
    ]
    assert invalid_guess.error_calls == [
        ("submit_guess_error", "invalid_player", "Guess submissions must match your connection."),
    ]
    assert persist.await_count >= 4


async def test_settings_broadcasts_carry_stored_room_settings(
    make_ws: Callable[..., TestWebSocket],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """start_game and settings_update broadcast the room's stored settings, not the client's echo."""
    room = GameRoom("ROOM-SETTINGS")
    await room.add_player("host", "Host", cast("WebSocket", make_ws()))
    await room.add_player("guest", "Guest", cast("WebSocket", make_ws()))
    session = cast("RoomWebSocketSession", _Session(room, player_id="host", host=True))
    broadcast = AsyncMock()
    monkeypatch.setattr(room, "broadcast", broadcast)
    monkeypatch.setattr(room, "persist", AsyncMock())
    monkeypatch.setattr(room.scheduler, "schedule_first_round", Mock())

    await room_actions.handle_settings_update(
        session,
        SettingsUpdateEvent(type="settings_update", rounds=7, drawingTimeLimit=40, guessingTimeLimit=25),
    )
    # A partial update keeps the other stored settings, and the broadcast says so.
    await room_actions.handle_settings_update(session, SettingsUpdateEvent(type="settings_update", difficulty="hard"))
    assert broadcast.await_args is not None
    assert broadcast.await_args.args[0] == SettingsUpdateEvent(
        type="settings_update",
        difficulty="hard",
        rounds=7,
        drawingTimeLimit=40,
        guessingTimeLimit=25,
    )

    # The server fills in defaults for omitted start settings; clients must see them.
    await room_actions.handle_start_game(session, StartGameEvent(type="start_game"))
    assert broadcast.await_args is not None
    assert broadcast.await_args.args[0] == StartGameEvent(
        type="start_game",
        difficulty="hard",
        rounds=5,
        drawingTimeLimit=None,
        guessingTimeLimit=60,
    )


async def test_room_action_handlers_cover_restart_drawpad_and_kick_errors(
    make_ws: Callable[..., TestWebSocket],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restart, drawpad, disconnect, and kick-vote error branches stay covered."""
    room = GameRoom("ROOM-MORE-ACTIONS")
    await room.add_player("host", "Host", cast("WebSocket", make_ws()))
    await room.add_player("guest", "Guest", cast("WebSocket", make_ws()))
    session = _Session(room, player_id="host", host=True)
    non_host = _Session(room, player_id="guest", host=False)

    monkeypatch.setattr(room, "broadcast", AsyncMock())
    monkeypatch.setattr(room, "persist", AsyncMock())
    monkeypatch.setattr(room, "reset_game", Mock())
    monkeypatch.setattr(room, "remove_player", AsyncMock())
    monkeypatch.setattr(
        room,
        "initiate_kick_vote",
        AsyncMock(return_value=SimpleNamespace(success=False, error="vote_failed")),
    )
    monkeypatch.setattr(
        room,
        "cast_kick_vote",
        AsyncMock(return_value=SimpleNamespace(success=False, error="cast_failed")),
    )

    await room_actions.handle_restart_game(
        cast("RoomWebSocketSession", session),
        RestartGameEvent(type="restart_game"),
    )
    await room_actions.handle_drawpad_clear(
        cast("RoomWebSocketSession", session),
        DrawpadClearEvent(type="drawpad_clear"),
    )
    await room_actions.handle_drawpad_clear(
        cast("RoomWebSocketSession", non_host),
        DrawpadClearEvent(type="drawpad_clear"),
    )
    await room_actions.handle_initiate_kick(
        cast("RoomWebSocketSession", session),
        InitiateKickEvent(type="initiate_kick", targetPlayerId="guest"),
    )
    await room_actions.handle_cast_kick_vote(
        cast("RoomWebSocketSession", session),
        CastKickVoteEvent(type="cast_kick_vote", targetPlayerId="guest"),
    )
    await room_actions.handle_disconnect(cast("RoomWebSocketSession", session))

    assert non_host.error_calls == [("permission_error", "host_only", "Only the host can clear the drawpad.")]
    assert ("kick_error", "vote_failed", "") in session.error_calls
    assert ("kick_error", "cast_failed", "") in session.error_calls


async def test_room_router_helpers_cover_not_found_and_retry_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Router helpers retry collisions and surface room-not-found cases."""
    fake_room = SimpleNamespace(
        players={"p1": object(), "p2": object()},
        metadata=SimpleNamespace(game_phase=GamePhase.LOBBY),
        persist=AsyncMock(),
        get_player_locale=lambda _player_id: "fr",
    )
    redis_client = SimpleNamespace(set=AsyncMock(side_effect=[False, True]))
    choice_values = iter(["A", "A", "A", "A", "A", "A", "B", "B", "B", "B", "B", "B"])

    monkeypatch.setattr(room_router, "get_redis", AsyncMock(return_value=redis_client))
    monkeypatch.setattr(room_router.room_manager, "get_or_create_room", Mock(return_value=fake_room))
    monkeypatch.setattr(room_router.room_manager, "find_random_public_room", Mock(return_value=None))
    monkeypatch.setattr(room_router.secrets, "choice", lambda _chars: next(choice_values))

    fake_request = SimpleNamespace(headers={}, client=None)
    created = await room_router.create_room(cast("Request", fake_request))
    monkeypatch.setattr(room_router.room_manager, "get_room", Mock(return_value=fake_room))
    existing_status = room_router.get_room_status(room_id="ROOM01")
    monkeypatch.setattr(room_router.room_manager, "get_room", Mock(return_value=None))
    missing_status = room_router.get_room_status(room_id="ROOM02")

    assert created.room_code == GENERATED_ROOM_CODE
    assert existing_status.exists is True
    assert existing_status.players == 2
    assert missing_status.exists is False


def test_generate_contract_helpers_cover_normalization_and_event_types() -> None:
    """Contract helpers normalize schemas, inline refs, and list a union's event types."""
    schema = {
        "$defs": {"Named": {"type": "object", "properties": {"type": {"const": "ping", "default": "ping"}}}},
        "oneOf": [{"$ref": "#/$defs/Named"}],
        "properties": {"type": {"const": "ping", "default": "ping"}},
    }

    prepared = generate_contracts.prepare(schema)
    event_types = generate_contracts.union_event_types(
        {
            "anyOf": [
                {"properties": {"type": {"const": "ping"}}},
                {"properties": {"type": {"const": "pong"}}},
                "ignored",
            ]
        }
    )

    assert SCHEMA_DEFS_KEY not in prepared
    assert SCHEMA_ANY_OF_KEY in prepared
    assert prepared["properties"]["type"] == {"const": "ping"}
    assert event_types == ["ping", "pong"]


def test_generate_contract_helpers_cover_errors_and_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Error branches and the main write orchestration remain covered."""
    with pytest.raises(TypeError, match="missing properties"):
        event_type_for_schema({})

    with pytest.raises(TypeError, match="Expected schema to contain anyOf"):
        generate_contracts.union_event_types({})

    with pytest.raises(ValueError, match="client event catalog does not match schema types"):
        generate_contracts.assert_catalog_matches_events(["join"], {"leave": {}}, "client")

    monkeypatch.setattr(generate_contracts, "CONTRACTS_ROOT", tmp_path)
    monkeypatch.setattr(
        generate_contracts,
        "generate_schema",
        lambda _adapter, *, mode: {"anyOf": [{"properties": {"type": {"const": f"{mode}-event"}}}]},
    )
    monkeypatch.setattr(
        generate_contracts,
        "CONTRACT_EVENT_CATALOG",
        {
            "client": {"validation-event": {}},
            "server": {"serialization-event": {}},
        },
    )
    write_schema = Mock()
    write_catalog = Mock()
    write_openapi = Mock()
    monkeypatch.setattr(generate_contracts, "write_schema", write_schema)
    monkeypatch.setattr(generate_contracts, "write_event_catalog", write_catalog)
    monkeypatch.setattr(generate_contracts, "write_openapi", write_openapi)

    generate_contracts.main()

    assert write_schema.call_count == 2
    write_catalog.assert_called_once()
    write_openapi.assert_called_once()
