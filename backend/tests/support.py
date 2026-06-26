"""Shared lightweight helpers for backend tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from fastapi import WebSocket


@dataclass
class TestWebSocket:
    """Lean websocket test double for room-oriented unit tests."""

    sent_texts: list[str] = field(default_factory=list)
    close_calls: list[dict[str, object | None]] = field(default_factory=list)
    send_error: Exception | None = None

    async def send_text(self, message: str) -> None:
        """Record a websocket text payload."""
        if self.send_error is not None:
            raise self.send_error
        self.sent_texts.append(message)

    async def send_json(self, data: object) -> None:
        """Serialize and record a websocket JSON payload."""
        await self.send_text(json.dumps(data))

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        """Record a websocket close call."""
        self.close_calls.append({"code": code, "reason": reason})


def as_websocket(test_websocket: TestWebSocket) -> WebSocket:
    """Cast a lightweight websocket double to the FastAPI websocket type used by GameRoom."""
    return cast("WebSocket", test_websocket)
