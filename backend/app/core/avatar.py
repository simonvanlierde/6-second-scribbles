"""Avatar color tokens.

Must stay in sync with ``frontend/src/composables/useAvatar.ts`` AVATAR_COLORS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

AVATAR_COLOR_TOKENS: tuple[str, ...] = (
    "var(--avatar-1)",
    "var(--avatar-2)",
    "var(--avatar-3)",
    "var(--avatar-4)",
    "var(--avatar-5)",
    "var(--avatar-6)",
)


def pick_avatar_color(player_id: str, used_colors: Iterable[str]) -> str:
    """Pick an avatar color for a new player.

    Prefers tokens not currently used by another player in the room; if all
    six are taken, falls back to a deterministic choice based on the player id.
    """
    used = set(used_colors)
    for token in AVATAR_COLOR_TOKENS:
        if token not in used:
            return token
    idx = sum(ord(c) for c in player_id) % len(AVATAR_COLOR_TOKENS)
    return AVATAR_COLOR_TOKENS[idx]
