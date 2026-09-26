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


async def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the singleton Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        # Verify connection
        try:
            await _redis_client.ping()
            logger.info("Redis connected", url=settings.REDIS_URL)
        except Exception as exc:
            logger.warning(
                "Redis unavailable — caching disabled", error=str(exc)
            )
            _redis_client = None
    return _redis_client


def make_cache_key(domain: str, **params: Any) -> str:
    """
    Build a deterministic, namespaced Redis key from arbitrary parameters.

    The parameters dict is sorted and JSON-serialised before hashing so
    key order does not matter.

    Example:
        make_cache_key(
            "route",
            origin="13.0827,80.2707",
            destination="13.0569,80.2425",
            mode="TRANSIT",
            departure_bucket="08:00",
            provider="google",
        )
        → "rivo:route:a3f2..."
    """
    payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"rivo:{domain}:{digest}"


async def cache_get(key: str) -> Optional[Any]:
    """
    Retrieve a cached value.  Returns None on miss or Redis unavailability.
    """
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Cache GET failed", key=key, error=str(exc))
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """
    Store a value in the cache with a TTL (seconds).
    Silently degrades if Redis is unavailable.
    """
    client = await get_redis()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
    except Exception as exc:
        logger.warning("Cache SET failed", key=key, error=str(exc))


async def cache_delete(key: str) -> None:
    """Invalidate a cache entry."""
    client = await get_redis()
    if client is None:
        return
    try:
        await client.delete(key)
    except Exception as exc:
        logger.warning("Cache DELETE failed", key=key, error=str(exc))


async def close_redis() -> None:
    """Call during application shutdown to cleanly close the connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
