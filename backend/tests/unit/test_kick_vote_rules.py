"""Refusal and expiry rules for kicking players, as players see them."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from app.rooms import kick_vote, player_lifecycle
from tests.constants import (
    HOST_CANNOT_BE_VOTE_KICKED_ERROR,
    KICK_VOTE_EXPIRED,
    KICK_VOTE_UPDATED,
    PLAYER_FOUR_ID,
    PLAYER_FOUR_NAME,
    PLAYER_KICKED,
    PLAYER_ONE_ID,
    PLAYER_ONE_NAME,
    PLAYER_THREE_ID,
    PLAYER_THREE_NAME,
    PLAYER_TWO_ID,
    PLAYER_TWO_NAME,
)
from tests.support import as_websocket

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.rooms.manager import GameRoom
    from tests.support import TestWebSocket

STRANGER_ID = "stranger"


def _sent_types(ws: TestWebSocket) -> list[str]:
    return [json.loads(text)["type"] for text in ws.sent_texts]


async def _fill_room(game_room: GameRoom, make_ws: Callable[..., TestWebSocket]) -> list[TestWebSocket]:
    """Join four players; the first one is the host."""
    sockets = [make_ws() for _ in range(4)]
    players = [
        (PLAYER_ONE_ID, PLAYER_ONE_NAME),
        (PLAYER_TWO_ID, PLAYER_TWO_NAME),
        (PLAYER_THREE_ID, PLAYER_THREE_NAME),
        (PLAYER_FOUR_ID, PLAYER_FOUR_NAME),
    ]
    for (player_id, name), ws in zip(players, sockets, strict=True):
        await player_lifecycle.add_player(game_room, player_id, name, as_websocket(ws))
    return sockets


class TestStartingAKick:
    """Who may start a kick, and what happens when they do."""

    async def test_host_kicks_at_once_without_a_vote(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """The host removes a player directly; nobody else has to vote."""
        host_ws, _, target_ws, _ = await _fill_room(game_room, make_ws)

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_ONE_ID, PLAYER_THREE_ID)

        assert result is None
        assert PLAYER_THREE_ID not in game_room.players
        assert PLAYER_THREE_ID in game_room.kicked_ids
        assert game_room.active_kick_votes == {}
        assert PLAYER_KICKED in _sent_types(host_ws)
        assert target_ws.close_calls == [{"code": 1008, "reason": "Kicked by host"}]

    async def test_refuses_initiators_and_targets_outside_the_room(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """A stale client cannot start a vote for, or against, someone who already left."""
        await _fill_room(game_room, make_ws)

        assert (
            await kick_vote.initiate_kick_vote(game_room, STRANGER_ID, PLAYER_THREE_ID)
            == kick_vote.INITIATOR_NOT_IN_ROOM_ERROR
        )
        assert (
            await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, STRANGER_ID)
            == kick_vote.TARGET_NOT_IN_ROOM_ERROR
        )
        assert game_room.active_kick_votes == {}

    async def test_refuses_kicking_yourself(self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]) -> None:
        """A player cannot start a vote against themselves."""
        await _fill_room(game_room, make_ws)

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_TWO_ID)

        assert result == kick_vote.SELF_KICK_ERROR
        assert PLAYER_TWO_ID in game_room.players

    async def test_refuses_a_second_vote_while_one_is_running(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """A running vote is not reset by another player starting it again."""
        await _fill_room(game_room, make_ws)
        await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_THREE_ID, PLAYER_FOUR_ID)

        assert result == kick_vote.VOTE_ALREADY_IN_PROGRESS_ERROR
        assert game_room.active_kick_votes[PLAYER_FOUR_ID].voters == {PLAYER_TWO_ID}

    async def test_an_expired_vote_can_be_started_again(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """Once a vote has run out, a new one starts fresh with only its initiator."""
        await _fill_room(game_room, make_ws)
        await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)
        game_room.active_kick_votes[PLAYER_FOUR_ID].expires_at = time.time() - 1

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_THREE_ID, PLAYER_FOUR_ID)

        assert result is None
        assert game_room.active_kick_votes[PLAYER_FOUR_ID].voters == {PLAYER_THREE_ID}


class TestCastingAVote:
    """Votes that must be refused, and votes on a vote that ran out."""

    async def test_refuses_a_voter_who_left(self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]) -> None:
        """A vote from someone no longer in the room does not count."""
        await _fill_room(game_room, make_ws)
        await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)

        result = await kick_vote.cast_kick_vote(game_room, STRANGER_ID, PLAYER_FOUR_ID)

        assert result == kick_vote.VOTER_NOT_IN_ROOM_ERROR
        assert game_room.active_kick_votes[PLAYER_FOUR_ID].voters == {PLAYER_TWO_ID}

    async def test_refuses_a_vote_when_none_is_running(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """Voting cannot start a vote by itself."""
        await _fill_room(game_room, make_ws)

        result = await kick_vote.cast_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)

        assert result == kick_vote.NO_ACTIVE_VOTE_ERROR
        assert game_room.active_kick_votes == {}

    async def test_a_late_vote_ends_the_expired_vote_for_everyone(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """A vote cast after the timeout is refused and every client is told the vote ended."""
        host_ws, *_ = await _fill_room(game_room, make_ws)
        await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)
        game_room.active_kick_votes[PLAYER_FOUR_ID].expires_at = time.time() - 1

        result = await kick_vote.cast_kick_vote(game_room, PLAYER_THREE_ID, PLAYER_FOUR_ID)

        assert result == kick_vote.VOTE_EXPIRED_ERROR
        assert PLAYER_FOUR_ID not in game_room.active_kick_votes
        assert PLAYER_FOUR_ID in game_room.players
        expired = json.loads(host_ws.sent_texts[-1])
        assert expired == {"type": KICK_VOTE_EXPIRED, "targetPlayerId": PLAYER_FOUR_ID}

    async def test_the_target_cannot_vote_against_themselves(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """The target's own vote is refused and does not move the tally."""
        host_ws, *_ = await _fill_room(game_room, make_ws)
        await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)

        result = await kick_vote.cast_kick_vote(game_room, PLAYER_FOUR_ID, PLAYER_FOUR_ID)

        assert result == kick_vote.SELF_VOTE_KICK_ERROR
        assert game_room.active_kick_votes[PLAYER_FOUR_ID].voters == {PLAYER_TWO_ID}
        assert KICK_VOTE_UPDATED not in _sent_types(host_ws)

    async def test_a_target_promoted_to_host_mid_vote_cannot_be_voted_out(
        self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """Host immunity holds when the target became host after the vote started."""
        await _fill_room(game_room, make_ws)
        await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)
        game_room.host_id = PLAYER_FOUR_ID  # as after a host transfer

        result = await kick_vote.cast_kick_vote(game_room, PLAYER_THREE_ID, PLAYER_FOUR_ID)

        assert result == HOST_CANNOT_BE_VOTE_KICKED_ERROR
        assert PLAYER_FOUR_ID in game_room.players
        assert game_room.active_kick_votes[PLAYER_FOUR_ID].voters == {PLAYER_TWO_ID}
