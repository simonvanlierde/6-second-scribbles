"""Benchmarks of scoring one guesser's submission, run for every guesser at the end of each round."""
# spell-checker: ignore elefant, girafe, tigger, elefante, elefantes, jirafa, jirafas, tigres, gato

from __future__ import annotations

from typing import TYPE_CHECKING

from app.scoring import GuessMatcher, GuessTarget

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

# A drawer's card, with the aliases and accents normalize_text and fuzzy_match handle.
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
    "a long guess matching nothing",
]
SPANISH_TARGETS = [
    GuessTarget(item_id=1, label="elefante", aliases=[]),
    GuessTarget(item_id=2, label="jirafa", aliases=[]),
    GuessTarget(item_id=3, label="tigre", aliases=[]),
]
SPANISH_GUESSES = ["elefantes", "jirafas", "tigres", "gato"]
MIN_ENGLISH_MATCHES = 5


def test_score_submission(benchmark: BenchmarkFixture) -> None:
    """Score a typical submission, with typos, plurals and an accent."""
    matched = benchmark(GuessMatcher().score_guesses_against_targets, GUESSES, TARGETS)

    assert len(matched) >= MIN_ENGLISH_MATCHES


def test_score_submission_with_spanish_plurals(benchmark: BenchmarkFixture) -> None:
    """Score with the guesser's own language rules for plurals."""
    matched = benchmark(GuessMatcher().score_guesses_against_targets, SPANISH_GUESSES, SPANISH_TARGETS, "es")

    assert len(matched) == len(SPANISH_TARGETS)


def test_score_largest_submission(benchmark: BenchmarkFixture) -> None:
    """Score the most guesses the protocol accepts (50), none of which match."""
    guesses = [f"{word} {i}" for i in range(10) for word in ("lion", "zebra", "rocket", "pizza", "castle")]

    benchmark(GuessMatcher().score_guesses_against_targets, guesses, TARGETS)
