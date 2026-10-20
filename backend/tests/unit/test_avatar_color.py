"""Avatar colour picker tests."""

from __future__ import annotations

from app.core.avatar import AVATAR_COLOR_TOKENS, pick_avatar_color
from app.rooms import player_lifecycle
from app.rooms.manager import GameRoom
from tests.support import TestWebSocket, as_websocket


def test_avatar_color_tokens_length() -> None:
    """There are exactly six avatar colour tokens."""
    assert len(AVATAR_COLOR_TOKENS) == 6


def test_avatar_color_tokens_unique() -> None:
    """No two avatar tokens resolve to the same value."""
    assert len(set(AVATAR_COLOR_TOKENS)) == len(AVATAR_COLOR_TOKENS)


def test_pick_returns_unused_token_first() -> None:
    """The picker prefers a colour not already used in the room."""
    used = [AVATAR_COLOR_TOKENS[0], AVATAR_COLOR_TOKENS[1]]
    picked = pick_avatar_color("player-abc", used)
    assert picked == AVATAR_COLOR_TOKENS[2]


def test_pick_is_deterministic_when_all_used() -> None:
    """The fallback colour is deterministic for the same player id."""
    used = list(AVATAR_COLOR_TOKENS)
    first = pick_avatar_color("player-abc", used)
    second = pick_avatar_color("player-abc", used)
    assert first == second
    assert first in AVATAR_COLOR_TOKENS


def test_pick_reuses_palette_when_all_used() -> None:
    """Once all tokens are taken, the picker reuses one from the palette."""
    used = list(AVATAR_COLOR_TOKENS)
    picked = pick_avatar_color("player-abc", used)
    assert picked in AVATAR_COLOR_TOKENS


async def test_players_without_a_picked_colour_get_different_colours() -> None:
    """The server hands each player who picked nothing a colour no one else in the room has."""
    room = GameRoom("COLOR1")
    first, _ = await player_lifecycle.add_player(room, "p1", "Ann", as_websocket(TestWebSocket()))
    second, _ = await player_lifecycle.add_player(room, "p2", "Bob", as_websocket(TestWebSocket()))

    assert first.color != second.color


async def test_a_picked_colour_is_kept_only_while_free() -> None:
    """A picked colour is used when free; a second player picking it gets another one."""
    room = GameRoom("COLOR2")
    picked = AVATAR_COLOR_TOKENS[2]
    first, _ = await player_lifecycle.add_player(
        room, "p1", "Ann", as_websocket(TestWebSocket()), preferred_color=picked
    )
    second, _ = await player_lifecycle.add_player(
        room, "p2", "Bob", as_websocket(TestWebSocket()), preferred_color=picked
    )

    assert first.color == picked
    assert second.color != picked
