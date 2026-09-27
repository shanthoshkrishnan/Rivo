"""
RIVO Backend — Observation & Listing Update Schemas
====================================================
Phase 10: Real Rental Observation Acquisition

Schemas for:
  - PATCH /api/v1/rentals/direct/{listing_id}   — listing update + append observation
  - GET  /api/v1/rentals/{listing_id}/history   — observation history
  - POST /api/v1/admin/rentals/collect          — bulk observation import (admin)
  - Bulk CSV/JSON import via scripts.import_rental_observations
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator

from app.core.config import AvailabilityStatus


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/rentals/direct/{listing_id}
# ─────────────────────────────────────────────────────────────────────────────

class DirectListingUpdateRequest(BaseModel):
    """
    Partial update payload for an existing RIVO Direct listing.
    Records a new observation snapshot whenever tracked fields change.
    Provide only the fields you want to update — omitted fields are unchanged.
    """
    rent_monthly: Optional[float] = Field(
        None, gt=0, le=1_000_000,
        description="Updated monthly rent in INR. Triggers an observation record."
    )
    maintenance_monthly: Optional[float] = Field(None, ge=0)
    deposit: Optional[float] = Field(None, ge=0)
    area_sqft: Optional[float] = Field(None, gt=0)
    furnishing: Optional[str] = Field(None, description="unfurnished | semi-furnished | fully-furnished")
    availability_status: Optional[AvailabilityStatus] = None
    notes: Optional[str] = Field(
        None, max_length=512,
        description="Freeform agent/owner note for this update (not published)"
    )

    @field_validator("furnishing")
    @classmethod
    def _normalise_furnishing(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_clean = v.lower().strip().replace(" ", "-")
        if v_clean not in ("unfurnished", "semi-furnished", "fully-furnished"):
            return "unfurnished"
        return v_clean


class DirectListingUpdateResponse(BaseModel):
    """Response after a PATCH update — returns updated listing and new observation summary."""
    listing_id: str
    updated_fields: List[str]
    observation_recorded: bool
    total_observations: int
    current_rent: Optional[float]
    availability_status: str
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/rentals/{listing_id}/history
# ─────────────────────────────────────────────────────────────────────────────

class ObservationRecord(BaseModel):
    """A single point-in-time rental observation snapshot."""
    listing_id: str
    observed_at: datetime
    rent_monthly: float
    availability_status: str
    locality: str
    bhk: int
    area_sqft: Optional[float] = None
    furnishing: Optional[str] = None
    source: str
    changed_fields: List[str] = Field(default_factory=list)
    is_synthetic: bool = False
    is_demo: bool = False
    eligible_for_model: bool = False


class ObservationHistoryResponse(BaseModel):
    """Full observation history for a single listing."""
    listing_id: str
    total_observations: int
    first_observed_at: Optional[datetime] = None
    last_observed_at: Optional[datetime] = None
    observations: List[ObservationRecord]
    eligible_for_model_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Observation Import (CSV/JSON)
# ─────────────────────────────────────────────────────────────────────────────

class BulkObservationRow(BaseModel):
    """
    One row from the bulk import CSV or JSON file.

    Required fields:
      listing_id, locality, bhk, rent_monthly, observed_at, source

    CRITICAL: is_synthetic and is_demo default to False.
    The importer MUST set them correctly.
    Records with is_synthetic=True are NEVER eligible_for_model.
    Records with is_demo=True   are NEVER eligible_for_model.
    """
    listing_id: str = Field(..., min_length=1)
    locality: str = Field(..., min_length=2, max_length=256)
    bhk: int = Field(..., ge=0, le=10)
    rent_monthly: float = Field(..., gt=0, le=1_000_000)
    observed_at: datetime
    source: str = Field(..., min_length=1, max_length=128,
                        description="e.g. 'owner_interview' | 'magicbricks_snapshot_2024-09-01' | 'rivo_direct'")
    area_sqft: Optional[float] = Field(None, gt=0)
    furnishing: Optional[str] = None
    property_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    availability_status: str = "AVAILABLE"
    is_synthetic: bool = False
    is_demo: bool = False
    is_periodic: bool = False
    is_live: bool = False

    @field_validator("observed_at", mode="before")
    @classmethod
    def _parse_dt(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Accept ISO-8601 with or without timezone
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    import warnings
                    warnings.warn(
                        f"observed_at {v!r} has no timezone — assuming UTC",
                        stacklevel=2,
                    )
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                raise ValueError(f"Cannot parse observed_at: {v!r} — use ISO-8601 format")
        raise ValueError(f"observed_at must be ISO-8601 string or datetime, got {type(v).__name__}")


class BulkImportResult(BaseModel):
    """Summary returned by scripts.import_rental_observations."""
    total_rows: int
    accepted: int
    rejected_synthetic: int
    rejected_demo: int
    rejected_validation_error: int
    eligible_for_model: int
    sources: List[str]
    localities: List[str]
    errors: List[str] = Field(default_factory=list)
    import_completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────────────────────────────────────
# Admin collection tool schemas
# ─────────────────────────────────────────────────────────────────────────────

class AdminCollectObservationRequest(BaseModel):
    """
    POST /api/v1/admin/rentals/collect — add a manually verified observation.
    This endpoint is for field agents or admins adding confirmed rental data.
    is_synthetic and is_demo MUST be false.
    """
    listing_id: str = Field(
        ..., min_length=1,
        description="Existing RIVO listing ID or new ad-hoc ID for off-platform observations"
    )
    locality: str = Field(..., min_length=2, max_length=256)
    bhk: int = Field(..., ge=0, le=10)
    rent_monthly: float = Field(..., gt=0, le=1_000_000)
    observed_at: Optional[datetime] = Field(
        None, description="Defaults to now if omitted"
    )
    source: str = Field(
        ..., min_length=1, max_length=128,
        description="Data collection method: 'field_agent' | 'owner_interview' | 'verified_portal'"
    )
    area_sqft: Optional[float] = Field(None, gt=0)
    furnishing: Optional[str] = None
    property_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    availability_status: str = "AVAILABLE"
    notes: Optional[str] = Field(None, max_length=1024)
    # These MUST be false for admin collection — enforced by the endpoint
    is_synthetic: bool = Field(False, description="MUST be false for admin-collected observations")
    is_demo: bool = Field(False, description="MUST be false for admin-collected observations")


class AdminCollectObservationResponse(BaseModel):
    """Response after admin observation submission."""
    accepted: bool
    listing_id: str
    observation_id: str
    eligible_for_model: bool
    total_eligible_observations: int
    model_eligibility_status: str
    message: str


class AdminDataQualityReport(BaseModel):
    """Summary returned by GET /api/v1/admin/rentals/data-quality"""
    total_observations: int
    real_observations: int
    demo_observations: int
    synthetic_observations: int
    eligible_for_model: int
    unique_properties: int
    unique_localities: List[str]
    unique_sources: List[str]
    temporal_span_days: Optional[float]
    model_ready: bool
    model_eligibility_status: str
    observations_needed: int
    # Per-gate progress for the data readiness dashboard (Task 5)
    gate_progress: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Per-gate progress toward model eligibility. "
            "Each gate shows {current, required, pass}. "
            "All gates must pass before ML training is permitted."
        ),
    )
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
