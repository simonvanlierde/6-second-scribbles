"""Tests for the room metadata model and its writers."""

import pytest

from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState, RoomMetadataState

LEAVER = "leaver"
STAYER = "stayer"
IDENTITY_FIELDS = {"player_user_ids", "player_rejoin_keys"}

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
