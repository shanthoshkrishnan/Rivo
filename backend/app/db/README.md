# `app/db/` — Database & Cache Layer

This package provides:
- Async SQLAlchemy engine and session factory (PostgreSQL + PostGIS)
- Sync engine for Alembic migrations and scripts
- Redis async cache layer with graceful degradation

---

## Files

### `session.py`

| Symbol | What it is |
|---|---|
| `async_engine` | Async SQLAlchemy engine (connection pool, `pool_pre_ping=True`) |
| `AsyncSessionLocal` | Async session factory |
| `sync_engine` | Sync engine for Alembic / CLI scripts |
| `Base` | Declarative base — **all ORM models inherit from this** |
| `get_db()` | FastAPI dependency — yields `AsyncSession`, auto-commit/rollback |
| `managed_session()` | Context manager for background tasks and scripts |

**FastAPI dependency injection:**
```python
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

**Script usage:**
```python
from app.db.session import managed_session

async with managed_session() as db:
    await db.execute(...)
```

---

### `cache.py`

Redis async cache with:
- **Graceful degradation**: all functions silently no-op if Redis is unavailable
- **Namespaced keys**: `rivo:{domain}:{sha256_hash}` — e.g. `rivo:route:abc123`
- **JSON serialisation**: values are JSON-encoded/decoded automatically

| Function | Purpose |
|---|---|
| `make_cache_key(domain, **params)` | Build a deterministic cache key from any params |
| `cache_get(key)` | Get cached value or `None` on miss |
| `cache_set(key, value, ttl)` | Store value with TTL in seconds |
| `cache_delete(key)` | Invalidate a cache entry |
| `close_redis()` | Call during application shutdown |

**Route caching example:**
```python
key = make_cache_key(
    "route",
    origin_lat=12.975, origin_lon=80.220,
    dest_lat=13.067, dest_lon=80.243,
    mode="TRANSIT",
    departure_bucket="08:00",
    provider="google",
)
cached = await cache_get(key)
if cached:
    return RouteResult(**cached)
```

---

## Connection settings

| Setting | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` | Async PostgreSQL |
| `DATABASE_SYNC_URL` | `postgresql+psycopg2://…` | Sync PostgreSQL (Alembic) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis |
| `ROUTE_CACHE_TTL` | `3600` | Route cache lifetime (seconds) |
| `RENTAL_CACHE_TTL` | `900` | Rental listing cache lifetime |

---

## Database setup

```bash
# Start PostgreSQL with PostGIS
docker compose up -d postgres

# Apply all migrations
alembic upgrade head

# Seed reference data
python scripts/seed_data.py
```

---

## Why PostGIS?

PostGIS enables efficient spatial queries such as:
- `ST_DWithin` — find all facilities within X metres of a point
- `ST_Distance` — calculate distance between two geometries
- `ST_MakePoint` — construct geometry from lat/lon

Every table with a spatial component has a `geom GEOMETRY(POINT, 4326)` column and an `h3_index` VARCHAR column for hex-level aggregation.
