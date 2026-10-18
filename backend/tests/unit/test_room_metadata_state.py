"""Tests for the room metadata model and its writers."""

from app.rooms.state import RoomMetadataState

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
