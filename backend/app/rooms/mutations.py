"""Helpers for mutating shared room metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.types import Difficulty, LanguageCode
    from app.rooms.manager import GameRoom


def apply_settings_update(
    room: GameRoom,
    *,
    difficulty: Difficulty | None,
    rounds: int | None,
    drawing_time_limit: int | None,
    guessing_time_limit: int | None = None,
) -> None:
    """Apply lobby/game settings updates to room metadata."""
    room.metadata.difficulty = difficulty or room.metadata.difficulty
    room.metadata.max_rounds = rounds or room.metadata.max_rounds
    room.metadata.drawing_time_limit = drawing_time_limit or room.metadata.drawing_time_limit
    room.metadata.guessing_time_limit = guessing_time_limit or room.metadata.guessing_time_limit


def set_default_locale(room: GameRoom, locale: LanguageCode) -> None:
    """Update the room's default locale."""
    room.metadata.default_locale = locale


def set_pad_visibility(room: GameRoom, *, visible: bool) -> None:
    """Update shared drawpad visibility."""
    room.metadata.pad_visibility = visible


def set_privacy(room: GameRoom, *, is_private: bool) -> None:
    """Update room privacy for random join visibility."""
    room.metadata.is_private = is_private


def set_custom_category_ids(room: GameRoom, *, category_ids: list[int] | None) -> None:
    """Set explicit room-level private category selection or clear back to host defaults."""
    if category_ids is None:
        room.metadata.custom_category_ids = None
        return

    room.metadata.custom_category_ids = sorted(set(category_ids))
