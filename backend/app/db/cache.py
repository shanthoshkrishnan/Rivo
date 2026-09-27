"""
RIVO Backend — Cache (Redis) Layer
====================================
Thin wrapper around redis-py that provides:
  - get / set / delete with automatic JSON (de)serialisation
  - A namespaced key builder for route caching
  - Async-compatible interface using redis.asyncio

Every cached value is tagged with a freshness label so the API
can transparently report LIVE vs RECENT data to the client.

Key naming convention:
    rivo:{domain}:{hash_of_params}

Examples:
    rivo:route:abc123
    rivo:rental:search:def456
    rivo:facility:hospital:ghi789
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None
_redis_checked: bool = False
_redis_available: bool = False
_memory_cache: dict[str, tuple[float, Any]] = {}


async def get_redis() -> Optional[aioredis.Redis]:
    """Return (and lazily create) the singleton Redis client with in-memory fallback."""
    global _redis_client, _redis_checked, _redis_available
    if not _redis_checked:
        _redis_checked = True
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=0.4,
                socket_timeout=0.4,
            )
            await client.ping()
            _redis_client = client
            _redis_available = True
            logger.info("Redis connected", url=settings.REDIS_URL)
        except Exception:
            logger.info("Redis not active; activated zero-overhead in-memory cache")
            _redis_client = None
            _redis_available = False
    return _redis_client if _redis_available else None


def make_cache_key(domain: str, **params: Any) -> str:
    """
    Build a deterministic, namespaced Redis key from arbitrary parameters.

    The parameters dict is sorted and JSON-serialised before hashing so
    key order does not matter.
    """
    payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"rivo:{domain}:{digest}"


async def cache_get(key: str) -> Optional[Any]:
    """
    Retrieve a cached value. Returns None on miss.
    Transparently uses in-memory cache when Redis is offline.
    """
    import time
    now = time.time()
    if key in _memory_cache:
        expire_at, val = _memory_cache[key]
        if now < expire_at:
            return val
        _memory_cache.pop(key, None)

    client = await get_redis()
    if client is not None:
        try:
            raw = await client.get(key)
            if raw is not None:
                val = json.loads(raw)
                _memory_cache[key] = (now + 60.0, val)
                return val
        except Exception as exc:
            logger.debug("Cache GET failed", key=key, error=str(exc))
    return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """
    Store a value in the cache with a TTL (seconds).
    Saves to both in-memory store and Redis.
    """
    import time
    _memory_cache[key] = (time.time() + ttl, value)

    client = await get_redis()
    if client is not None:
        try:
            await client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        except Exception as exc:
            logger.debug("Cache SET failed", key=key, error=str(exc))


async def cache_delete(key: str) -> None:
    """Invalidate a cache entry."""
    _memory_cache.pop(key, None)
    client = await get_redis()
    if client is not None:
        try:
            await client.delete(key)
        except Exception as exc:
            logger.debug("Cache DELETE failed", key=key, error=str(exc))


async def close_redis() -> None:
    """Call during application shutdown to cleanly close the connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
