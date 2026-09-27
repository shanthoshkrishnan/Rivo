"""
RIVO Backend — Pydantic Schemas for Routing
============================================
RouteRequest  — what the caller provides
RouteResult   — what a routing provider returns for one mode
RouteStep     — one step inside a transit itinerary
RouteComparison — all modes compared for one origin→destination pair

Modes: TRANSIT | DRIVE | TWO_WHEELER | WALK
Providers: google | gtfs | otp | mock

Phase 3:
  - RouteStep added for full itinerary (leg-by-leg).
  - TransitDetails added for transit-specific step info.
  - TrafficInfo added for drive/two-wheeler live traffic.
  - RouteResult extended with steps, departure_time, arrival_time,
    walking_seconds, waiting_seconds, in_vehicle_seconds, and
    cost fields (monthly_commute_cost, monthly_commute_hours).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field

from app.core.config import DataFreshness


# ─────────────────────────────────────────────────────────────────────────────
# Transit step detail (populated by Google Routes and OTP)
# ─────────────────────────────────────────────────────────────────────────────
class TransitDetails(BaseModel):
    """
    Detailed transit info for one transit leg (bus / metro / train).
    All fields are Optional — not every provider returns every field.
    DO NOT invent values; leave None if not returned by the provider.
    """
    agency: Optional[str] = None           # e.g. "MTC" or "CMRL"
    line: Optional[str] = None             # full route name
    line_short_name: Optional[str] = None  # e.g. "21B"
    vehicle_type: Optional[str] = None     # BUS | HEAVY_RAIL | SUBWAY | FERRY
    headsign: Optional[str] = None         # destination shown on board
    departure_stop: Optional[str] = None   # boarding stop name
    arrival_stop: Optional[str] = None     # alighting stop name
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    num_stops: Optional[int] = None        # number of intermediate stops


class RouteStep(BaseModel):
    """
    One step inside a door-to-door itinerary.

    type:
      WALK      — walking portion
      TRANSIT   — bus / metro / train
      WAIT      — waiting at stop (if provider returns it)
      DRIVE     — driving portion
    """
    type: str                              # WALK | TRANSIT | WAIT | DRIVE
    instruction: Optional[str] = None     # human-readable e.g. "Walk to Guindy Metro"
    duration_seconds: Optional[int] = None
    distance_m: Optional[float] = None
    polyline: Optional[str] = None        # encoded polyline for this step
    transit: Optional[TransitDetails] = None   # only set when type=TRANSIT


# ─────────────────────────────────────────────────────────────────────────────
# Traffic info (DRIVE / TWO_WHEELER)
# ─────────────────────────────────────────────────────────────────────────────
class TrafficInfo(BaseModel):
    """
    Live vs historical traffic info for road-based modes.
    traffic_status:
      LIVE_TRAFFIC       — returned from a live traffic-aware routing call
      HISTORICAL         — based on historical speed patterns
    """
    normal_duration_seconds: Optional[int] = None
    traffic_duration_seconds: Optional[int] = None  # None → traffic not available
    traffic_status: Optional[str] = None            # LIVE_TRAFFIC | HISTORICAL


# ─────────────────────────────────────────────────────────────────────────────
# Route Request
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# Route Result
# ─────────────────────────────────────────────────────────────────────────────
class RouteResult(BaseModel):
    """
    Route result for a single mode from a single provider.

    Phase 3 additions:
      - steps: full itinerary (walk → transit → walk)
      - departure_time / arrival_time
      - walking_seconds / waiting_seconds / in_vehicle_seconds
      - traffic: live traffic info for road modes
      - source_label: human-readable data label for UI provenance panel
    """
    mode: str                         # TRANSIT | DRIVE | TWO_WHEELER | WALK
    provider: str                     # google | gtfs | otp | mock
    distance_m: Optional[float] = None
    duration_seconds: Optional[int] = None
    walk_seconds: Optional[int] = None
    wait_seconds: Optional[int] = None
    in_vehicle_seconds: Optional[int] = None
    transfer_count: Optional[int] = None
    fare_amount: Optional[float] = None        # INR one-way
    route_geometry: Optional[str] = None       # encoded polyline (full route)
    observed_at: Optional[datetime] = None
    data_freshness: DataFreshness = DataFreshness.LIVE

    # Phase 3: full itinerary steps
    steps: List[RouteStep] = Field(default_factory=list)

    # Phase 3: departure / arrival times (from Google or OTP)
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None

    # Phase 3: traffic info for DRIVE / TWO_WHEELER
    traffic: Optional[TrafficInfo] = None

    # Phase 3: source label for provenance panel
    # Phase 3: source label for provenance panel
    source_label: Optional[str] = None   # e.g. "Google Routes API" / "CUMTA GTFS"
    transit_summary: Optional[str] = None # e.g. "8 min walk + 6 min wait + 18 min metro + 5 min walk"
    is_anomaly: bool = False

    # UI badges
    is_fastest: bool = False
    is_cheapest: bool = False
    is_fewest_transfers: bool = False

    @computed_field
    @property
    def duration_minutes(self) -> Optional[float]:
        if self.duration_seconds is None:
            return None
        return round(self.duration_seconds / 60, 1)

    @computed_field
    @property
    def distance_km(self) -> Optional[float]:
        if self.distance_m is None:
            return None
        return round(self.distance_m / 1000.0, 1)

    @computed_field
    @property
    def duration_min(self) -> Optional[int]:
        if self.duration_seconds is None:
            return None
        return int(round(self.duration_seconds / 60.0))

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

    @property
    def monthly_commute_hours(self) -> Optional[float]:
        """
        Time tax: one_way_minutes × 2 × work_days / 60.
        Displayed separately — never silently converted to money.
        """
        if self.duration_seconds is None:
            return None
        from app.core.config import get_settings
        work_days = get_settings().DEFAULT_WORK_DAYS_PER_MONTH
        return round(self.duration_seconds / 60 * 2 * work_days / 60, 1)

    @computed_field
    @property
    def distance_meters(self) -> Optional[float]:
        """Convenience alias for distance_m."""
        return self.distance_m

    @computed_field
    @property
    def polyline(self) -> Optional[str]:
        """Convenience alias for route_geometry."""
        return self.route_geometry


# ─────────────────────────────────────────────────────────────────────────────
# Route Comparison
# ─────────────────────────────────────────────────────────────────────────────
class RouteComparison(BaseModel):
    """All modes compared for one origin→destination pair."""
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    routes: List[RouteResult]
    computed_at: datetime
    data_freshness: DataFreshness = DataFreshness.LIVE
