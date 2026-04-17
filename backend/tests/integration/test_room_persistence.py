"""Integration tests for Redis-backed room persistence."""

from __future__ import annotations

import pytest

from app.core.types import GamePhase
from app.rooms.manager import RoomManager, room_manager
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from tests.constants import ANIMALS, HOST_ONE

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_room_manager_restores_room_state_from_real_redis(redis_client: object) -> None:
    """Room state can be restored from Redis."""
    _ = redis_client
    room = room_manager.get_or_create_room("REDIS01")
    room.host_id = HOST_ONE
    room.metadata.game_phase = GamePhase.DRAWING
    room.metadata.current_round = 2
    room.metadata.ready_players.add(HOST_ONE)
    room.metadata.player_assignments = {
        HOST_ONE: PlayerPromptAssignmentState(
            category_id=1,
            category="Animals",
            item_ids=[11, 12],
            items=["cat", "dog"],
            alternatives={"cat": ["kitty"]},
        ),
    }
    room.metadata.guess_submissions = [
        GuessSubmissionState(player_id=HOST_ONE, target_player_id=HOST_ONE, guesses=["cat"]),
    ]

    await room.persist()

    restored_manager = RoomManager()
    await restored_manager.start()
    try:
        restored_room = restored_manager.get_room("REDIS01")
        assert restored_room is not None
        assert restored_room.host_id == HOST_ONE
        assert restored_room.metadata.game_phase == GamePhase.DRAWING
        assert restored_room.metadata.current_round == 2
        assert restored_room.metadata.ready_players == {HOST_ONE}
        assert restored_room.metadata.player_assignments[HOST_ONE].category == ANIMALS
        assert restored_room.metadata.guess_submissions[0].player_id == HOST_ONE
        assert restored_room.metadata.guess_submissions[0].guesses == ["cat"]
    finally:
        await restored_manager.stop()
