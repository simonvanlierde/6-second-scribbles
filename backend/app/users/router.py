"""Routes for the authenticated current user."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUserDep
from app.users.schemas import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    """Return the current authenticated user."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        displayName=current_user.display_name,
        preferredLocale=current_user.preferred_locale,
        isGuest=current_user.password_hash is None,
    )
