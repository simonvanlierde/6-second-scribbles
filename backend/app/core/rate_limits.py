"""Small Redis-backed fixed-window rate limiting helpers."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.redis import increment_rate_limit


def get_client_identifier(request: Request) -> str:
    """Return a stable best-effort client identifier for route throttling."""
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
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
