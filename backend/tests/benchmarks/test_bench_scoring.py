"""Benchmarks for guess normalization and fuzzy matching (scored on every round)."""
# spell-checker: ignore elefant, girafe, tigger, cafe, jirafa, elefante, elefantes, jirafas, tigres, gato
# spell-checker: ignore Crème, ÉLÉPHANT, Жираф, résumé

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.scoring import GuessMatcher, GuessTarget, normalize_text

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

# A drawer's card holds a handful of prompts; guessers type up to a few guesses per prompt.
TARGETS = [
    GuessTarget(item_id=1, label="elephant", aliases=["elefant"]),
    GuessTarget(item_id=2, label="giraffe", aliases=[]),
    GuessTarget(item_id=3, label="tiger", aliases=["big cat"]),
    GuessTarget(item_id=4, label="new york city", aliases=["nyc", "new york"]),
    GuessTarget(item_id=5, label="ice cream cone", aliases=["ice cream"]),
    GuessTarget(item_id=6, label="café", aliases=["coffee shop"]),
]
GUESSES = [
    "elefant",
    "girafe",
    "tigger",
    "new york",
    "ice creams",
    "cafe",
    "submarine",
    "a very long guess that matches nothing at all",
]
SPANISH_TARGETS = [
    GuessTarget(item_id=1, label="elefante", aliases=[]),
    GuessTarget(item_id=2, label="jirafa", aliases=[]),
    GuessTarget(item_id=3, label="tigre", aliases=[]),
]
SPANISH_GUESSES = ["elefantes", "jirafas", "tigres", "gato"]


@pytest.fixture
def matcher() -> GuessMatcher:
    """A fresh matcher instance."""
    return GuessMatcher()


def test_normalize_text(benchmark: BenchmarkFixture) -> None:
    """Normalize a mix of accented, cased and non-Latin guesses."""
    texts = ["  Café Crème ", "ÉLÉPHANT", "Жираф", "大象", "naïve résumé", "Ice Cream Cone"]

    @benchmark
    def run() -> None:
        for text in texts:
            normalize_text(text)


def test_fuzzy_match_pairs(benchmark: BenchmarkFixture, matcher: GuessMatcher) -> None:
    """Fuzzy-match every guess against every target label."""

    @benchmark
    def run() -> None:
        for guess in GUESSES:
            for target in TARGETS:
                matcher.fuzzy_match(guess, target.label)


def test_score_guesses_against_targets(benchmark: BenchmarkFixture, matcher: GuessMatcher) -> None:
    """Score one guesser's full submission against a drawer's card."""
    matched = benchmark(matcher.score_guesses_against_targets, GUESSES, TARGETS)
    assert len(matched) >= 5


def test_score_guesses_spanish_locale(benchmark: BenchmarkFixture, matcher: GuessMatcher) -> None:
    """Score a submission with locale-aware plural handling."""
    matched = benchmark(matcher.score_guesses_against_targets, SPANISH_GUESSES, SPANISH_TARGETS, "es")
    assert len(matched) == 3


def test_score_max_submission(benchmark: BenchmarkFixture, matcher: GuessMatcher) -> None:
    """Worst case: the largest submission the protocol accepts (50 guesses)."""
    guesses = [f"{word} {i}" for i in range(10) for word in ("lion", "zebra", "rocket", "pizza", "castle")]
    benchmark(matcher.score_guesses_against_targets, guesses, TARGETS)
