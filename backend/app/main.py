"""
RIVO Backend — Main FastAPI Application
=========================================
Entry point for the RIVO backend API.

Startup sequence:
  1. Configure logging
  2. Mount CORS middleware
  3. Include API v1 router
  4. Register lifespan events (DB warmup, Redis connect)

Error handling:
  - 422 validation errors return structured JSON
  - 500 errors return a safe message (no stack trace in production)
  - Provider failures are surfaced via data_freshness labels,
    never hidden from the UI

Docs are available at:
  /docs        — Swagger UI
  /redoc       — ReDoc
  /openapi.json — raw schema
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, logger
from app.db.cache import close_redis, get_redis

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    configure_logging()

    # ── Phase 3: API configuration diagnostic (keys never logged) ─────────────
    google_routes_status = "CONFIGURED" if settings.google_routes_enabled else "NOT CONFIGURED"
    google_places_status = "CONFIGURED" if settings.google_places_enabled else "NOT CONFIGURED"

    logger.info(
        "RIVO Backend starting",
        env=settings.APP_ENV,
        rental_provider=settings.RENTAL_PROVIDER,
    )
    logger.info(f"Google Routes: {google_routes_status}")
    logger.info(f"Google Places: {google_places_status}")

    if not settings.google_routes_enabled:
        logger.warning(
            "Google Routes API key not set — routing will use GTFS → OTP → Mock fallback. "
            "Set GOOGLE_ROUTES_API_KEY in .env to enable live transit routing."
        )
    if not settings.google_places_enabled:
        logger.warning(
            "Google Places API key not set — facility discovery will use local verified seed data. "
            "Set GOOGLE_PLACES_API_KEY in .env to enable live facility search."
        )

    # Warm up Redis connection
    await get_redis()
    yield
    # Shutdown
    await close_redis()
    logger.info("RIVO Backend stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health_check():
        from app.core.circuit_breaker import circuit_breaker
        routes_info = circuit_breaker.get_routes_status()
        places_info = circuit_breaker.get_places_status()
        return {
            "status": "ok",
            "env": settings.APP_ENV,
            "version": settings.APP_VERSION,
            "rental_provider": settings.RENTAL_PROVIDER,
            "google_routes": "CONFIGURED" if settings.google_routes_enabled else "NOT CONFIGURED",
            "google_places": "CONFIGURED" if settings.google_places_enabled else "NOT CONFIGURED",
            "google_routes_available": routes_info["available"],
            "google_places_available": places_info["available"],
            "google_routes_failure_reason": routes_info["reason"],
            "google_places_failure_reason": places_info["reason"],
            "google_status": routes_info["reason"] if not routes_info["available"] else "AVAILABLE",
            "fallback_provider": "gtfs",
            "message": routes_info.get("message") if not routes_info["available"] else "OK",
        }

    # ── Root ──────────────────────────────────────────────────────────────────
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "RIVO API",
            "description": "Chennai-first housing + mobility intelligence platform",
            "team": "CLAIRES (ST1010)",
            "problem_statement": "PS-11-S3",
            "docs": "/docs",
            "version": settings.APP_VERSION,
        }

    # ── Global error handler ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=exc,
        )
        if settings.APP_ENV == "production":
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. Please try again."},
            )
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Application instance (used by uvicorn)
# ─────────────────────────────────────────────────────────────────────────────
app = create_app()
