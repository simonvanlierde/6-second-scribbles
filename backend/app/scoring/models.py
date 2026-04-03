"""Typed result models for scoring flows."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type MatchMethod = Literal["exact", "fuzzy", "alternative", "none"]


class GuessMatchResult(BaseModel):
    """Result of matching one guess against the accepted answers."""

    model_config = ConfigDict(extra="forbid")

    matched: bool
    matched_item: str | None
    similarity: float
    method: MatchMethod


class GuessMatchDetailResult(BaseModel):
    """Detailed scoring information for a matched guess."""

    model_config = ConfigDict(extra="forbid")

    guess: str
    matched_item: str
    similarity: float
    method: MatchMethod


class ScoreGuessesResult(BaseModel):
    """Aggregate scoring result for a set of guesses."""

    model_config = ConfigDict(extra="forbid")

    score: int
    total: int
    percentage: float
    matches: list[GuessMatchDetailResult] = Field(default_factory=list)
    unmatched_answers: list[str] = Field(default_factory=list)
