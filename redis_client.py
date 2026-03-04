import json
import logging
from typing import Any

import redis

from config import REDIS_URL

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if not REDIS_URL:
        raise RuntimeError("REDIS_URL is not configured.")
    if _redis_client is None:
        use_ssl = REDIS_URL.startswith("rediss://")
        kwargs: dict[str, Any] = {"decode_responses": True}
        if use_ssl:
            kwargs["ssl"] = True
            kwargs["ssl_cert_reqs"] = None
        _redis_client = redis.Redis.from_url(REDIS_URL, **kwargs)
    return _redis_client


def cache_get_json(key: str) -> Any | None:
    try:
        raw = get_redis_client().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.exception("Redis cache get failed for key=%s", key)
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    try:
        payload = json.dumps(value)
        get_redis_client().setex(key, ttl_seconds, payload)
    except Exception:
        logger.exception("Redis cache set failed for key=%s", key)


def invalidate_leaderboard_cache() -> None:
    try:
        client = get_redis_client()
        keys = client.keys("leaderboard:*")
        if keys:
            client.delete(*keys)
    except Exception:
        logger.exception("Redis leaderboard cache invalidation failed")


def rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
    """
    Sliding-window-ish fixed bucket limiter using Redis INCR + EXPIRE.

    Returns:
        allowed: bool
        count: current request count in window
        retry_after: seconds until window resets (0 if allowed)
    """
    try:
        client = get_redis_client()

        # INCR first, then set EXPIRE for first hit in window.
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, window_seconds)

        ttl = int(client.ttl(key))
        if ttl < 0:
            client.expire(key, window_seconds)
            ttl = window_seconds

        allowed = count <= limit
        retry_after = 0 if allowed else ttl
        return allowed, count, retry_after
    except Exception:
        logger.exception("Redis rate limiter failed for key=%s", key)
        # Fail open when Redis is unavailable.
        return True, 0, 0
