"""HTTP schemas for auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GuestAuthRequest(BaseModel):
    """Optional request body for guest session bootstrap."""

    preferred_locale: str = Field(default="en", alias="preferredLocale")
    display_name: str | None = Field(default=None, alias="displayName")


class RegisterRequest(BaseModel):
    """Request body for account registration."""

    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    preferred_locale: str = Field(default="en", alias="preferredLocale")
    display_name: str | None = Field(default=None, alias="displayName")


class LoginRequest(BaseModel):
    """Request body for username/password login."""

    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
