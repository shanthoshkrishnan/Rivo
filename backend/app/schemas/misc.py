"""
RIVO Backend — Pydantic Schemas for Facilities, Workers & Data Sources
=======================================================================
FacilityOut       — public response for a school/hospital/pharmacy
WorkerOccupation  — list item for GET /api/workers/occupations
IncomeProfileOut  — income percentile data per occupation
DataSourceOut     — public response for GET /api/data/sources
ScenarioRequest   — POST /api/scenarios/evaluate
ScenarioResponse  — before/after accessibility metrics
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import ConfidenceLevel, DataFreshness


# ─────────────────────────────────────────────────────────────────────────────
# Facility access result (used inside recommendation results)
# ─────────────────────────────────────────────────────────────────────────────
class FacilityAccess(BaseModel):
    """
    Whether a particular facility type meets the family's threshold.
    Used in RecommendationResult for school/hospital/pharmacy access.
    """
    nearest_minutes: Optional[float] = None
    meets_threshold: Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# Facilities
# ─────────────────────────────────────────────────────────────────────────────
class FacilityOut(BaseModel):
    id: UUID
    name: str
    facility_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    distance_m: Optional[float] = None        # distance from search origin
    travel_time_minutes: Optional[float] = None
    data_freshness: DataFreshness
    source_name: str

    model_config = {"from_attributes": True}


class FacilitySearchParams(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    facility_type: str                        # school | hospital | pharmacy
    radius_km: float = Field(5.0, gt=0, le=20)
    limit: int = Field(10, ge=1, le=50)


class FacilityNearbyResponse(BaseModel):
    facility_type: str
    results: List[FacilityOut]
    data_freshness: DataFreshness


# ─────────────────────────────────────────────────────────────────────────────
# Workers / Occupations
# ─────────────────────────────────────────────────────────────────────────────
class WorkerOccupationOut(BaseModel):
    occupation_key: str
    occupation_label: str
    nic_code: Optional[str] = None
    description: Optional[str] = None


class IncomeProfileOut(BaseModel):
    occupation_key: str
    geography_level: str
    income_p25: Optional[float] = None
    income_median: Optional[float] = None
    income_p75: Optional[float] = None
    sample_size: Optional[int] = None
    confidence: Optional[ConfidenceLevel] = None
    survey_year: Optional[int] = None
    data_freshness: DataFreshness
    source_name: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Data Sources
# ─────────────────────────────────────────────────────────────────────────────
class DataSourceOut(BaseModel):
    id: UUID
    source_name: str
    layer: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    license: Optional[str] = None
    attribution: Optional[str] = None
    data_freshness: Optional[DataFreshness] = None
    update_frequency: Optional[str] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Scenarios
# ─────────────────────────────────────────────────────────────────────────────
class TransitScenarioParams(BaseModel):
    """New transit stops/routes to add to the network."""
    new_stops: List[dict] = Field(
        default_factory=list,
        description="List of {name, lat, lon, route_ids} dicts",
    )
    new_routes: List[dict] = Field(default_factory=list)
    description: str = "Proposed transit scenario"


class HousingScenarioParams(BaseModel):
    """New housing supply site to add."""
    site_lat: float
    site_lon: float
    units: int = Field(..., gt=0)
    avg_rent_monthly: float = Field(..., gt=0)
    description: str = "Proposed housing site"


class ScenarioRequest(BaseModel):
    """POST /api/scenarios/evaluate"""
    scenario_type: str    # transit | housing
    occupation_key: str
    transit_params: Optional[TransitScenarioParams] = None
    housing_params: Optional[HousingScenarioParams] = None
    commute_threshold_minutes: int = Field(45, ge=10, le=120)


class ScenarioMetrics(BaseModel):
    worker_reach_30min: Optional[int] = None
    worker_reach_45min: Optional[int] = None
    worker_reach_60min: Optional[int] = None
    affordable_listings: Optional[int] = None
    commute_median_minutes: Optional[float] = None


class ScenarioResponse(BaseModel):
    scenario_id: str
    occupation_key: str
    before: ScenarioMetrics
    after: ScenarioMetrics
    delta_worker_reach_45min: Optional[int] = None
    delta_affordable_listings: Optional[int] = None
    computed_at: datetime
    data_freshness: DataFreshness = DataFreshness.ESTIMATED
