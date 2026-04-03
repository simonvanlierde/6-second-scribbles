"""HTTP schemas for the rooms domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.categories.schemas import CategorySummary
from app.core.types import Difficulty, GamePhase  # noqa: TC001 - used by Pydantic at runtime

if TYPE_CHECKING:
    from app.categories.models import Category


class RandomRoomResponse(BaseModel):
    """Response for finding a random joinable room."""

    room_code: str
    player_count: int
    max_players: int


class CustomCategoryCreate(BaseModel):
    """Request body for creating a room-specific category."""

    name: str
    items: list[str]
    difficulty: Difficulty = "medium"
    description: str | None = None
    created_by: str


class CustomCategoryCreateResponse(BaseModel):
    """Response after creating a room-specific category."""

    success: bool
    category: CategorySummary
    message: str


class RoomCategoriesItem(CategorySummary):
    """Category response augmented with items for a room."""

    items: list[str]

    @classmethod
    def from_model(cls, category: Category, *, items: list[str]) -> RoomCategoriesItem:  # ty: ignore[invalid-method-override]
        """Build a room-category response item from a Category ORM instance."""
        return cls(
            **CategorySummary.from_model(category).model_dump(),
            items=items,
        )


class RoomCategoriesResponse(BaseModel):
    """Response for listing custom categories in a room."""

    room_id: str
    categories: list[RoomCategoriesItem]
    count: int


class DeleteCustomCategoryResponse(BaseModel):
    """Response after deleting a room-specific category."""

    success: bool
    message: str


class RoomStatusResponse(BaseModel):
    """Response for room status checks."""

    exists: bool
    players: int | None = None
    game_phase: GamePhase | None = None
