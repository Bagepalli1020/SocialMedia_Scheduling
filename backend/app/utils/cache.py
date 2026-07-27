"""Simple Redis cache helpers for analytics dashboard."""

import json
from typing import Any

import redis

from app.config import get_settings

settings = get_settings()

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _redis_client
    try:
        if _redis_client is None:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # ping to ensure connection
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def cache_get(key: str) -> Any | None:
    client = get_redis()
    if not client:
        return None
    raw = client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    client = get_redis()
    if not client:
        return
    client.setex(key, ttl_seconds, json.dumps(value, default=str))


def cache_delete_pattern(pattern: str) -> None:
    client = get_redis()
    if not client:
        return
    for key in client.scan_iter(match=pattern):
        client.delete(key)
