"""Optional Upstash Redis read-through cache for session history.

Redis is never the source of truth - Supabase is. Serverless-friendly by
design: Upstash speaks Redis over HTTPS (no TCP connection pools), and any
cache failure degrades silently to plain Supabase reads. Wiping Redis at
any moment loses nothing but a few warm reads.
"""

import json
import logging

import httpx

from fintra.config import get_settings

logger = logging.getLogger("fintra.cache")

TTL_SECONDS = 86400  # idle sessions expire from the cache after a day
_TIMEOUT = 2.0  # a slow cache must never stall a turn


def _key(session_id: str) -> str:
    return f"fintra:chat:{session_id}"


def _command(*args: str) -> dict | None:
    """Run one Redis command via the Upstash REST API; None if disabled/failed."""
    settings = get_settings()
    if not (settings.upstash_redis_rest_url and settings.upstash_redis_rest_token):
        return None
    try:
        response = httpx.post(
            settings.upstash_redis_rest_url,
            headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
            json=list(args),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception:  # noqa: BLE001 - cache failures must never break a turn
        logger.warning("redis unavailable - degrading to supabase-only reads")
        return None


def get_history(session_id: str) -> list[dict] | None:
    """Cached history for the session; None means miss (or cache disabled)."""
    result = _command("GET", _key(session_id))
    if result is None or result.get("result") is None:
        return None
    try:
        return json.loads(result["result"])
    except (TypeError, ValueError):
        return None  # corrupt entry: treat as a miss, Supabase will refill it


def set_history(session_id: str, history: list[dict]) -> None:
    _command("SET", _key(session_id), json.dumps(history), "EX", str(TTL_SECONDS))
