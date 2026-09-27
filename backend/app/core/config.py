"""
RIVO Backend — Application Configuration
=========================================
Reads all settings from environment variables (or .env file).
Pydantic-Settings validates and type-coerces every value at startup,
so the application fails fast if a required variable is missing or
has the wrong type.

Data-freshness labels (LIVE, PERIODIC, ESTIMATED, HISTORICAL) are
defined here so every module imports from one canonical location.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Data-freshness labels (referenced by every layer that produces data)
# ─────────────────────────────────────────────────────────────────────────────
class DataFreshness(str, Enum):
    """
    UI-facing freshness labels.  Every API response that surfaces data
    MUST include one of these labels so the frontend can display it
    transparently.

    LIVE        – returned directly from a live provider right now
    RECENT      – from cache; provider was live within ROUTE_CACHE_TTL
    PERIODIC    – batch-refreshed on a schedule (e.g. daily GTFS)
    ESTIMATED   – derived from a model, not a direct observation
    HISTORICAL  – from a dataset that is not regularly updated
    LOW_DATA    – very few observations; confidence is low
    """
    LIVE = "LIVE"
    RECENT = "RECENT"
    PERIODIC = "PERIODIC"
    ESTIMATED = "ESTIMATED"
    HISTORICAL = "HISTORICAL"
    LOW_DATA = "LOW_DATA"


class ConfidenceLevel(str, Enum):
    """Human-readable confidence tiers.  Do not use raw percentages."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AvailabilityStatus(str, Enum):
    """Rental availability state."""
    AVAILABLE = "AVAILABLE"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    RECENTLY_SEEN = "RECENTLY_SEEN"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    """Rental verification level."""
    UNVERIFIED = "UNVERIFIED"
    LOCATION_VERIFIED = "LOCATION_VERIFIED"
    OWNER_ATTESTED = "OWNER_ATTESTED"
    RIVO_VERIFIED = "RIVO_VERIFIED"


class RentalProviderName(str, Enum):
    MOCK = "mock"
    OPEN_DATASET = "open_dataset"
    LICENSED = "licensed"
    AUTHORIZED_THIRD_PARTY = "authorized_third_party"
    RIVO_DIRECT = "rivo_direct"
    AUTHORIZED_PARTNER = "authorized_partner"


class LiveApiDisabledError(Exception):
    """Raised when a live external Google API call is attempted while RIVO_LIVE_API_TESTS=False."""
    pass


_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_CANONICAL_BACKEND_ENV = _BACKEND_DIR / ".env"
_CANONICAL_ROOT_ENV = _REPO_ROOT / ".env"

# Explicitly load backend/.env into environment if present
from dotenv import load_dotenv
if _CANONICAL_BACKEND_ENV.exists():
    load_dotenv(dotenv_path=_CANONICAL_BACKEND_ENV, override=False)
if _CANONICAL_ROOT_ENV.exists():
    load_dotenv(dotenv_path=_CANONICAL_ROOT_ENV, override=False)


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    """
    Central settings object.  Uses Pydantic-Settings to load from:
      1. Environment variables (highest priority)
      2. backend/.env (canonical backend configuration)
      3. Repo root .env (if present)
      4. .env in the current working directory
      5. Defaults defined below

    All fields are validated at import time; the application refuses to start
    if a required setting is absent or malformed.
    """

    model_config = SettingsConfigDict(
        env_file=[
            str(_CANONICAL_ROOT_ENV),
            str(_CANONICAL_BACKEND_ENV),
            ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "changeme"
    LOG_LEVEL: str = "INFO"
    APP_TITLE: str = "RIVO Backend API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "Chennai-first housing + mobility intelligence platform. "
        "PS-11-S3 — Can the People Who Run the City Afford to Live In It?"
    )

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://rivo:rivo_password@localhost:5432/rivo_db"
    )
    DATABASE_SYNC_URL: str = (
        "postgresql+psycopg2://rivo:rivo_password@localhost:5432/rivo_db"
    )

    # ── Cache ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    ROUTE_CACHE_TTL: int = 3600   # seconds; cached route is RECENT
    RENTAL_CACHE_TTL: int = 900   # 15 min before re-fetch

    # ── Routing providers ────────────────────────────────────────────────────
    GOOGLE_ROUTES_API_KEY: str = ""          # blank → skip Google routing
    OTP_BASE_URL: str = "http://localhost:8080/otp"
    OTP_ENABLED: bool = False

    # ── Rental provider ──────────────────────────────────────────────────────
    RENTAL_PROVIDER: RentalProviderName = RentalProviderName.MOCK
    LICENSED_RENTAL_API_KEY: str = ""
    LICENSED_RENTAL_BASE_URL: str = ""

    # ── Places / Facilities ──────────────────────────────────────────────────
    GOOGLE_PLACES_API_KEY: str = ""          # blank → OSM-only mode

    # ── Live API Safety Switch & Quota Budgets ───────────────────────────────
    # When False, live Google HTTP requests are blocked to preserve quota during development.
    RIVO_LIVE_API_TESTS: bool = False
    ROUTE_SEARCH_BUDGET: int = 10
    PLACES_SEARCH_BUDGET: int = 8
    DETAILED_ROUTE_BUDGET: int = 5
    FAMILY_ROUTE_BUDGET: int = 6

    # ── Rental Inventory Budgets & Refresh ────────────────────────────────────
    RENTAL_REFRESH_BUDGET: int = 50
    RENTAL_PROVIDER_TTL: int = 86400  # 24 hours in seconds

    # ── Fuel prices (updated periodically; override via env/DB) ──────────────
    DEFAULT_PETROL_PRICE_INR: float = 105.0
    DEFAULT_DIESEL_PRICE_INR: float = 92.0

    # ── ML model ─────────────────────────────────────────────────────────────
    RENT_MODEL_PATH: str = "data/models/rent_model.joblib"

    # ── Data directories ─────────────────────────────────────────────────────
    SEED_DATA_DIR: str = "data/seed"
    FIXTURE_DATA_DIR: str = "data/fixtures"

    # ── Transport defaults ────────────────────────────────────────────────────
    DEFAULT_WORK_DAYS_PER_MONTH: int = 22    # configurable; 22 or 26
    TWO_WHEELER_EFFICIENCY_KMPL: float = 45.0
    CAR_EFFICIENCY_KMPL: float = 14.0

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    # ── H3 resolution ────────────────────────────────────────────────────────
    H3_RESOLUTION: int = 9   # ~174 m hex diameter — good city-level resolution

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def google_routes_enabled(self) -> bool:
        return bool(self.GOOGLE_ROUTES_API_KEY and self.GOOGLE_ROUTES_API_KEY.strip())

    @property
    def google_places_enabled(self) -> bool:
        return bool(self.GOOGLE_PLACES_API_KEY and self.GOOGLE_PLACES_API_KEY.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings singleton.
    Use dependency injection in FastAPI:
        settings: Settings = Depends(get_settings)
    Or import directly for scripts/services:
        from app.core.config import get_settings
        settings = get_settings()
    """
    return Settings()
