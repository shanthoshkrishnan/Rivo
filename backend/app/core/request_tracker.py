"""
RIVO Backend — External Request Tracker & API Budget Manager
============================================================
Instruments every external API request and enforces strict budgets.
Sanitized counters only — NEVER logs API keys, headers, or personal data.

Tasks:
  - Task 1: Measure current request cost
  - Task 2: Strict API budget limits
  - Task 11: Cache statistics
  - Task 17: API request count targets
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.core.config import get_settings
from app.core.logging import logger


@dataclass
class SearchRequestSummary:
    search_id: str
    listings_examined: int = 0
    routes_requested: int = 0
    routes_cache_hits: int = 0
    places_requested: int = 0
    places_cache_hits: int = 0
    total_external_requests: int = 0
    budget_exhausted: bool = False
    start_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, int | str | bool | float]:
        elapsed_ms = round((time.time() - self.start_time) * 1000, 1)
        return {
            "search_id": self.search_id,
            "listings_examined": self.listings_examined,
            "routes_requested": self.routes_requested,
            "routes_cache_hits": self.routes_cache_hits,
            "places_requested": self.places_requested,
            "places_cache_hits": self.places_cache_hits,
            "total_external_requests": self.total_external_requests,
            "budget_exhausted": self.budget_exhausted,
            "elapsed_ms": elapsed_ms,
        }


class RequestBudgetManager:
    """
    Manages request budgets and captures metrics for a search session.
    Configurable via environment variables:
      - ROUTE_SEARCH_BUDGET (default 10)
      - PLACES_SEARCH_BUDGET (default 8)
      - DETAILED_ROUTE_BUDGET (default 5)
      - FAMILY_ROUTE_BUDGET (default 6)
    """

    def __init__(
        self,
        search_id: str = "default",
        mode: str = "search",  # "search" or "detail"
    ) -> None:
        self.settings = get_settings()
        self.search_id = search_id
        self.mode = mode
        self.summary = SearchRequestSummary(search_id=search_id)

        # Establish budget based on mode
        if mode == "detail":
            self.route_budget = self.settings.DETAILED_ROUTE_BUDGET
            self.places_budget = self.settings.FAMILY_ROUTE_BUDGET
        else:
            self.route_budget = self.settings.ROUTE_SEARCH_BUDGET
            self.places_budget = self.settings.PLACES_SEARCH_BUDGET

    def can_request_route(self) -> bool:
        """Check whether another route API call is within budget."""
        if self.summary.routes_requested >= self.route_budget:
            self.summary.budget_exhausted = True
            logger.warning(
                "[BUDGET EXHAUSTED] Route request budget reached",
                search_id=self.search_id,
                requested=self.summary.routes_requested,
                budget=self.route_budget,
            )
            return False
        return True

    def can_request_places(self) -> bool:
        """Check whether another places API call is within budget."""
        if self.summary.places_requested >= self.places_budget:
            self.summary.budget_exhausted = True
            logger.warning(
                "[BUDGET EXHAUSTED] Places request budget reached",
                search_id=self.search_id,
                requested=self.summary.places_requested,
                budget=self.places_budget,
            )
            return False
        return True

    def record_listings_examined(self, count: int) -> None:
        self.summary.listings_examined += count

    def record_route_call(
        self,
        provider: str,
        cache_hit: bool,
        latency_ms: float = 0.0,
        operation: str = "compute_route",
    ) -> None:
        """Record route request metrics (strictly sanitized)."""
        if cache_hit:
            self.summary.routes_cache_hits += 1
        else:
            self.summary.routes_requested += 1
            if provider.lower() in ("google", "google_routes"):
                self.summary.total_external_requests += 1

        logger.info(
            "[REQUEST METRIC]",
            search_id=self.search_id,
            provider=provider,
            endpoint="routes",
            operation=operation,
            cache_hit=cache_hit,
            cache_miss=not cache_hit,
            latency_ms=round(latency_ms, 1),
        )

    def record_places_call(
        self,
        provider: str,
        cache_hit: bool,
        latency_ms: float = 0.0,
        facility_type: str = "school",
    ) -> None:
        """Record places request metrics (strictly sanitized)."""
        if cache_hit:
            self.summary.places_cache_hits += 1
        else:
            self.summary.places_requested += 1
            if provider.lower() in ("google", "google_places"):
                self.summary.total_external_requests += 1

        logger.info(
            "[REQUEST METRIC]",
            search_id=self.search_id,
            provider=provider,
            endpoint="places",
            operation=f"search_{facility_type}",
            cache_hit=cache_hit,
            cache_miss=not cache_hit,
            latency_ms=round(latency_ms, 1),
        )

    def log_search_report(self) -> Dict[str, int | str | bool | float]:
        """Produce the Task 1 final summary log."""
        data = self.summary.to_dict()
        logger.info(
            "[SEARCH BUDGET SUMMARY]",
            search_id=self.search_id,
            listings_examined=data["listings_examined"],
            routes_requested=data["routes_requested"],
            routes_cache_hits=data["routes_cache_hits"],
            places_requested=data["places_requested"],
            places_cache_hits=data["places_cache_hits"],
            total_external_requests=data["total_external_requests"],
            budget_exhausted=data["budget_exhausted"],
            elapsed_ms=data["elapsed_ms"],
        )
        return data


# Context-local or active budget manager reference for the current request
_ACTIVE_TRACKER: Optional[RequestBudgetManager] = None


def get_current_tracker() -> RequestBudgetManager:
    global _ACTIVE_TRACKER
    if _ACTIVE_TRACKER is None:
        _ACTIVE_TRACKER = RequestBudgetManager("default_session")
    return _ACTIVE_TRACKER


def set_current_tracker(tracker: RequestBudgetManager) -> None:
    global _ACTIVE_TRACKER
    _ACTIVE_TRACKER = tracker


def reset_current_tracker() -> None:
    global _ACTIVE_TRACKER
    _ACTIVE_TRACKER = None
