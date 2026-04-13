"""HTTP schemas for users and session-backed auth responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Public user payload for the current authenticated session."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    username: str
    display_name: str | None = Field(alias="displayName")
    preferred_locale: str = Field(alias="preferredLocale")
    is_guest: bool = Field(alias="isGuest")


class UpdatePreferencesRequest(BaseModel):
    """Request body for updating user preferences."""

    preferred_locale: str | None = Field(default=None, alias="preferredLocale")
    display_name: str | None = Field(default=None, alias="displayName")
