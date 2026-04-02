"""Shared request and response models for HTTP API routes."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain_types import Difficulty, GamePhase, LanguageCode  # noqa: TC001 - used by Pydantic at runtime
from app.result_models import MatchMethod  # noqa: TC001 - used by Pydantic at runtime


class GuessRequest(BaseModel):
    """Request body for scoring player guesses."""

    guesses: list[str]
    correct_answers: list[str]
    alternatives: dict[str, list[str]] = Field(default_factory=dict)


class GuessMatchDetail(BaseModel):
    """A single guess-to-answer match result."""

    guess: str
    matched_item: str
    similarity: float
    method: MatchMethod


class GuessResponse(BaseModel):
    """Response body for scoring player guesses."""

    score: int
    total: int
    percentage: float
    matches: list[GuessMatchDetail]
    unmatched_answers: list[str]


class ApiStatusResponse(BaseModel):
    """Generic status response for health and stats endpoints."""

    status: str


class AppInfoResponse(ApiStatusResponse):
    """Root endpoint response."""

    service: str
    version: str


class StatsResponse(ApiStatusResponse):
    """Server statistics response."""

    total_rooms: int
    active_rooms: int
    hibernated_rooms: int
    empty_rooms: int
    total_players: int


class RandomRoomResponse(BaseModel):
    """Response for finding a random joinable room."""

    room_code: str
    player_count: int
    max_players: int


class CategorySummary(BaseModel):
    """Compact category representation used by list endpoints."""

    id: int
    name: str
    difficulty: Difficulty
    description: str | None
    language: LanguageCode | None
    room_id: str | None
    created_by: str | None
    is_custom: bool


class CardResponse(BaseModel):
    """Card representation returned from category detail endpoints."""

    id: int
    category_id: int
    item: str
    alternatives: list[str]


class CategoriesResponse(BaseModel):
    """Response for listing categories."""

    categories: list[CategorySummary]
    count: int


class CategoryDetailResponse(BaseModel):
    """Response for a single category and its cards."""

    category: CategorySummary
    items: list[str]
    cards: list[CardResponse]


class RandomCategoryCardSet(BaseModel):
    """Cards selected for a single player/category pairing."""

    category: str
    items: list[str]
    alternatives: dict[str, list[str]]
    is_custom: bool


class RandomCardsResponse(BaseModel):
    """Response for the random card selection endpoint."""

    difficulty: Difficulty
    categories: dict[int, RandomCategoryCardSet]
    includes_custom: bool


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
