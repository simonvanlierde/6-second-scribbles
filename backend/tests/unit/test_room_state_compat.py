"""A room saved before the metadata writers moved onto RoomMetadataState still loads and plays."""

import json
from typing import TYPE_CHECKING

import pytest

from app.core.types import GamePhase
from app.rooms.manager import GameRoom
from app.rooms.player_lifecycle import IDENTITY_CONFLICT_ERROR
from app.rooms.state import RoomState
from tests.support import as_websocket

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support import TestWebSocket

HOST = "p1"
GUEST = "p2"
HOST_CATEGORY = "Pets"

# Saved with RoomState.model_dump_json() by the code before the change. Rooms
# outlive deploys and rollbacks, so this exact JSON must keep loading.
SAVED_ROOM = """
{
  "room_id": "FIXTURE",
  "host_id": "p1",
  "last_host_id": "p1",
  "created_at": 1700000000.0,
  "emptied_at": null,
  "is_hibernated": false,
  "metadata": {
    "game_phase": "guessing",
    "round_start_time": 1700000000000,
    "guessing_start_time": 1700000030000,
    "drawing_time_limit": 30,
    "guessing_time_limit": 45,
    "difficulty": "hard",
    "max_rounds": 3,
    "current_round": 2,
    "pad_visibility": false,
    "ready_players": [
      "p2"
    ],
    "is_private": true,
    "default_locale": "nl",
    "player_locales": {
      "p1": "en",
      "p2": "nl"
    },
    "player_user_ids": {
      "p1": "user-1"
    },
    "player_rejoin_keys": {
      "p1": "7ad27eea60ceba5f24ce706ab14202721fe5c1d3a9082ebdede0b639e535a1bc",
      "p2": "1c2f6c25015958693661611c5ea0dc992a9ae37ff8bc1ef2d5ee5a78a28ccc4c"
    },
    "custom_category_ids": [
      3,
      7
    ],
    "player_assignments": {
      "p1": {
        "category_id": 7,
        "category": "Pets",
        "item_ids": [
          1,
          2
        ],
        "items": [
          "cat",
          "dog"
        ],
        "alternatives": {
          "cat": [
            "kitten"
          ]
        }
      },
      "p2": {
        "category_id": 7,
        "category": "Animals",
        "item_ids": [
          1,
          2
        ],
        "items": [
          "cat",
          "dog"
        ],
        "alternatives": {
          "cat": [
            "kitten"
          ]
        }
      }
    },
    "guess_targets": {
      "p1": "p2",
      "p2": "p1"
    },
    "guess_submissions": [
      {
        "player_id": "p1",
        "target_player_id": "p2",
        "guesses": [
          "cat"
        ],
        "submitted_at": 1700000040000
      }
    ],
    "submitted_players": [
      "p1"
    ],
    "player_scores": {
      "p1": 20,
      "p2": 10,
      "p3": 5
    },
    "player_seats": {
      "p1": 0,
      "p2": 1
    }
  }
}
"""


def test_saved_room_round_trips_to_the_same_json() -> None:
    """Loading and saving again gives back the same JSON, so a rollback can read it."""
    state = RoomState.model_validate_json(SAVED_ROOM)
    assert json.loads(state.model_dump_json()) == json.loads(SAVED_ROOM)


async def test_saved_room_restores_and_plays(make_ws: Callable[..., TestWebSocket]) -> None:
    """A restored room keeps seats, identity, cards and scores, and the new writers work on it."""
    room = GameRoom.from_state(RoomState.model_validate_json(SAVED_ROOM))
    card = room.room_state_event(for_player_id=HOST).card
    assert card is not None
    assert card.category == HOST_CATEGORY

    await room.add_player(HOST, "Al", as_websocket(make_ws()), user_id="user-1", rejoin_key="key-p1")
    with pytest.raises(ValueError, match=IDENTITY_CONFLICT_ERROR):
        await room.add_player(GUEST, "Bo", as_websocket(make_ws()), rejoin_key="wrong")
    await room.add_player(GUEST, "Bo", as_websocket(make_ws()), rejoin_key="key-p2")
    assert room.host_id == HOST
    assert room.metadata.player_seats == {HOST: 0, GUEST: 1}

    await room.remove_player(GUEST, forget_identity=True)
    assert GUEST not in room.metadata.player_assignments
    assert GUEST not in room.metadata.player_rejoin_keys
    assert room.metadata.player_scores[GUEST] == 10

    room.reset_game()
    assert room.metadata.game_phase == GamePhase.LOBBY
    assert room.metadata.player_scores == {HOST: 0}
    assert room.metadata.is_private
