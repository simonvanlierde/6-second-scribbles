"""Fuzzy matching and scoring logic for guess validation.

Uses rapidfuzz for high-performance fuzzy string matching.
"""

from __future__ import annotations

__all__ = [
    "GuessMatchDetailResult",
    "GuessMatchResult",
    "GuessMatcher",
    "GuessTarget",
    "ScoreGuessesResult",
    "guess_matcher",
    "normalize_text",
]

import functools
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from rapidfuzz import fuzz

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


@dataclass(frozen=True)
class GuessTarget:
    """One canonical guess target with its localized accepted answers."""

    item_id: int
    label: str
    aliases: list[str]


def normalize_text(text: str) -> str:
    """Normalize text for comparison: casefold, strip, remove accents.

    Strips combining marks (accents) so ``café`` matches ``cafe``, but preserves
    the base characters of every script. The previous ``encode("ascii", "ignore")``
    dropped all non-Latin text to an empty string, making Cyrillic/CJK/Greek/Arabic
    answers permanently unscoreable.
    """
    decomposed = unicodedata.normalize("NFD", text.casefold().strip())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", without_marks)


@functools.lru_cache(maxsize=1024)
def _generate_variants(normalized: str) -> frozenset[str]:
    """Generate common plural/verb variants of a normalized word."""
    variants = {normalized}

    if normalized.endswith("s"):
        variants.add(normalized[:-1])
        if normalized.endswith("es"):
            variants.add(normalized[:-2])
    else:
        variants.add(f"{normalized}s")
        variants.add(f"{normalized}es")

    if normalized.endswith("ing"):
        variants.add(normalized[:-3])

    return frozenset(variants)


class GuessMatcher:
    """Handles fuzzy matching of player guesses against correct answers."""

    FUZZY_MATCH_THRESHOLD = 85

    def exact_match(self, guess: str, target: str) -> bool:
        """Check if guess exactly matches target."""
        return bool(_generate_variants(normalize_text(guess)) & _generate_variants(normalize_text(target)))

    def fuzzy_match(self, guess: str, target: str) -> tuple[bool, float]:
        """Check if guess fuzzy matches target."""
        guess_norm = normalize_text(guess)
        target_norm = normalize_text(target)

        if self.exact_match(guess, target):
            return True, 100.0

        token_score = fuzz.token_sort_ratio(guess_norm, target_norm)
        partial_score = fuzz.partial_ratio(guess_norm, target_norm)
        similarity = max(token_score, partial_score)
        return similarity >= self.FUZZY_MATCH_THRESHOLD, similarity

    def match_guess(
        self,
        guess: str,
        correct_answers: list[str],
        alternatives: list[str] | None = None,
    ) -> GuessMatchResult:
        """Match a guess against a list of correct answers."""
        if not normalize_text(guess):
            return GuessMatchResult(matched=False, matched_item=None, similarity=0.0, method="none")

        for answer in correct_answers:
            if self.exact_match(guess, answer):
                return GuessMatchResult(matched=True, matched_item=answer, similarity=100.0, method="exact")

        if alternatives:
            for alt in alternatives:
                if self.exact_match(guess, alt):
                    return GuessMatchResult(matched=True, matched_item=alt, similarity=100.0, method="alternative")

        best_match = None
        best_score = 0.0
        best_item = None

        for answer in correct_answers:
            is_match, score = self.fuzzy_match(guess, answer)
            if score > best_score:
                best_score = score
                best_match = is_match
                best_item = answer

        if best_match:
            return GuessMatchResult(matched=True, matched_item=best_item, similarity=best_score, method="fuzzy")

        return GuessMatchResult(matched=False, matched_item=None, similarity=best_score, method="none")

    def score_guesses_against_targets(
        self,
        guesses: list[str],
        targets: list[GuessTarget],
    ) -> ScoreGuessesResult:
        """Score guesses against canonical item targets with localized labels and aliases."""
        matched_item_ids: set[int] = set()
        match_details: list[GuessMatchDetailResult] = []

        for guess in guesses:
            best_target: GuessTarget | None = None
            best_result: GuessMatchResult | None = None

            for target in targets:
                if target.item_id in matched_item_ids:
                    continue

                result = self.match_guess(guess, [target.label], target.aliases)
                if not result.matched:
                    continue

                if best_result is None or result.similarity > best_result.similarity:
                    best_target = target
                    best_result = result

            if best_target is None or best_result is None:
                continue

            matched_item_ids.add(best_target.item_id)
            match_details.append(
                GuessMatchDetailResult(
                    guess=guess,
                    matched_item=best_target.label,
                    similarity=best_result.similarity,
                    method=best_result.method,
                )
            )

        unmatched_answers = [target.label for target in targets if target.item_id not in matched_item_ids]
        total = len(targets)

        return ScoreGuessesResult(
            score=len(matched_item_ids),
            total=total,
            percentage=(len(matched_item_ids) / total * 100) if total else 0,
            matches=match_details,
            unmatched_answers=unmatched_answers,
        )


guess_matcher = GuessMatcher()
