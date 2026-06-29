"""Round state and scoring helpers for game rooms."""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING

from app.categories import service as category_service
from app.core.types import GamePhase
from app.rooms.protocol import (
    GameCompleteServerEvent,
    ReadyStatusEvent,
    RoundCompleteServerEvent,
    RoundHighlight,
    RoundHighlights,
    RoundResultItem,
    StartGuessingEvent,
)
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from app.scoring import GuessTarget, guess_matcher

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.types import Difficulty
    from app.rooms.manager import GameRoom

logger = logging.getLogger(__name__)

POINTS_PER_CORRECT_GUESS = 10


def _build_round_result_item(
    *,
    player_id: str,
    target_player_id: str,
    correct_guesses: int,
    total_items: int,
    points_earned: int,
) -> RoundResultItem:
    """Build a typed round result item."""
    return RoundResultItem(
        playerId=player_id,
        targetPlayerId=target_player_id,
        correctGuesses=correct_guesses,
        totalItems=total_items,
        pointsEarned=points_earned,
    )


def configure_game(
    room: GameRoom,
    *,
    drawing_time_limit: int | None,
    guessing_time_limit: int | None,
    difficulty: Difficulty | None,
    max_rounds: int | None,
) -> None:
    """Initialize a new game from the lobby state."""
    room.metadata.drawing_time_limit = drawing_time_limit
    room.metadata.guessing_time_limit = guessing_time_limit or 60
    room.metadata.difficulty = difficulty or room.metadata.difficulty
    room.metadata.max_rounds = max_rounds or 5
    room.metadata.game_phase = GamePhase.LOBBY
    room.metadata.current_round = 0
    room.metadata.round_start_time = None
    room.metadata.player_assignments = {}
    room.metadata.guess_targets = {}
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    room.metadata.player_scores = dict.fromkeys(room.players, 0)
    room.metadata.ready_players.clear()
    room.round_drawings.clear()
    room.drawing_history.clear()


def start_round(
    room: GameRoom,
    *,
    round_number: int | None,
    cards: dict[str, PlayerPromptAssignmentState] | None,
) -> int:
    """Transition the room into a new drawing round and return the start timestamp."""
    round_start_time = int(time.time() * 1000)
    room.metadata.round_start_time = round_start_time
    room.metadata.guessing_start_time = None
    room.metadata.game_phase = GamePhase.DRAWING
    room.metadata.current_round = round_number or (room.metadata.current_round + 1)
    room.metadata.player_assignments = cards or {}
    room.metadata.guess_targets = {}
    room.round_drawings.clear()
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    for player_id in room.players:
        room.metadata.player_scores.setdefault(player_id, 0)
    room.metadata.ready_players.clear()
    return round_start_time


def start_guessing(room: GameRoom) -> int:
    """Transition into the guessing phase and return the scoring timeout.

    Idempotent: if the room is already guessing (e.g. the fallback scheduler
    fires after an early all-ready transition), do not re-assign guess targets
    or reset counters — doing so would invalidate in-flight submissions.
    """
    if room.metadata.game_phase == GamePhase.GUESSING:
        return room.metadata.guessing_time_limit or 60
    room.metadata.guessing_start_time = int(time.time() * 1000)
    room.metadata.game_phase = GamePhase.GUESSING
    # Only connected players take part in guessing; a disconnected player should
    # not be assigned a (possibly blank) drawing to guess, nor be expected to submit.
    room.metadata.guess_targets = assign_guess_targets(
        [player_id for player_id, player in room.players.items() if player.connected],
    )
    room.metadata.ready_players.clear()
    return room.metadata.guessing_time_limit or 60


def expected_guessers(room: GameRoom) -> list[str]:
    """Connected players who have a target this round (i.e. are expected to submit)."""
    return [
        player_id
        for player_id, player in room.players.items()
        if player.connected and player_id in room.metadata.guess_targets
    ]


def all_expected_guesses_submitted(room: GameRoom) -> bool:
    """Whether every currently-connected player with a target has submitted.

    Computed live from current membership rather than a mutable counter, so it
    stays correct across mid-guessing disconnects and reconnects.
    """
    expected = expected_guessers(room)
    return bool(expected) and all(player_id in room.metadata.submitted_players for player_id in expected)


def all_connected_players_ready(room: GameRoom) -> bool:
    """Whether every connected player has marked ready (and at least one is connected).

    Used for the early drawing->guessing transition; computed over connected
    players so a mid-drawing disconnect does not stall the room.
    """
    connected = [player_id for player_id, player in room.players.items() if player.connected]
    return bool(connected) and all(player_id in room.metadata.ready_players for player_id in connected)


def start_guessing_event(room: GameRoom) -> StartGuessingEvent:
    """Transition into guessing and return the broadcast event."""
    start_guessing(room)
    return StartGuessingEvent(
        type="start_guessing",
        guessing_start_time=room.metadata.guessing_start_time,
        guessTargets=dict(room.metadata.guess_targets),
    )


def reset_game(room: GameRoom) -> None:
    """Reset mutable game state back to the lobby."""
    room.metadata.player_scores = {}
    room.metadata.current_round = 0
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    room.metadata.player_assignments = {}
    room.metadata.guess_targets = {}
    room.metadata.ready_players.clear()
    room.metadata.round_start_time = None
    room.metadata.guessing_start_time = None
    room.metadata.game_phase = GamePhase.LOBBY
    room.round_drawings.clear()
    room.drawing_history.clear()


def mark_player_ready(room: GameRoom, player_id: str) -> ReadyStatusEvent:
    """Record that a player is ready and return the shared ready-status payload."""
    room.metadata.ready_players.add(player_id)
    return ReadyStatusEvent(
        readyCount=len(room.metadata.ready_players),
        totalPlayers=len(room.players),
    )


def record_guess_submission(room: GameRoom, *, player_id: str, target_player_id: str, guesses: list[str]) -> bool:
    """Store a guess submission and report whether scoring should begin immediately."""
    assigned_target = room.metadata.guess_targets.get(player_id)
    if assigned_target != target_player_id:
        logger.warning(
            "[GameRoom %s] Player %s submitted guesses for unexpected target %s (assigned: %s)",
            room.room_id,
            player_id,
            target_player_id,
            assigned_target,
        )
        return False

    submission = GuessSubmissionState(
        player_id=player_id,
        target_player_id=target_player_id,
        guesses=guesses,
        submitted_at=int(time.time() * 1000),
    )
    room.metadata.guess_submissions.append(submission)
    room.metadata.submitted_players.add(player_id)
    logger.info(
        "[Server] Guess submitted by %s: %s/%s connected players submitted",
        player_id,
        len(room.metadata.submitted_players),
        len(expected_guessers(room)),
    )
    return all_expected_guesses_submitted(room)


def assign_guess_targets(player_ids: list[str]) -> dict[str, str]:
    """Assign each player exactly one other player's drawing to guess.

    Uses circular rotation on a shuffled list: player[i] guesses player[(i+1) % n].
    With 2+ players this guarantees no self-assignments.
    """
    if len(player_ids) < 2:
        return {}

    shuffled = player_ids[:]
    random.shuffle(shuffled)
    return {player_id: shuffled[(i + 1) % len(shuffled)] for i, player_id in enumerate(shuffled)}


def _best_guesser_highlight(results: list[RoundResultItem]) -> RoundHighlight | None:
    """Pick the player with the highest correct/total ratio (needs ≥1 correct guess)."""
    best: RoundResultItem | None = None
    best_ratio = 0.0
    for item in results:
        if item.total_items <= 0 or item.correct_guesses <= 0:
            continue
        ratio = item.correct_guesses / item.total_items
        better_ratio = best is None or ratio > best_ratio
        tie_break = best is not None and ratio == best_ratio and item.correct_guesses > best.correct_guesses
        if better_ratio or tie_break:
            best = item
            best_ratio = ratio
    if best is None:
        return None
    return RoundHighlight(playerId=best.player_id, detail=f"{best.correct_guesses}/{best.total_items}")


def _speed_demon_highlight(submissions: list[GuessSubmissionState]) -> RoundHighlight | None:
    """Pick the first player to submit a non-empty guess set."""
    candidates = [s for s in submissions if s.submitted_at > 0 and any(g.strip() for g in s.guesses)]
    if not candidates:
        return None
    fastest = min(candidates, key=lambda s: s.submitted_at)
    return RoundHighlight(playerId=fastest.player_id, detail="")


def _wildest_miss_highlight(miss_candidates: list[tuple[str, str, float]]) -> RoundHighlight | None:
    """Pick the guess furthest (string-distance) from any target item."""
    if not miss_candidates:
        return None
    player_id, guess, _distance = max(miss_candidates, key=lambda c: c[2])
    return RoundHighlight(playerId=player_id, detail=guess)


def compute_highlights(
    results: list[RoundResultItem],
    submissions: list[GuessSubmissionState],
    miss_candidates: list[tuple[str, str, float]],
) -> RoundHighlights | None:
    """Build the per-round highlights; returns None for empty/degenerate rounds.

    ``miss_candidates`` is a list of ``(player_id, guess, distance)`` for guesses that
    matched no target, where distance is ``100 - nearest_similarity``.
    """
    if not submissions:
        return None
    highlights = RoundHighlights(
        best_guesser=_best_guesser_highlight(results),
        speed_demon=_speed_demon_highlight(submissions),
        wildest_miss=_wildest_miss_highlight(miss_candidates),
    )
    if highlights.best_guesser is None and highlights.speed_demon is None and highlights.wildest_miss is None:
        return None
    return highlights


def _collect_miss_candidates(
    *,
    player_id: str,
    guesses: list[str],
    matched_guesses: set[str],
    targets: list[GuessTarget],
    miss_candidates: list[tuple[str, str, float]],
) -> None:
    """Append (player_id, guess, distance) for each guess that matched no target."""
    for guess in guesses:
        if guess in matched_guesses or not guess_matcher.normalize(guess):
            continue
        nearest = max((guess_matcher.fuzzy_match(guess, t.label)[1] for t in targets), default=0.0)
        miss_candidates.append((player_id, guess, 100.0 - nearest))


async def score_round(room: GameRoom, db: AsyncSession) -> RoundCompleteServerEvent:
    """Score the current round and update cumulative room scores."""
    results: list[RoundResultItem] = []
    round_points: dict[str, int] = dict.fromkeys(room.players, 0)
    miss_candidates: list[tuple[str, str, float]] = []

    for submission in room.metadata.guess_submissions:
        player_id = submission.player_id
        target_player_id = submission.target_player_id
        guesses = submission.guesses

        target_assignment = room.metadata.player_assignments.get(target_player_id)
        if not target_assignment or target_assignment.category_id is None:
            logger.warning(
                "[GameRoom %s] No prompt assignment found for player %s, skipping", room.room_id, target_player_id
            )
            continue

        scoring_targets = await category_service.get_localized_scoring_targets(
            db,
            category_id=target_assignment.category_id,
            prompt_ids=target_assignment.item_ids,
            preferred_locale=room.get_player_locale(player_id),
        )
        scoring_result = guess_matcher.score_guesses_against_targets(guesses, scoring_targets.targets)
        correct_count = scoring_result.score
        points_earned = correct_count * POINTS_PER_CORRECT_GUESS

        _collect_miss_candidates(
            player_id=player_id,
            guesses=guesses,
            matched_guesses={match.guess for match in scoring_result.matches},
            targets=scoring_targets.targets,
            miss_candidates=miss_candidates,
        )

        if player_id in round_points:
            round_points[player_id] += points_earned
        if target_player_id in round_points:
            round_points[target_player_id] += points_earned

        results.append(
            _build_round_result_item(
                player_id=player_id,
                target_player_id=target_player_id,
                correct_guesses=correct_count,
                total_items=len(scoring_targets.targets),
                points_earned=points_earned,
            ),
        )

    for player_id, points in round_points.items():
        room.metadata.player_scores[player_id] = room.metadata.player_scores.get(player_id, 0) + points

    room.metadata.game_phase = GamePhase.ROUND_RESULTS
    return RoundCompleteServerEvent(
        results=results,
        scores=dict(room.metadata.player_scores),
        highlights=compute_highlights(results, room.metadata.guess_submissions, miss_candidates),
    )


def game_complete_event(room: GameRoom) -> GameCompleteServerEvent:
    """Build the final game-complete event and update the room phase."""
    winner_id = (
        max(room.metadata.player_scores, key=lambda pid: room.metadata.player_scores[pid])
        if room.metadata.player_scores
        else ""
    )
    room.metadata.game_phase = GamePhase.FINAL_RESULTS
    return GameCompleteServerEvent(
        finalScores=dict(room.metadata.player_scores),
        winner=winner_id,
    )
