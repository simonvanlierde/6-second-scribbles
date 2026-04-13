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
    RoundResultItem,
    StartGuessingEvent,
)
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from app.scoring import guess_matcher

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.types import Difficulty
    from app.rooms.manager import GameRoom

logger = logging.getLogger(__name__)


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
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    room.metadata.player_count_for_scoring = len(room.players)
    for player_id in room.players:
        room.metadata.player_scores.setdefault(player_id, 0)
    room.metadata.ready_players.clear()
    return round_start_time


def start_guessing(room: GameRoom) -> int:
    """Transition into the guessing phase and return the scoring timeout."""
    room.metadata.guessing_start_time = int(time.time() * 1000)
    room.metadata.game_phase = GamePhase.GUESSING
    room.metadata.guess_targets = assign_guess_targets(list(room.players))
    room.metadata.player_count_for_scoring = len(room.players)
    room.metadata.ready_players.clear()
    return room.metadata.guessing_time_limit or 60


def start_guessing_event(room: GameRoom) -> StartGuessingEvent:
    """Transition into guessing and return the broadcast event."""
    start_guessing(room)
    return StartGuessingEvent(
        type="start_guessing",
        guessingStartTime=room.metadata.guessing_start_time,
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

    submission = GuessSubmissionState(player_id=player_id, target_player_id=target_player_id, guesses=guesses)
    room.metadata.guess_submissions.append(submission)
    room.metadata.submitted_players.add(player_id)
    submitted = len(room.metadata.submitted_players)
    expected = room.metadata.player_count_for_scoring
    logger.info(
        "[Server] Guess submitted by %s: %s/%s players submitted",
        player_id,
        submitted,
        expected,
    )
    return expected > 0 and submitted >= expected


def assign_guess_targets(player_ids: list[str]) -> dict[str, str]:
    """Assign each player exactly one other player's drawing to guess."""
    if len(player_ids) < 2:
        return {}

    shuffled = player_ids[:]
    random.shuffle(shuffled)

    for index, player_id in enumerate(shuffled):
        next_player_id = shuffled[(index + 1) % len(shuffled)]
        if player_id == next_player_id:
            return assign_guess_targets(player_ids)

    return {player_id: shuffled[(index + 1) % len(shuffled)] for index, player_id in enumerate(shuffled)}


async def score_round(room: GameRoom, db: AsyncSession) -> RoundCompleteServerEvent:
    """Score the current round and update cumulative room scores."""
    results: list[RoundResultItem] = []
    round_points: dict[str, int] = dict.fromkeys(room.players, 0)

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
        points_earned = correct_count * 10

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
