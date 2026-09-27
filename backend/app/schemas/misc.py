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
    facility_status: 'available' | 'unavailable' | 'insufficient_data'
    """
    nearest_name: Optional[str] = None
    nearest_minutes: Optional[float] = None
    meets_threshold: Optional[bool] = None
    distance_m: Optional[float] = None
    facility_status: str = "available"
    source_name: Optional[str] = None


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
    corridor_id: Optional[str] = "cmrl_c4"
    new_stops: List[dict] = Field(
        default_factory=list,
        description="List of {name, lat, lon, route_ids} dicts",
    )
    new_routes: List[dict] = Field(default_factory=list)
    description: str = "Proposed transit scenario"


class HousingScenarioParams(BaseModel):
    """New housing supply site to add."""
    site_locality: Optional[str] = "ambattur"
    site_lat: float = 13.1143
    site_lon: float = 80.1548
    units: int = Field(120, gt=0)
    avg_rent_monthly: float = Field(14000.0, gt=0)
    target_bhk: Optional[str] = "1-2 BHK"
    description: str = "Proposed housing site"


class ScenarioRequest(BaseModel):
    """POST /api/scenarios/evaluate"""
    scenario_type: str = "transit"    # transit | housing
    occupation_key: str = "nurse"
    income_band: str = "median"       # p25 | median | p75
    monthly_income: Optional[float] = None
    commute_threshold_minutes: int = Field(45, ge=10, le=120)
    work_days_per_month: int = Field(26, ge=1, le=31)
    transit_params: Optional[TransitScenarioParams] = None
    housing_params: Optional[HousingScenarioParams] = None


class ScenarioMetrics(BaseModel):
    worker_reach_30min: Optional[int] = None
    worker_reach_45min: Optional[int] = None
    worker_reach_60min: Optional[int] = None
    worker_reach_lower_bound: Optional[int] = None
    worker_reach_upper_bound: Optional[int] = None
    affordable_listings: Optional[int] = None
    commute_median_minutes: Optional[float] = None
    catchment_sqkm: Optional[float] = None


class ScenarioStateMetrics(BaseModel):
    reachable_workers: int
    median_commute_minutes: float
    affordable_listings: int
    monthly_transport_cost: float
    monthly_rent_estimate: float
    monthly_income: float
    housing_burden_pct: float
    transport_burden_pct: float
    cash_burden_pct: float


class ScenarioChangeMetrics(BaseModel):
    workers_reached: int
    commute_minutes_saved_per_trip: float
    affordable_listings_added: int
    monthly_transport_savings: float
    annual_transport_savings: float


class ScenarioWorkerImpact(BaseModel):
    time_saved_per_trip_minutes: float
    work_days_per_month: int
    monthly_time_saved_hours: float
    annual_time_saved_hours: float
    monthly_money_saved: float
    annual_money_saved: float


class ScenarioConfidence(BaseModel):
    level: str = "MEDIUM"
    data_type: str = "ESTIMATED"
    sources: List[str] = Field(default_factory=list)
    disclaimer: str = "Scenario results are estimates, not forecasts."


class ScenarioMapData(BaseModel):
    corridors: List[dict] = Field(default_factory=list)
    stations: List[dict] = Field(default_factory=list)
    catchment_circles: List[dict] = Field(default_factory=list)
    housing_sites: List[dict] = Field(default_factory=list)
    employment_clusters: List[dict] = Field(default_factory=list)
    current_reachable_area: List[List[float]] = Field(default_factory=list)
    proposed_reachable_area: List[List[float]] = Field(default_factory=list)


class ScenarioResponse(BaseModel):
    scenario_id: str
    occupation_key: str
    scenario_type: str = "transit"
    scenario_name: str = "CMRL Phase II Scenario"
    scenario_status_label: str = "Scenario simulation — not current service"
    project_status: str = "CMRL Phase-II under construction (target completion late 2028)"
    before: ScenarioMetrics
    after: ScenarioMetrics
    current: Optional[ScenarioStateMetrics] = None
    proposed: Optional[ScenarioStateMetrics] = None
    change: Optional[ScenarioChangeMetrics] = None
    worker_impact: Optional[ScenarioWorkerImpact] = None
    confidence_detail: Optional[ScenarioConfidence] = None
    map_data: Optional[ScenarioMapData] = None
    delta_worker_reach_45min: Optional[int] = None
    delta_affordable_listings: Optional[int] = None
    confidence: str = "MEDIUM"
    methodology: Optional[str] = None
    affected_neighborhoods: List[str] = Field(default_factory=list)
    computed_at: datetime
    data_freshness: DataFreshness = DataFreshness.ESTIMATED
