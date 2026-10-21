"""Scoring a round whose category or prompts a reseed deleted mid-round."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import delete

from app.categories.models import Category, CategoryPrompt, Prompt
from app.core.types import GamePhase
from app.rooms import manager as manager_module
from app.rooms import player_lifecycle, rounds
from app.rooms.manager import GameRoom
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from tests.constants import PLAYER_ONE_ID, PLAYER_ONE_NAME, PLAYER_TWO_ID, PLAYER_TWO_NAME, ROUND_COMPLETE
from tests.support import TestWebSocket, as_websocket

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def _guessing_room(db_session: AsyncSession) -> tuple[GameRoom, Category, list[Prompt]]:
    category = Category(
        difficulty="medium", source="system", available_locales=["en"], translations={"en": {"name": "Animals"}}
    )
    prompts = [
        Prompt(stable_key=f"reseed-{label}", translations={"en": {"label": label, "aliases": []}})
        for label in ("cat", "dog")
    ]
    db_session.add_all([category, *prompts])
    await db_session.flush()
    db_session.add_all(
        CategoryPrompt(category_id=category.id, prompt_id=p.id, sort_order=i) for i, p in enumerate(prompts)
    )
    await db_session.commit()

    room = GameRoom("ROOM-RESEED")
    await player_lifecycle.add_player(room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(TestWebSocket()))
    await player_lifecycle.add_player(room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(TestWebSocket()))
    card = PlayerPromptAssignmentState(
        category_id=category.id, category="Animals", item_ids=[p.id for p in prompts], items=["cat", "dog"]
    )
    rounds.start_round(room, round_number=1, cards={PLAYER_ONE_ID: card, PLAYER_TWO_ID: card})
    rounds.start_guessing(room)
    room.metadata.guess_submissions = [
        GuessSubmissionState(player_id=PLAYER_ONE_ID, target_player_id=PLAYER_TWO_ID, guesses=["cat", "dog"]),
    ]
    return room, category, prompts


def _round_complete(room: GameRoom) -> dict[str, object]:
    sent = cast("TestWebSocket", room.players[PLAYER_ONE_ID].websocket).sent_texts
    return next(msg for msg in map(json.loads, sent) if msg["type"] == ROUND_COMPLETE)


async def test_deleted_category_scores_zero_and_ends_the_round(
    db_session: AsyncSession,
    db_session_maker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The room leaves GUESSING even though the category lookup now finds nothing."""
    monkeypatch.setattr(manager_module, "get_session_maker", lambda: db_session_maker)
    room, category, _ = await _guessing_room(db_session)
    await db_session.execute(delete(Category).where(Category.id == category.id))
    await db_session.commit()

    await room.score_and_broadcast_round()

    assert room.metadata.game_phase == GamePhase.ROUND_RESULTS
    result = cast("list[dict[str, int]]", _round_complete(room)["results"])[0]
    assert (result["correctGuesses"], result["totalItems"], result["pointsEarned"]) == (0, 0, 0)
    room.scheduler.cancel_round_tasks()


async def test_deleted_prompt_scores_against_the_rest(
    db_session: AsyncSession,
    db_session_maker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A deleted prompt drops out of the targets; the others still score."""
    monkeypatch.setattr(manager_module, "get_session_maker", lambda: db_session_maker)
    room, _, prompts = await _guessing_room(db_session)
    await db_session.execute(delete(Prompt).where(Prompt.id == prompts[1].id))
    await db_session.commit()

    await room.score_and_broadcast_round()

    assert room.metadata.game_phase == GamePhase.ROUND_RESULTS
    result = cast("list[dict[str, int]]", _round_complete(room)["results"])[0]
    assert (result["correctGuesses"], result["totalItems"], result["pointsEarned"]) == (1, 1, 10)
    room.scheduler.cancel_round_tasks()
