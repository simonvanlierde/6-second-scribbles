"""Typed result models for room-domain flows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KickVoteResult(BaseModel):
    """Structured result returned from kick-vote actions."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    error: str | None = None
    immediate: bool = False
    reason: str | None = None
    vote_id: str | None = None
    vote_passed: bool | None = None
    current_votes: int | None = None
    required_votes: int | None = None
