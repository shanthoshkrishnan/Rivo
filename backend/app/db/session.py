"""
RIVO Backend — Database Engine & Session Factory
=================================================
Provides:
  - Async SQLAlchemy engine (used by FastAPI handlers)
  - Sync engine (used by Alembic migrations and CLI scripts)
  - Async session factory with dependency-injection helper
  - Base declarative class shared by all ORM models

PostGIS support is enabled via GeoAlchemy2.
The `load_spatialite` event is NOT used because we rely on
PostgreSQL + PostGIS, not SQLite/SpatiaLite.

Usage (FastAPI):
    from app.db.session import get_db
    async def endpoint(db: AsyncSession = Depends(get_db)):
        ...

Usage (scripts/migrations):
    from app.db.session import sync_engine
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, MappedColumn
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import logger


settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Async engine  (FastAPI / application runtime)
# ─────────────────────────────────────────────────────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",   # SQL log in dev only
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,           # drop stale connections before use
    pool_recycle=1800,            # recycle every 30 min
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# Sync engine  (Alembic, scripts, ML training)
# ─────────────────────────────────────────────────────────────────────────────
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Declarative base shared by all ORM models
# ─────────────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All ORM model classes inherit from this Base.
    Importing this in alembic/env.py ensures all tables are discovered
    during autogenerate.
    """
    pass


_db_available: bool | None = None
_sqlite_sessionmaker = None


def _get_sqlite_sessionmaker():
    global _sqlite_sessionmaker
    if _sqlite_sessionmaker is None:
        import os
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent.parent
        sqlite_path = base_dir / "data" / "rivo.db"
        if sqlite_path.exists():
            from sqlalchemy.ext.asyncio import create_async_engine
            sqlite_engine = create_async_engine(f"sqlite+aiosqlite:///{sqlite_path}", echo=False)
            _sqlite_sessionmaker = async_sessionmaker(
                bind=sqlite_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
    return _sqlite_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    """
    Yield an async database session for use in FastAPI route handlers.
    Attempts PostgreSQL first; automatically falls back to local seeded
    SQLite database (data/rivo.db) if PostgreSQL is offline.
    """
    global _db_available
    session = None

    # If PostgreSQL is already known to be offline, use SQLite fallback directly
    if _db_available is False:
        sqlite_maker = _get_sqlite_sessionmaker()
        if sqlite_maker is not None:
            async with sqlite_maker() as s:
                try:
                    yield s
                finally:
                    await s.close()
            return
        yield None
        return

    try:
        session = AsyncSessionLocal()
        if _db_available is None:
            try:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                _db_available = True
            except Exception:
                _db_available = False
                logger.info("PostgreSQL offline; connected to local SQLite database (data/rivo.db)")
                sqlite_maker = _get_sqlite_sessionmaker()
                if sqlite_maker is not None:
                    async with sqlite_maker() as s:
                        try:
                            yield s
                        finally:
                            await s.close()
                    return
                yield None
                return

        yield session
        await session.commit()
    except Exception:
        if session:
            try:
                await session.rollback()
            except Exception:
                pass
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception:
                pass


@asynccontextmanager
async def managed_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context-manager version of get_db for use outside FastAPI
    (e.g. background tasks, CLI scripts).

    Example:
        async with managed_session() as db:
            await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
