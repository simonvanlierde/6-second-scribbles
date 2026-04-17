"""Routes for the authenticated current user."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUserDep
from app.core.database import AsyncSessionDep
from app.users.schemas import UpdatePreferencesRequest, UserResponse

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


@router.patch("/me/preferences", response_model=UserResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: CurrentUserDep,
    db: AsyncSessionDep,
) -> UserResponse:
    """Update the current user's basic profile preferences."""
    if request.preferred_locale is not None:
        current_user.preferred_locale = request.preferred_locale
    if request.display_name is not None:
        current_user.display_name = request.display_name

    await db.commit()

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        displayName=current_user.display_name,
        preferredLocale=current_user.preferred_locale,
        isGuest=current_user.password_hash is None,
    )
