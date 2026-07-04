"""Small Redis-backed fixed-window rate limiting helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.core.config import settings
from app.core.redis import increment_rate_limit

if TYPE_CHECKING:
    from starlette.requests import HTTPConnection


def get_client_identifier(conn: HTTPConnection) -> str:
    """Return a stable best-effort client identifier for route throttling.

    Accepts any Starlette connection (HTTP ``Request`` or ``WebSocket``). Only
    honours X-Forwarded-For when ``rate_limit_trust_forwarded_for`` is set, since
    a client-supplied value would otherwise let an attacker rotate IPs to bypass
    per-IP throttles (login/register/room-creation brute force).
    """
    if settings.rate_limit_trust_forwarded_for:
        # Use the RIGHTMOST entry: the trusted proxy (Caddy) appends the real peer
        # IP, so the last hop is what it saw. The leftmost is client-supplied and
        # spoofable — taking it would reintroduce the per-IP throttle bypass.
        forwarded_for = conn.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.rsplit(",", 1)[-1].strip()
    if conn.client and conn.client.host:
        return conn.client.host
    return "unknown"


async def enforce_rate_limit(
    *,
    bucket: str,
    identifier: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise 429 when a fixed-window limit is exceeded."""
    count, retry_after = await increment_rate_limit(bucket, identifier, window_seconds=window_seconds)
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after or window_seconds} seconds.",
            headers={"Retry-After": str(retry_after or window_seconds)},
        )
