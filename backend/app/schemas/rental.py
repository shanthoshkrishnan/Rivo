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

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import ConfidenceLevel, DataFreshness


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
    geocode_confidence: Optional[ConfidenceLevel] = None
    # ML model output (nullable until pipeline runs)
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

    Hard constraints (reject if violated):
      - max_rent_monthly
      - bhk (if specified)
      - property_type (if specified)

    Soft preferences handled downstream in the recommendation engine.
    """
    # Hard constraints
    max_rent_monthly: float = Field(..., gt=0, description="Hard maximum rent in INR")
    bhk: Optional[int] = Field(None, ge=1, le=10)
    property_type: Optional[str] = None    # flat | house | pg | studio

    # Location filter
    locality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = Field(10.0, gt=0, le=50)

    # Availability
    available_only: bool = True

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=1000)

    @field_validator("property_type")
    @classmethod
    def _normalise_property_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.lower().strip()


# ─────────────────────────────────────────────────────────────────────────────
# Paginated response envelope
# ─────────────────────────────────────────────────────────────────────────────
class PaginatedRentalResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data_freshness: DataFreshness
    results: List[RentalListingOut]
