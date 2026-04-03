"""Round state and scoring helpers for game rooms."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.rooms.protocol import (
    GameCompleteBroadcastEvent,
    ReadyStatusEvent,
    RoundCompleteBroadcastEvent,
    RoundResultItem,
    StartGuessingEvent,
)
from app.rooms.state import GuessSubmissionState, PlayerCardState
from app.scoring import guess_matcher

if TYPE_CHECKING:
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
    round_length: int | None,
    difficulty: Difficulty | None,
    max_rounds: int | None,
) -> None:
    """Initialize a new game from the lobby state."""
    room.metadata.round_length = round_length
    room.metadata.difficulty = difficulty or room.metadata.difficulty
    room.metadata.max_rounds = max_rounds or 5
    room.metadata.game_phase = "lobby"
    room.metadata.current_round = 0
    room.metadata.round_start_time = None
    room.metadata.player_cards = {}
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    room.metadata.player_scores = dict.fromkeys(room.players, 0)
    room.metadata.ready_players.clear()


def start_round(room: GameRoom, *, round_number: int | None, cards: dict[str, PlayerCardState] | None) -> int:
    """Transition the room into a new drawing round and return the start timestamp."""
    round_start_time = int(time.time() * 1000)
    room.metadata.round_start_time = round_start_time
    room.metadata.game_phase = "drawing"
    room.metadata.current_round = round_number or (room.metadata.current_round + 1)
    room.metadata.player_cards = cards or {}
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    room.metadata.player_count_for_scoring = len(room.players)
    for player_id in room.players:
        room.metadata.player_scores.setdefault(player_id, 0)
    room.metadata.ready_players.clear()
    return round_start_time


def start_guessing(room: GameRoom) -> int:
    """Transition into the guessing phase and return the scoring timeout."""
    room.metadata.game_phase = "guessing"
    room.metadata.player_count_for_scoring = len(room.players)
    return room.metadata.round_length or 30


def start_guessing_event(room: GameRoom) -> StartGuessingEvent:
    """Transition into guessing and return the broadcast event."""
    start_guessing(room)
    return StartGuessingEvent()


def reset_game(room: GameRoom) -> None:
    """Reset mutable game state back to the lobby."""
    room.metadata.player_scores = {}
    room.metadata.current_round = 0
    room.metadata.guess_submissions = []
    room.metadata.submitted_players = set()
    room.metadata.player_cards = {}
    room.metadata.ready_players.clear()
    room.metadata.round_start_time = None
    room.metadata.game_phase = "lobby"


def mark_player_ready(room: GameRoom, player_id: str) -> ReadyStatusEvent:
    """Record that a player is ready and return the shared ready-status payload."""
    room.metadata.ready_players.add(player_id)
    return ReadyStatusEvent(
        readyCount=len(room.metadata.ready_players),
        totalPlayers=len(room.players),
    )


def record_guess_submission(room: GameRoom, *, player_id: str, target_player_id: str, guesses: list[str]) -> bool:
    """Store a guess submission and report whether scoring should begin immediately."""
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


def score_round(room: GameRoom) -> RoundCompleteBroadcastEvent:
    """Score the current round and update cumulative room scores."""
    results: list[RoundResultItem] = []
    round_points: dict[str, int] = dict.fromkeys(room.players, 0)

    for submission in room.metadata.guess_submissions:
        player_id = submission.player_id
        target_player_id = submission.target_player_id
        guesses = submission.guesses

        target_card = room.metadata.player_cards.get(target_player_id)
        if not target_card:
            logger.warning("[GameRoom %s] No card found for player %s, skipping", room.room_id, target_player_id)
            continue

        correct_items = target_card.items
        alternatives_map = target_card.alternatives
        scoring_result = guess_matcher.score_guesses(guesses, correct_items, alternatives_map)
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
                total_items=len(correct_items),
                points_earned=points_earned,
            ),
        )

    for player_id, points in round_points.items():
        room.metadata.player_scores[player_id] = room.metadata.player_scores.get(player_id, 0) + points

    room.metadata.game_phase = "scoring"
    return RoundCompleteBroadcastEvent(
        results=results,
        scores=dict(room.metadata.player_scores),
    )


def game_complete_event(room: GameRoom) -> GameCompleteBroadcastEvent:
    """Build the final game-complete event and update the room phase."""
    winner_id = (
        max(room.metadata.player_scores, key=lambda pid: room.metadata.player_scores[pid])
        if room.metadata.player_scores
        else ""
    )
    room.metadata.game_phase = "complete"
    return GameCompleteBroadcastEvent(
        finalScores=dict(room.metadata.player_scores),
        winner=winner_id,
    )
