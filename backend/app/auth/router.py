"""Authentication routes for guest, register, login, and logout flows."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Request, Response, status

from app.auth.dependencies import OptionalCurrentUserDep
from app.auth.schemas import GuestAuthRequest, LoginRequest, RegisterRequest
from app.auth.service import (
    create_guest_user,
    create_user_session,
    login_user,
    logout_session,
    register_user,
    to_user_response,
)
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


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


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


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    response: Response,
    http_request: Request,
    db: AsyncSessionDep,
    current_user: OptionalCurrentUserDep,
) -> UserResponse:
    """Register a new account or claim the current guest user."""
    await enforce_rate_limit(
        bucket="auth_register",
        identifier=f"{get_client_identifier(http_request)}:{request.username.lower()}",
        limit=settings.auth_register_rate_limit,
        window_seconds=settings.auth_register_rate_window_seconds,
    )
    user = await register_user(
        db,
        username=request.username,
        password=request.password,
        preferred_locale=request.preferred_locale,
        display_name=request.display_name,
        current_user=current_user,
    )
    session_id = await create_user_session(user)
    _set_session_cookie(response, session_id)
    return to_user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
    db: AsyncSessionDep,
) -> UserResponse:
    """Authenticate an existing user and start a new session."""
    await enforce_rate_limit(
        bucket="auth_login",
        identifier=f"{get_client_identifier(http_request)}:{request.username.lower()}",
        limit=settings.auth_login_rate_limit,
        window_seconds=settings.auth_login_rate_window_seconds,
    )
    user = await login_user(db, username=request.username, password=request.password)
    session_id = await create_user_session(user)
    _set_session_cookie(response, session_id)
    return to_user_response(user)


@router.post("/logout", status_code=204)
async def logout(
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> Response:
    """Logout the current session."""
    await logout_session(session_id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response
