"""Tests for the room metadata model and its writers."""

import pytest

from app.core.types import GamePhase
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState, RoomMetadataState

LEAVER = "leaver"
STAYER = "stayer"
IDENTITY_FIELDS = {"player_user_ids", "player_rejoin_keys", "player_departed_at"}

FIELD_GROUPS = (
    RoomMetadataState.SEAT_FIELDS,
    RoomMetadataState.ROUND_FIELDS,
    RoomMetadataState.GAME_FIELDS,
    RoomMetadataState.SETTINGS_FIELDS,
)


def test_every_field_is_in_exactly_one_group() -> None:
    """A new field fails here until it is classified, so its reset rule is a decision."""
    for name in RoomMetadataState.model_fields:
        groups = [group for group in FIELD_GROUPS if name in group]
        assert len(groups) == 1, f"{name} is in {len(groups)} field groups"
    assert set().union(*FIELD_GROUPS) == set(RoomMetadataState.model_fields)


def _metadata_with_both_players() -> RoomMetadataState:
    """Metadata with every player-keyed field filled for LEAVER and STAYER."""
    card = PlayerPromptAssignmentState(category="Pets", items=["cat"])
    return RoomMetadataState(
        ready_players={LEAVER, STAYER},
        player_locales={LEAVER: "en", STAYER: "nl"},
        player_user_ids={LEAVER: "user-leaver", STAYER: "user-stayer"},
        player_rejoin_keys={LEAVER: "a" * 64, STAYER: "b" * 64},
        player_assignments={LEAVER: card, STAYER: card},
        guess_targets={LEAVER: STAYER, STAYER: LEAVER},
        guess_submissions=[GuessSubmissionState(player_id=LEAVER, target_player_id=STAYER, guesses=["cat"])],
        submitted_players={LEAVER, STAYER},
        player_scores={LEAVER: 10, STAYER: 20},
        player_seats={LEAVER: 0, STAYER: 1},
        player_departed_at={LEAVER: 1.0, STAYER: 1.0},
    )


@pytest.mark.parametrize("forget_identity", [True, False])
def test_forget_player_leaves_no_seat_or_round_trace(*, forget_identity: bool) -> None:
    """Every keyed seat or round field drops the player; a new keyed field must be handled too."""
    metadata = _metadata_with_both_players()
    metadata.forget_player(LEAVER, forget_identity=forget_identity)

    kept = set() if forget_identity else IDENTITY_FIELDS
    for name in RoomMetadataState.SEAT_FIELDS | RoomMetadataState.ROUND_FIELDS:
        value = getattr(metadata, name)
        if not isinstance(value, dict | set):
            continue
        assert (LEAVER in value) == (name in kept), name
        assert STAYER in value, name
    # Values that name the leaver are a record of the round, not their seat:
    # the stayer still guesses the leaver's drawing, and the leaver's guess
    # still credits the stayer.
    assert metadata.guess_targets == {STAYER: LEAVER}
    assert [s.player_id for s in metadata.guess_submissions] == [LEAVER]
    assert metadata.player_scores == {LEAVER: 10, STAYER: 20}


def _mid_game_metadata() -> RoomMetadataState:
    """Metadata in the middle of a guessing round with non-default settings."""
    metadata = _metadata_with_both_players()
    metadata.game_phase = GamePhase.GUESSING
    metadata.current_round = 2
    metadata.round_start_time = 1_700_000_000_000
    metadata.guessing_start_time = 1_700_000_030_000
    metadata.max_rounds = 3
    metadata.is_private = True
    return metadata


def _fields(metadata: RoomMetadataState, names: frozenset[str]) -> dict[str, object]:
    return {name: getattr(metadata, name) for name in names}


def test_reset_round_clears_only_round_fields() -> None:
    """Every round field goes back to its default; the cards become the new prompts."""
    metadata = _mid_game_metadata()
    before = metadata.model_copy(deep=True)
    cards = {STAYER: PlayerPromptAssignmentState(category="Food", items=["pie"])}

    metadata.reset_round(cards=cards)

    defaults = RoomMetadataState()
    expected = _fields(defaults, RoomMetadataState.ROUND_FIELDS) | {"player_assignments": cards}
    assert _fields(metadata, RoomMetadataState.ROUND_FIELDS) == expected
    others = RoomMetadataState.SEAT_FIELDS | RoomMetadataState.GAME_FIELDS | RoomMetadataState.SETTINGS_FIELDS
    assert _fields(metadata, others) == _fields(before, others)


def test_reset_game_starts_scores_at_zero_for_the_given_players() -> None:
    """Round and game fields reset; earlier scores, also of players who left, are dropped."""
    metadata = _mid_game_metadata()
    metadata.player_scores["departed"] = 30
    before = metadata.model_copy(deep=True)

    metadata.reset_game([LEAVER, STAYER])

    defaults = RoomMetadataState()
    reset = RoomMetadataState.ROUND_FIELDS | RoomMetadataState.GAME_FIELDS
    expected = _fields(defaults, reset) | {"player_scores": {LEAVER: 0, STAYER: 0}}
    assert _fields(metadata, reset) == expected
    kept = RoomMetadataState.SEAT_FIELDS | RoomMetadataState.SETTINGS_FIELDS
    assert _fields(metadata, kept) == _fields(before, kept)
