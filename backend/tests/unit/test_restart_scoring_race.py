"""Restarting during scoring must leave the room in the lobby."""

import asyncio
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

from app.categories.service import LocalizedScoringTargets
from app.core.types import GamePhase
from app.rooms import manager as manager_module
from app.rooms import rounds
from app.rooms.manager import GameRoom
from app.rooms.session import RoomWebSocketSession
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from app.scoring import GuessTarget
from tests.constants import PLAYER_ONE_ID, PLAYER_TWO_ID

if TYPE_CHECKING:
    import pytest


async def test_restart_during_scoring_finishes_in_lobby(
    room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An in-flight score cannot undo the host's request to return to the lobby."""
    room = room_with_players
    room.metadata.game_phase = GamePhase.GUESSING
    room.metadata.current_round = 1
    room.metadata.player_assignments = {
        PLAYER_TWO_ID: PlayerPromptAssignmentState(category_id=1, category="Animals", item_ids=[1], items=["cat"])
    }
    room.metadata.guess_submissions = [
        GuessSubmissionState(player_id=PLAYER_ONE_ID, target_player_id=PLAYER_TWO_ID, guesses=["cat"])
    ]
    entered, release = asyncio.Event(), asyncio.Event()

    async def scoring_targets(*_args: object, **_kwargs: object) -> LocalizedScoringTargets:
        entered.set()
        await release.wait()
        return LocalizedScoringTargets(
            category_id=1,
            category_name="Animals",
            targets=[GuessTarget(item_id=1, label="cat", aliases=[])],
            locale="en",
        )

    monkeypatch.setattr(rounds.category_service, "get_localized_scoring_targets", scoring_targets)
    session_maker = Mock(return_value=AsyncMock())
    monkeypatch.setattr(manager_module, "get_session_maker", lambda: session_maker)
    monkeypatch.setattr(room, "persist", AsyncMock())
    host = RoomWebSocketSession(room, room.players[PLAYER_ONE_ID].websocket)
    host.player_id = PLAYER_ONE_ID
    scoring = asyncio.create_task(room.score_and_broadcast_round())
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        restarting = asyncio.create_task(host.handle(json.dumps({"type": "restart_game"})))
        await asyncio.sleep(0)
    finally:
        release.set()
    await asyncio.wait_for(asyncio.gather(scoring, restarting), timeout=1)

    assert room.metadata.game_phase == GamePhase.LOBBY
    assert all(score == 0 for score in room.metadata.player_scores.values())
    assert not room.scheduler.is_next_round_pending()
