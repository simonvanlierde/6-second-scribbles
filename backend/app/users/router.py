"""Routes for the authenticated current user."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUserDep
from app.auth.service import to_user_response
from app.users.schemas import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    """Return the current authenticated user."""
    return to_user_response(current_user)
