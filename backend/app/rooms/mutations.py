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
    round_length: int | None,
) -> None:
    """Apply lobby/game settings updates to room metadata."""
    room.metadata.difficulty = difficulty or room.metadata.difficulty
    room.metadata.max_rounds = rounds or room.metadata.max_rounds
    room.metadata.round_length = round_length or room.metadata.round_length


def set_language(room: GameRoom, language: LanguageCode) -> None:
    """Update the room language."""
    room.metadata.language = language


def set_pad_visibility(room: GameRoom, *, visible: bool) -> None:
    """Update shared drawpad visibility."""
    room.metadata.pad_visibility = visible


def set_privacy(room: GameRoom, *, is_private: bool) -> None:
    """Update room privacy for random join visibility."""
    room.metadata.is_private = is_private
