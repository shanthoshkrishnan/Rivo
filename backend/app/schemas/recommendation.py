"""
RIVO Backend — Pydantic Schemas for Recommendations
=====================================================
RecommendationRequest  — POST /api/recommendations/search
RecommendationResult   — single scored/explained listing
RecommendationResponse — paginated results

Hard constraints are validated here before any DB or route call.
The pipeline guarantees:
  1. Only listings that pass hard constraints reach the scorer.
  2. Soft preferences affect the ranking, not the hard filter.
  3. Every result includes an explainability block.

Family layer:
  adults, children, child_age_bands, school_max_minutes,
  hospital_max_minutes, pharmacy_max_minutes
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.config import ConfidenceLevel, DataFreshness
from app.schemas.routing import RouteResult


# ─────────────────────────────────────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────────────────────────────────────
class FamilyContext(BaseModel):
    """
    Family accessibility layer.
    Child names are NOT stored — only counts and age bands.
    Thresholds are soft by default; make them hard only if user sets
    require_within_threshold=True.
    """
    adults: int = Field(1, ge=1, le=10)
    children: int = Field(0, ge=0, le=10)
    # e.g. ["0-5", "6-12"]  — used to determine school type needed
    child_age_bands: List[str] = Field(default_factory=list)
    # Maximum travel time to nearest facility (minutes)
    school_max_minutes: Optional[int] = Field(None, ge=1, le=120)
    hospital_max_minutes: Optional[int] = Field(None, ge=1, le=120)
    pharmacy_max_minutes: Optional[int] = Field(None, ge=1, le=120)
    # Whether to treat facility thresholds as hard constraints
    require_within_threshold: bool = False


class WorkerContext(BaseModel):
    """Worker / income context for affordability calculations."""
    occupation_key: Optional[str] = None        # e.g. "nurse", "teacher"
    household_income_monthly: Optional[float] = Field(None, gt=0)  # INR
    # income percentile band: "p25" | "median" | "p75"
    income_band: Optional[str] = None


class RecommendationRequest(BaseModel):
    """
    POST /api/recommendations/search

    Hard constraints → soft preferences → family layer → routing
    All hard constraints are validated here; the service rejects them
    before any expensive operation.
    """
    # ── Hard constraints ──────────────────────────────────────────────────────
    max_rent_monthly: float = Field(..., gt=0, description="Hard maximum rent (INR)")
    bhk: Optional[int] = Field(None, ge=1, le=10)
    property_type: Optional[str] = None

    # ── Workplace (routing origin) ────────────────────────────────────────────
    workplace_lat: float = Field(..., ge=-90, le=90)
    workplace_lon: float = Field(..., ge=-180, le=180)
    workplace_label: Optional[str] = None

    # ── Commute constraints ───────────────────────────────────────────────────
    max_commute_minutes: int = Field(60, ge=5, le=240)
    max_transfers: Optional[int] = Field(None, ge=0, le=5)
    max_walk_minutes: Optional[int] = Field(None, ge=1, le=60)
    preferred_modes: List[str] = Field(
        default_factory=lambda: ["TRANSIT", "TWO_WHEELER", "DRIVE"]
    )

    # ── Worker / income ───────────────────────────────────────────────────────
    worker: Optional[WorkerContext] = None

    # ── Family ───────────────────────────────────────────────────────────────
    family: Optional[FamilyContext] = None

    # ── Search area ───────────────────────────────────────────────────────────
    search_lat: Optional[float] = None
    search_lon: Optional[float] = None
    search_radius_km: float = Field(15.0, gt=0, le=50)

    # ── Work days (affects monthly transport cost) ────────────────────────────
    work_days_per_month: int = Field(22, ge=1, le=31)

    # ── Response options ──────────────────────────────────────────────────────
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=50)

    @model_validator(mode="after")
    def _validate_coordinates(self) -> "RecommendationRequest":
        if self.search_lat is None:
            self.search_lat = self.workplace_lat
        if self.search_lon is None:
            self.search_lon = self.workplace_lon
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────
class FacilityAccess(BaseModel):
    """Travel time and count for a nearby facility type."""
    nearest_minutes: Optional[float] = None
    count_within_threshold: Optional[int] = None
    meets_threshold: Optional[bool] = None


class AffordabilityBreakdown(BaseModel):
    """
    Full cost breakdown for one listing × worker combination.
    Algorithms sourced directly from ALGORITHMS.md sections 5–9.
    """
    monthly_rent: Optional[float] = None
    monthly_maintenance: Optional[float] = None
    monthly_transport_cost: Optional[float] = None
    monthly_total_cost: Optional[float] = None
    # housing_burden = rent / income
    housing_burden_pct: Optional[float] = None
    # transport_burden = transport / income
    transport_burden_pct: Optional[float] = None
    # cash_burden = (rent + maintenance + transport) / income
    cash_burden_pct: Optional[float] = None
    # time_tax = one_way_min × 2 × work_days / 60
    monthly_commute_hours: Optional[float] = None


class ExplainabilityBlock(BaseModel):
    """
    Human-readable reasons generated from real data, NOT an LLM.
    Positive reasons and disqualifying factors are separated.
    """
    passes_all_hard_constraints: bool
    positive_reasons: List[str] = Field(default_factory=list)
    negative_reasons: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    data_freshness: DataFreshness = DataFreshness.ESTIMATED


class RecommendationResult(BaseModel):
    """A single scored and explained rental listing."""
    listing_id: str
    provider: str
    # Core listing fields
    locality: Optional[str] = None
    bhk: Optional[int] = None
    area_sqft: Optional[float] = None
    furnishing: Optional[str] = None
    property_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rent_monthly: Optional[float] = None
    maintenance_monthly: Optional[float] = None
    # Routing
    best_route: Optional[RouteResult] = None
    all_routes: List[RouteResult] = Field(default_factory=list)
    # Affordability
    affordability: Optional[AffordabilityBreakdown] = None
    # Family facilities
    school_access: Optional[FacilityAccess] = None
    hospital_access: Optional[FacilityAccess] = None
    pharmacy_access: Optional[FacilityAccess] = None
    # Scoring
    score_total: Optional[float] = None
    score_components: dict = Field(default_factory=dict)
    # Explainability
    explainability: Optional[ExplainabilityBlock] = None
    # Metadata
    data_freshness: DataFreshness = DataFreshness.ESTIMATED
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class RecommendationResponse(BaseModel):
    """Paginated recommendation results."""
    total: int
    page: int
    page_size: int
    results: List[RecommendationResult]
    search_metadata: dict = Field(default_factory=dict)
