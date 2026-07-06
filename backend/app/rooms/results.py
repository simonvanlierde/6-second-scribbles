"""Typed result models for room-domain flows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KickVoteResult(BaseModel):
    """Structured result returned from kick-vote actions."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    error: str | None = None
