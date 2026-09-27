"""
RIVO Backend — Pydantic Schemas for Rental Listings
=====================================================
These schemas define the API contract for rental data.

Separation of concerns:
  RentalListingBase   — shared fields
  RentalListingCreate — ingest payload (from providers/scrapers)
  RentalListingDB     — full DB record returned to internal services
  RentalListingOut    — public API response (omits internal fields)
  RentalSearchParams  — validated query parameters for /api/rentals/search

All money values are in INR.
All distances are in metres unless suffixed _km.
All times are in seconds unless suffixed _minutes or _hours.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import (
    AvailabilityStatus,
    ConfidenceLevel,
    DataFreshness,
    VerificationStatus,
)

# ─────────────────────────────────────────────────────────────────────────────
# Chennai Pilot Spatial Bounding Box & Geocode Validation
# ─────────────────────────────────────────────────────────────────────────────
CHENNAI_LAT_MIN = 12.75
CHENNAI_LAT_MAX = 13.35
CHENNAI_LON_MIN = 80.00
CHENNAI_LON_MAX = 80.35


def validate_chennai_coordinates(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
    """Validate that coordinates fall strictly inside the Chennai pilot bounds."""
    if not (CHENNAI_LAT_MIN <= lat <= CHENNAI_LAT_MAX):
        return False, f"Latitude {lat:.4f} is outside Chennai pilot bounds [{CHENNAI_LAT_MIN}, {CHENNAI_LAT_MAX}]"
    if not (CHENNAI_LON_MIN <= lon <= CHENNAI_LON_MAX):
        return False, f"Longitude {lon:.4f} is outside Chennai pilot bounds [{CHENNAI_LON_MIN}, {CHENNAI_LON_MAX}]"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# Shared base
# ─────────────────────────────────────────────────────────────────────────────
class RentalListingBase(BaseModel):
    listing_id: str
    provider: str
    city: str = "Chennai"
    locality_raw: Optional[str] = None
    locality_normalized: Optional[str] = None
    address_raw: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocode_confidence: Optional[ConfidenceLevel] = None
    rent_monthly: Optional[float] = Field(None, ge=0)
    maintenance_monthly: Optional[float] = Field(None, ge=0)
    deposit: Optional[float] = Field(None, ge=0)
    brokerage: Optional[float] = Field(None, ge=0)
    property_type: Optional[str] = None
    bhk: Optional[int] = Field(None, ge=0, le=10)
    bedrooms: Optional[int] = Field(None, ge=0)
    area_sqft: Optional[float] = Field(None, ge=0)
    furnishing: Optional[str] = None   # unfurnished | semi-furnished | fully-furnished
    bathrooms: Optional[int] = Field(None, ge=0)
    tenant_preference: Optional[str] = None
    is_available: bool = True
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    duplicate_cluster_id: Optional[str] = None
    is_canonical: bool = True
    consent_given: bool = True


class RentalListingCreate(RentalListingBase):
    """Schema for ingesting a listing from a provider or scraper."""
    observed_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    url_hash: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    data_freshness: DataFreshness = DataFreshness.PERIODIC


class RentalListingOut(RentalListingBase):
    """Public API response schema."""
    id: UUID
    h3_index: Optional[str] = None
    gcc_ward: Optional[str] = None
    model_rent_p25: Optional[float] = None
    model_rent_p50: Optional[float] = None
    model_rent_p75: Optional[float] = None
    data_confidence: Optional[ConfidenceLevel] = None
    data_freshness: DataFreshness = DataFreshness.PERIODIC
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Search parameters
# ─────────────────────────────────────────────────────────────────────────────
class RentalSearchParams(BaseModel):
    """
    Query parameters for GET /api/rentals/search.
    """
    min_rent_monthly: Optional[float] = Field(None, ge=0, description="Hard minimum rent in INR")
    max_rent_monthly: float = Field(..., gt=0, description="Hard maximum rent in INR")
    bhk: Optional[int] = Field(None, ge=1, le=10)
    property_type: Optional[str] = None    # flat | house | pg | studio

    locality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = Field(10.0, gt=0, le=50)

    available_only: bool = True
    source_categories: Optional[List[str]] = Field(
        default=None,
        description="Filter by source tier: CURRENT, RECENT, PERIODIC, DEMO",
    )

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=1000)

    @field_validator("property_type")
    @classmethod
    def _normalise_property_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.lower().strip()


# ─────────────────────────────────────────────────────────────────────────────
# First-Party RIVO Direct Submission Request
# ─────────────────────────────────────────────────────────────────────────────
class DirectRentalSubmissionRequest(BaseModel):
    locality: str = Field(..., min_length=2, max_length=128)
    address: Optional[str] = Field(None, max_length=256)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    rent_monthly: float = Field(..., gt=0, le=1_000_000)
    maintenance_monthly: float = Field(0.0, ge=0)
    deposit: Optional[float] = Field(None, ge=0)
    bhk: int = Field(..., ge=0, le=10)
    area_sqft: Optional[float] = Field(None, gt=0)
    furnishing: Optional[str] = None
    property_type: Optional[str] = "flat"
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    consent_to_publish: bool = Field(
        True,
        description="Explicit owner/agent consent to publish listing on RIVO",
    )

    @field_validator("furnishing")
    @classmethod
    def _check_furnishing(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_clean = v.lower().strip().replace(" ", "-")
        if v_clean not in ("unfurnished", "semi-furnished", "fully-furnished"):
            return "unfurnished"
        return v_clean


# ─────────────────────────────────────────────────────────────────────────────
# Market Summary & Admin Schemas
# ─────────────────────────────────────────────────────────────────────────────
class MarketSummaryResponse(BaseModel):
    listing_count: int = 0
    listings_observed: int = 0
    observation_count: int = 0
    median: Optional[float] = None
    median_asking_rent: Optional[float] = None
    p25: Optional[float] = None
    rent_p25: Optional[float] = None
    p75: Optional[float] = None
    rent_p75: Optional[float] = None
    by_bhk: Dict[int, float] = Field(default_factory=dict)
    median_by_bhk: Dict[int, float] = Field(default_factory=dict)
    by_locality: Dict[str, float] = Field(default_factory=dict)
    median_by_locality: Dict[str, float] = Field(default_factory=dict)
    source_count: int = 0
    data_as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: str = "INSUFFICIENT_DATA"
    insufficient_data: bool = False



class RentalAdminSummary(BaseModel):
    total_listings: int
    current_listings: int
    recent_listings: int
    periodic_listings: int
    demo_listings: int
    stale_listings: int
    unknown_availability: int
    duplicate_clusters: int
    provider_health: Dict[str, bool]
    last_refresh: Optional[datetime] = None
    records_ingested: int


# ─────────────────────────────────────────────────────────────────────────────
# Paginated response envelope
# ─────────────────────────────────────────────────────────────────────────────
class PaginatedRentalResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data_freshness: DataFreshness
    results: List[RentalListingOut]

