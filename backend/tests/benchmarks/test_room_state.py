"""Benchmarks of the room snapshot that every Redis save writes and every restore reads."""
# spell-checker: ignore elefant, tigger

from __future__ import annotations

from typing import TYPE_CHECKING

from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState, RoomMetadataState, RoomState

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

PLAYER_IDS = [f"player-{i}" for i in range(8)]


def _mid_round_room() -> RoomState:
    """A full room in the guessing phase, with every card dealt and every guess in."""
    metadata = RoomMetadataState(
        game_phase="guessing",
        current_round=3,
        player_locales=dict.fromkeys(PLAYER_IDS, "en"),
        player_rejoin_keys=dict.fromkeys(PLAYER_IDS, "a" * 64),
        player_seats={player_id: i for i, player_id in enumerate(PLAYER_IDS)},
        player_scores={player_id: i * 2 for i, player_id in enumerate(PLAYER_IDS)},
        ready_players=set(PLAYER_IDS),
        player_assignments={
            player_id: PlayerPromptAssignmentState(
                category_id=7,
                category="Animals",
                item_ids=list(range(6)),
                items=["elephant", "giraffe", "tiger", "zebra", "lion", "monkey"],
                alternatives={"elephant": ["elefant"], "tiger": ["big cat"]},
            )
            for player_id in PLAYER_IDS
        },
        guess_targets={player_id: PLAYER_IDS[(i + 1) % len(PLAYER_IDS)] for i, player_id in enumerate(PLAYER_IDS)},
        guess_submissions=[
            GuessSubmissionState(
                player_id=player_id,
                target_player_id=PLAYER_IDS[(i + 1) % len(PLAYER_IDS)],
                guesses=["elephant", "giraffe", "tigger", "horse"],
                submitted_at=1_700_000_000_000 + i,
            )
            for i, player_id in enumerate(PLAYER_IDS)
        ],
        submitted_players=set(PLAYER_IDS),
    )
    return RoomState(room_id="ABCD", host_id=PLAYER_IDS[0], created_at=1_700_000_000.0, metadata=metadata)


def test_dump_room_state(benchmark: BenchmarkFixture) -> None:
    """Serialize a mid-round room for Redis."""
    room = _mid_round_room()

    payload = benchmark(room.model_dump_json)

    assert RoomState.model_validate_json(payload) == room


def test_load_room_state(benchmark: BenchmarkFixture) -> None:
    """Restore a mid-round room from Redis."""
    room = _mid_round_room()

    restored = benchmark(RoomState.model_validate_json, room.model_dump_json())

    assert restored == room
