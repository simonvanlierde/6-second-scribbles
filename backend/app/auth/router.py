"""Authentication routes for guest sessions."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.auth.schemas import GuestAuthRequest
from app.auth.service import create_guest_user, create_user_session, to_user_response
from app.core.config import settings
from app.core.database import AsyncSessionDep
from app.core.rate_limits import enforce_rate_limit, get_client_identifier
from app.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_same_site,
        path="/",
    )


@router.post("/guest", response_model=UserResponse)
async def create_guest_auth_session(
    request: GuestAuthRequest,
    response: Response,
    http_request: Request,
    db: AsyncSessionDep,
) -> UserResponse:
    """Create a guest user and authenticated session."""
    await enforce_rate_limit(
        bucket="auth_guest",
        identifier=get_client_identifier(http_request),
        limit=settings.auth_guest_rate_limit,
        window_seconds=settings.auth_guest_rate_window_seconds,
    )
    user = await create_guest_user(
        db,
        preferred_locale=request.preferred_locale,
        display_name=request.display_name,
    )
    session_id = await create_user_session(user)
    _set_session_cookie(response, session_id)
    return to_user_response(user)
