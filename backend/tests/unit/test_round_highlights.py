"""Unit tests for per-round highlight computation."""

from __future__ import annotations

from app.rooms.protocol import RoundResultItem
from app.rooms.rounds import compute_highlights
from app.rooms.state import GuessSubmissionState

P1 = "p1"
P2 = "p2"
P3 = "p3"


def _result(player_id: str, correct: int, total: int) -> RoundResultItem:
    """Build a round result item for one guesser."""
    return RoundResultItem(
        playerId=player_id,
        targetPlayerId="target",
        correctGuesses=correct,
        totalItems=total,
        pointsEarned=correct * 10,
    )


def _submission(player_id: str, guesses: list[str], submitted_at: int) -> GuessSubmissionState:
    """Build a guess submission with an explicit submission timestamp."""
    return GuessSubmissionState(
        player_id=player_id,
        target_player_id="target",
        guesses=guesses,
        submitted_at=submitted_at,
    )


def test_no_submissions_returns_none() -> None:
    """A round with no submissions has no highlights."""
    assert compute_highlights([], [], []) is None


def test_best_guesser_picks_highest_ratio() -> None:
    """The best guesser is the player with the highest correct/total ratio."""
    results = [_result(P1, 1, 4), _result(P2, 3, 4)]
    highlights = compute_highlights(results, [_submission(P1, ["a"], 1)], [])
    assert highlights is not None
    expected_detail = "3/4"
    best = highlights.best_guesser
    assert best is not None
    assert best.player_id == P2
    assert best.detail == expected_detail


def test_best_guesser_tie_breaks_on_correct_count() -> None:
    """When ratios tie, the player with more correct guesses wins."""
    results = [_result(P1, 1, 2), _result(P2, 2, 4)]  # both 0.5
    highlights = compute_highlights(results, [_submission(P1, ["a"], 1)], [])
    assert highlights is not None
    expected_detail = "2/4"
    best = highlights.best_guesser
    assert best is not None
    assert best.player_id == P2
    assert best.detail == expected_detail


def test_best_guesser_requires_at_least_one_correct() -> None:
    """A player who got nothing right is never the best guesser."""
    results = [_result(P1, 0, 4)]
    highlights = compute_highlights(results, [_submission(P1, ["a"], 1)], [])
    assert highlights is not None  # speed demon still present
    assert highlights.best_guesser is None


def test_speed_demon_is_earliest_non_empty_submission() -> None:
    """The speed demon is the earliest submission with a non-empty guess set."""
    submissions = [
        _submission(P1, ["a"], 500),
        _submission(P2, ["b"], 100),
        _submission(P3, [], 50),  # empty guesses are ignored
    ]
    highlights = compute_highlights([], submissions, [])
    assert highlights is not None
    assert highlights.speed_demon is not None
    assert highlights.speed_demon.player_id == P2


def test_speed_demon_ignores_blank_guesses_and_zero_timestamp() -> None:
    """Blank guesses and unset timestamps cannot win speed demon."""
    submissions = [_submission(P1, ["   "], 100), _submission(P2, ["x"], 0)]
    assert compute_highlights([], submissions, []) is None


def test_wildest_miss_picks_max_distance() -> None:
    """The wildest miss is the guess furthest from any target item."""
    submissions = [_submission(P1, ["x"], 1)]
    miss_candidates = [(P1, "banana", 30.0), (P2, "zzz", 95.0)]
    highlights = compute_highlights([], submissions, miss_candidates)
    assert highlights is not None
    miss = highlights.wildest_miss
    assert miss is not None
    assert miss.player_id == P2
    assert miss.detail == miss_candidates[1][1]
