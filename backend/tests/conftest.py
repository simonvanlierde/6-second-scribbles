"""Shared pytest configuration for the backend test suite."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from app.categories import service as category_service
from app.rooms.manager import room_manager as global_room_manager

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

PYTEST_MAIN_TASK_NAME = "Task-1"


@pytest.fixture(autouse=True)
async def reset_room_manager() -> AsyncGenerator[None]:
    """Keep the global room manager isolated between tests."""
    await global_room_manager.stop()
    global_room_manager.rooms.clear()
    yield
    await global_room_manager.stop()
    global_room_manager.rooms.clear()


@pytest.fixture
def _deterministic_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make random.sample deterministic by taking the first N items."""
    monkeypatch.setattr(category_service.random, "sample", lambda items, n: list(items)[:n])


@pytest.fixture(scope="session", autouse=True)
async def cleanup_pending_tasks_at_session_end() -> AsyncGenerator[None]:
    """Cancel any leftover background tasks before pytest tears down the shared session loop."""
    yield
    current = asyncio.current_task()
    pending = [
        task
        for task in asyncio.all_tasks()
        if task is not current and not task.done() and task.get_name() != PYTEST_MAIN_TASK_NAME
    ]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
