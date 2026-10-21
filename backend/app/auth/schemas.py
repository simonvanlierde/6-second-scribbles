"""HTTP schemas for auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GuestAuthRequest(BaseModel):
    """Optional request body for guest session bootstrap."""

    # Bounds match the DB columns (display_name String(80), preferred_locale
    # String(16)); without them an over-long value is a 500 on commit, not a 422.
    preferred_locale: str = Field(default="en", alias="preferredLocale", max_length=16)
    display_name: str | None = Field(default=None, alias="displayName", max_length=80)
