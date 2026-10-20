"""Kick-vote lifecycle helpers for game rooms."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.config import settings
from app.rooms.protocol import (
    KickVoteExpiredEvent,
    KickVoteStartedEvent,
    KickVoteUpdatedEvent,
    PlayerKickedEvent,
)

if TYPE_CHECKING:
    from app.rooms.manager import GameRoom

logger = logging.getLogger(__name__)

HOST_CANNOT_BE_VOTE_KICKED_ERROR = "The host cannot be vote-kicked. Leave the room instead."
VOTE_KICK_PUBLIC_ONLY_ERROR = "Vote-kick is only available in public rooms."
INITIATOR_NOT_IN_ROOM_ERROR = "Initiator not in room"
TARGET_NOT_IN_ROOM_ERROR = "Target player not in room"
SELF_KICK_ERROR = "Cannot kick yourself"
VOTE_ALREADY_IN_PROGRESS_ERROR = "Vote already in progress"
VOTER_NOT_IN_ROOM_ERROR = "Voter not in room"
NO_ACTIVE_VOTE_ERROR = "No active vote for this player"
VOTE_EXPIRED_ERROR = "Vote has expired"
SELF_VOTE_KICK_ERROR = "Cannot vote to kick yourself"


@dataclass
class KickVote:
    """Tracks votes to kick a player."""

    target_player_id: str
    target_player_name: str
    voters: set[str] = field(default_factory=set)
    expires_at: float = field(default_factory=lambda: time.time() + 60)


async def initiate_kick_vote(room: GameRoom, initiator_id: str, target_player_id: str) -> str | None:
    """Start a kick vote, or kick at once when the host asks; return the refusal reason, if any."""
    rejection = _validate_initiate_kick_vote(room, initiator_id, target_player_id)
    if rejection is not None:
        return rejection

    is_host_kicking = initiator_id == room.host_id
    target_is_host = target_player_id == room.host_id

    if is_host_kicking and not target_is_host:
        await kick_player(room, target_player_id, "Kicked by host")
        return None

    if target_is_host:
        return HOST_CANNOT_BE_VOTE_KICKED_ERROR

    if room.metadata.is_private:
        return VOTE_KICK_PUBLIC_ONLY_ERROR

    target_player = room.players[target_player_id]
    vote = KickVote(
        target_player_id=target_player_id,
        target_player_name=target_player.name,
        voters={initiator_id},
        expires_at=time.time() + settings.kick_vote_timeout_seconds,
    )
    room.active_kick_votes[target_player_id] = vote

    await room.broadcast(
        KickVoteStartedEvent(
            targetPlayerId=target_player_id,
            targetPlayerName=target_player.name,
            initiatorId=initiator_id,
            requiredVotes=get_required_votes(room),
            currentVotes=1,
            expiresAt=vote.expires_at * 1000,
        ),
    )

    logger.info(
        "[GameRoom %s] Kick vote started for %s by %s",
        room.room_id,
        target_player.name,
        room.players[initiator_id].name,
    )

    return None


async def cast_kick_vote(room: GameRoom, voter_id: str, target_player_id: str) -> str | None:
    """Cast a vote to kick a player; return the refusal reason, if any."""
    if voter_id not in room.players:
        return VOTER_NOT_IN_ROOM_ERROR

    if target_player_id not in room.active_kick_votes:
        return NO_ACTIVE_VOTE_ERROR

    vote = room.active_kick_votes[target_player_id]

    if time.time() > vote.expires_at:
        del room.active_kick_votes[target_player_id]
        await room.broadcast(KickVoteExpiredEvent(targetPlayerId=target_player_id))
        return VOTE_EXPIRED_ERROR

    if voter_id == target_player_id:
        return SELF_VOTE_KICK_ERROR

    # Re-check host immunity: the target may have been promoted to host after the
    # vote started (host disconnect + transfer), and initiate() only guards the
    # start. Without this a sitting host could be vote-kicked mid-vote.
    if target_player_id == room.host_id:
        return HOST_CANNOT_BE_VOTE_KICKED_ERROR

    vote.voters.add(voter_id)

    required_votes = get_required_votes(room)
    # Count only voters still connected, matching the connected-only denominator in
    # get_required_votes; a departed/disconnected voter must not push the tally over.
    current_votes = sum(1 for vid in vote.voters if vid in room.players and room.players[vid].connected)

    await room.broadcast(
        KickVoteUpdatedEvent(
            targetPlayerId=target_player_id,
            currentVotes=current_votes,
            requiredVotes=required_votes,
        ),
    )

    logger.info(
        "[GameRoom %s] Kick vote: %s/%s for %s",
        room.room_id,
        current_votes,
        required_votes,
        vote.target_player_name,
    )

    if current_votes >= required_votes:
        await kick_player(room, target_player_id, "Kicked by vote")

    return None


def get_required_votes(room: GameRoom) -> int:
    """Calculate required votes to kick a player (the host cannot be vote-kicked)."""
    # Only connected players can actually cast a vote; counting disconnected
    # ("reconnecting") players would inflate the threshold past what is reachable.
    eligible_voters = sum(1 for player in room.players.values() if player.connected) - 1
    return max(2, int((eligible_voters * 2) / 3) + 1)


def _validate_initiate_kick_vote(
    room: GameRoom,
    initiator_id: str,
    target_player_id: str,
) -> str | None:
    if initiator_id not in room.players:
        return INITIATOR_NOT_IN_ROOM_ERROR

    if target_player_id not in room.players:
        return TARGET_NOT_IN_ROOM_ERROR

    if initiator_id == target_player_id:
        return SELF_KICK_ERROR

    if target_player_id in room.active_kick_votes:
        vote = room.active_kick_votes[target_player_id]
        if time.time() < vote.expires_at:
            return VOTE_ALREADY_IN_PROGRESS_ERROR
        del room.active_kick_votes[target_player_id]

    return None


async def kick_player(room: GameRoom, player_id: str, reason: str = "Kicked") -> None:
    """Kick a player from the room."""
    if player_id not in room.players:
        return

    player = room.players[player_id]
    logger.info("[GameRoom %s] Kicking player %s (%s): %s", room.room_id, player.name, player_id, reason)

    await room.broadcast(
        PlayerKickedEvent(
            playerId=player_id,
            playerName=player.name,
            reason=reason,
        ),
        exclude=player_id,
    )

    try:
        await player.websocket.close(code=1008, reason=reason)
    except Exception:
        logger.exception("[GameRoom %s] Error closing websocket for kicked player", room.room_id)

    room.kicked_ids.add(player_id)
    if user_id := room.metadata.player_user_ids.get(player_id):
        room.kicked_ids.add(user_id)
    await room.remove_player(player_id, forget_identity=True)
    room.active_kick_votes.pop(player_id, None)


def cleanup_expired_votes(room: GameRoom) -> int:
    """Remove expired kick votes."""
    now = time.time()
    expired = [target_id for target_id, vote in room.active_kick_votes.items() if now > vote.expires_at]

    for target_id in expired:
        del room.active_kick_votes[target_id]
        logger.info("[GameRoom %s] Kick vote expired for player %s", room.room_id, target_id)

    return len(expired)
