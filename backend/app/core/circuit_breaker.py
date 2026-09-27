"""
RIVO Backend — Quota Circuit Breaker & Provider Health State
============================================================
Protects Google API quotas and prevents retry storms when quota is exceeded.

Tasks:
  - Task 12: Quota Circuit Breaker (429 / RESOURCE_EXHAUSTED / QUOTA_EXCEEDED)
  - Task 13: Daily Quota Awareness & Provider Health State
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from app.core.config import get_settings
from app.core.logging import logger


class GoogleCircuitBreaker:
    """
    Tracks runtime health and availability of Google APIs.
    Trips immediately upon receiving 429 / QUOTA_EXCEEDED so the application
    switches seamlessly to GTFS / local without retry storms.
    """

    def __init__(self) -> None:
        self._routes_available: bool = True
        self._places_available: bool = True
        self._routes_failure_reason: str = "AVAILABLE"
        self._places_failure_reason: str = "AVAILABLE"
        self._routes_tripped_at: Optional[float] = None
        self._places_tripped_at: Optional[float] = None
        self._cooldown_seconds: float = 300.0  # 5 minutes cooldown before testing availability again

    def get_routes_status(self) -> Dict[str, str | bool]:
        settings = get_settings()
        if not settings.google_routes_enabled:
            return {
                "available": False,
                "reason": "UNCONFIGURED",
                "message": "Google Routes API key not configured",
            }
        if not self._routes_available:
            return {
                "available": False,
                "reason": self._routes_failure_reason,
                "message": "Google live routing temporarily unavailable. Showing periodic transit estimate.",
            }
        return {
            "available": True,
            "reason": "AVAILABLE",
            "message": "Google Routes API active",
        }

    def get_places_status(self) -> Dict[str, str | bool]:
        settings = get_settings()
        if not settings.google_places_enabled:
            return {
                "available": False,
                "reason": "UNCONFIGURED",
                "message": "Google Places API key not configured",
            }
        if not self._places_available:
            return {
                "available": False,
                "reason": self._places_failure_reason,
                "message": "Google Places API temporarily unavailable. Using verified seed facilities.",
            }
        return {
            "available": True,
            "reason": "AVAILABLE",
            "message": "Google Places API active",
        }

    def is_routes_available(self) -> bool:
        return self._routes_available

    def is_places_available(self) -> bool:
        return self._places_available

    def trip_routes(self, reason: str = "QUOTA_EXCEEDED") -> None:
        self._routes_available = False
        self._routes_failure_reason = reason
        self._routes_tripped_at = time.time()
        logger.warning(
            "[CIRCUIT BREAKER] Google Routes circuit breaker TRIPPED",
            reason=reason,
            fallback="gtfs",
        )

    def trip_places(self, reason: str = "QUOTA_EXCEEDED") -> None:
        self._places_available = False
        self._places_failure_reason = reason
        self._places_tripped_at = time.time()
        logger.warning(
            "[CIRCUIT BREAKER] Google Places circuit breaker TRIPPED",
            reason=reason,
            fallback="local_seed",
        )

    def reset(self) -> None:
        """Reset circuit breaker (for testing or after cooldown)."""
        self._routes_available = True
        self._places_available = True
        self._routes_failure_reason = "AVAILABLE"
        self._places_failure_reason = "AVAILABLE"
        self._routes_tripped_at = None
        self._places_tripped_at = None


# Global singleton instance
circuit_breaker = GoogleCircuitBreaker()
