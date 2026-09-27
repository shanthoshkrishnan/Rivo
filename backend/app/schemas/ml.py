"""
RIVO Backend — Rent Intelligence & ML Schemas
==============================================
Pydantic contracts for:
  - Model eligibility evaluation
  - Rent percentile estimation (p25, p50, p75)
  - Asking rent vs expected market range comparisons
  - Spatial rent cell representation
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import ConfidenceLevel, DataFreshness


class ModelEligibilityThresholds(BaseModel):
    min_real_observations: int = Field(default=50, description="Minimum non-synthetic observations required")
    min_unique_properties: int = Field(default=30, description="Minimum unique property IDs")
    min_localities: int = Field(default=5, description="Minimum unique localities covered")
    min_bhk_classes: int = Field(default=3, description="Minimum BHK classes (e.g. 1, 2, 3 BHK)")
    min_source_count: int = Field(default=2, description="Minimum independent data sources")
    max_synthetic_ratio: float = Field(default=0.10, description="Maximum allowable synthetic/demo data fraction")
    min_temporal_span_days: int = Field(default=7, description="Minimum days of temporal variation")


class ModelEligibilityResult(BaseModel):
    is_eligible: bool = Field(..., description="Whether data meets all safeguards for ML training")
    status: str = Field(..., description="READY | NOT_READY_INSUFFICIENT_DATA")
    reasons: List[str] = Field(default_factory=list, description="Detailed pass/fail reasons for each safeguard")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Observed dataset statistics")
    thresholds: Dict[str, Any] = Field(default_factory=dict, description="Configured engineering safeguard thresholds")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class RentPredictionRequest(BaseModel):
    bhk: int = Field(default=2, ge=1, le=5)
    area_sqft: Optional[float] = Field(default=None, ge=100.0, le=10000.0)
    property_type: Optional[str] = Field(default="flat")
    furnishing: Optional[str] = Field(default="semi-furnished")
    locality: Optional[str] = Field(default=None)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    h3_index: Optional[str] = Field(default=None)


class RentPredictionResponse(BaseModel):
    rent_p25: Optional[float] = None
    rent_p50: Optional[float] = None
    rent_p75: Optional[float] = None
    price_per_sqft_median: Optional[float] = None
    model_name: str = "rivo_rent_engine"
    model_version: str = "baseline_v1"
    confidence: str = "INSUFFICIENT_DATA"   # HIGH / MEDIUM / LOW / INSUFFICIENT_DATA
    method: str = "hierarchical_median_fallback"
    data_freshness: str = "MODELLED"
    insufficient_data: bool = False
    explanation: str = ""
    transit_features: Optional[Dict[str, Any]] = None


class MarketComparison(BaseModel):
    asking_rent: float
    expected_range_min: Optional[float] = None
    expected_range_max: Optional[float] = None
    median_estimate: Optional[float] = None
    market_position: str = "INSUFFICIENT_DATA"   # WITHIN_RANGE | ABOVE_RANGE | BELOW_RANGE | INSUFFICIENT_DATA
    market_position_label: str = "Market range unavailable"
    confidence: str = "INSUFFICIENT_DATA"
    model_version: str = "none"


class RentCellOut(BaseModel):
    h3_index: str
    resolution: int = 8
    locality: Optional[str] = None
    rent_p25: Optional[float] = None
    rent_p50: Optional[float] = None
    rent_p75: Optional[float] = None
    price_per_sqft_median: Optional[float] = None
    observation_count: int = 0
    unique_properties: int = 0
    source_count: int = 0
    latest_observation: Optional[datetime] = None
    confidence: str = "INSUFFICIENT_DATA"
    model_version: str = "none"
