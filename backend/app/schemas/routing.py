"""
RIVO Backend — Pydantic Schemas for Routing
============================================
RouteRequest  — what the caller provides
RouteResult   — what a routing provider returns for one mode
RouteComparison — all modes compared for one origin→destination pair

Modes: TRANSIT | DRIVE | TWO_WHEELER | WALK
Providers: google | otp | mock

The API always returns multiple modes so the UI can show:
  Fastest / Cheapest / Fewest transfers / Preferred badges.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.config import DataFreshness


class RouteRequest(BaseModel):
    """
    POST /api/routes/compare request body.

    departure_time is optional; defaults to next morning peak.
    mode_preferences lets the user hint preferred modes without
    hard-excluding others.
    """
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lon: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lon: float = Field(..., ge=-180, le=180)
    departure_time: Optional[datetime] = None
    # requested modes; empty = compute all available
    modes: List[str] = Field(
        default_factory=lambda: ["TRANSIT", "DRIVE", "TWO_WHEELER", "WALK"]
    )


class RouteResult(BaseModel):
    """
    Route result for a single mode from a single provider.
    All fields from DATA_SOURCES.md route_result block.
    """
    mode: str                         # TRANSIT | DRIVE | TWO_WHEELER | WALK
    provider: str                     # google | otp | mock
    distance_m: Optional[float] = None
    duration_seconds: Optional[int] = None
    walk_seconds: Optional[int] = None
    wait_seconds: Optional[int] = None
    in_vehicle_seconds: Optional[int] = None
    transfer_count: Optional[int] = None
    fare_amount: Optional[float] = None        # INR one-way
    route_geometry: Optional[str] = None       # GeoJSON LineString
    observed_at: Optional[datetime] = None
    data_freshness: DataFreshness = DataFreshness.LIVE
    # UI badges
    is_fastest: bool = False
    is_cheapest: bool = False
    is_fewest_transfers: bool = False

    @property
    def duration_minutes(self) -> Optional[float]:
        if self.duration_seconds is None:
            return None
        return round(self.duration_seconds / 60, 1)

    @property
    def monthly_commute_cost(self) -> Optional[float]:
        """
        Monthly commute cost = (outbound + return fare) × work_days.
        Uses default 22 work days; caller can override.
        """
        if self.fare_amount is None:
            return None
        from app.core.config import get_settings
        work_days = get_settings().DEFAULT_WORK_DAYS_PER_MONTH
        return round(self.fare_amount * 2 * work_days, 2)


class RouteComparison(BaseModel):
    """All modes compared for one origin→destination pair."""
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    routes: List[RouteResult]
    computed_at: datetime
    data_freshness: DataFreshness = DataFreshness.LIVE
