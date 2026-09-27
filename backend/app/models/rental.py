"""
RIVO Backend — Rental Listing ORM Model
=========================================
Maps to the `rental_listings` table in PostgreSQL + PostGIS.

Design decisions
----------------
* `geom` stores the PostGIS geometry (POINT, SRID 4326 / WGS-84).
  This enables spatial queries (ST_DWithin, ST_Distance, etc.).
* `h3_index` at resolution 9 (~174 m hex) allows cheap hex-level
  aggregation without full spatial joins.
* Raw values (locality_raw, rent_monthly_raw) are preserved alongside
  normalised values so the original data can always be audited.
* `data_confidence` uses HIGH / MEDIUM / LOW — never an opaque float.
* `duplicate_cluster_id` groups near-duplicate listings detected by
  the deduplication algorithm.
* Rent model outputs (p25/p50/p75) are nullable; they are filled once
  the ML pipeline runs — never fabricated.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RentalListing(Base):
    """
    A single rental listing as ingested from a provider.

    Every field follows the canonical schema defined in DATA_SOURCES.md.
    The table enforces uniqueness on (provider, listing_id) so re-ingesting
    the same listing updates rather than duplicates it.
    """

    __tablename__ = "rental_listings"
    __table_args__ = (
        UniqueConstraint("provider", "listing_id", name="uq_provider_listing"),
    )

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Provider metadata ────────────────────────────────────────────────────
    listing_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # freshness: LIVE | PERIODIC | ESTIMATED | HISTORICAL | LOW_DATA
    data_freshness: Mapped[str] = mapped_column(String(32), nullable=False, default="PERIODIC")

    # ── Temporal ─────────────────────────────────────────────────────────────
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # ── Location ─────────────────────────────────────────────────────────────
    city: Mapped[str] = mapped_column(String(64), nullable=False, default="Chennai", index=True)
    locality_raw: Mapped[Optional[str]] = mapped_column(String(256))
    locality_normalized: Mapped[Optional[str]] = mapped_column(String(256), index=True)
    address_raw: Mapped[Optional[str]] = mapped_column(Text)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    # PostGIS geometry column (POINT, WGS-84); nullable until geocoded
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    # H3 index at resolution 9 for hex-level aggregation
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    # GCC ward code from GCC GIS 2025
    gcc_ward: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    geocode_confidence: Mapped[Optional[str]] = mapped_column(String(16))   # HIGH/MEDIUM/LOW

    # ── Rent & costs ─────────────────────────────────────────────────────────
    rent_monthly: Mapped[Optional[float]] = mapped_column(Float, index=True)
    rent_monthly_raw: Mapped[Optional[float]] = mapped_column(Float)        # before normalisation
    maintenance_monthly: Mapped[Optional[float]] = mapped_column(Float)
    deposit: Mapped[Optional[float]] = mapped_column(Float)
    brokerage: Mapped[Optional[float]] = mapped_column(Float)

    # ── Property attributes ──────────────────────────────────────────────────
    property_type: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    bhk: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    area_sqft: Mapped[Optional[float]] = mapped_column(Float)
    furnishing: Mapped[Optional[str]] = mapped_column(String(32))   # unfurnished/semi/fully
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer)
    tenant_preference: Mapped[Optional[str]] = mapped_column(String(128))

    # ── Deduplication ────────────────────────────────────────────────────────
    url_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    duplicate_cluster_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=True)   # primary in cluster

    # ── ML rent model outputs ────────────────────────────────────────────────
    # Filled by the rent estimation pipeline; null until then.
    model_rent_p25: Mapped[Optional[float]] = mapped_column(Float)
    model_rent_p50: Mapped[Optional[float]] = mapped_column(Float)
    model_rent_p75: Mapped[Optional[float]] = mapped_column(Float)
    data_confidence: Mapped[Optional[str]] = mapped_column(String(16))   # HIGH/MEDIUM/LOW

    # ── Source registry link ─────────────────────────────────────────────────
    source_name: Mapped[Optional[str]] = mapped_column(String(128))
    source_url: Mapped[Optional[str]] = mapped_column(Text)

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<RentalListing provider={self.provider!r} "
            f"listing_id={self.listing_id!r} "
            f"bhk={self.bhk} rent={self.rent_monthly}>"
        )


class RentalObservation(Base):
    """
    Empirical rental price observation over time.
    Preserves raw asking rents, source provenance, and model eligibility.
    """
    __tablename__ = "rental_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rent_monthly: Mapped[float] = mapped_column(Float, nullable=False)
    rent_monthly_raw: Mapped[Optional[float]] = mapped_column(Float)
    availability_status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    locality: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    bhk: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    area_sqft: Mapped[Optional[float]] = mapped_column(Float)
    furnishing: Mapped[Optional[str]] = mapped_column(String(32))
    property_type: Mapped[Optional[str]] = mapped_column(String(64))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Dataset flags
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    is_periodic: Mapped[bool] = mapped_column(Boolean, default=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    eligible_for_model: Mapped[bool] = mapped_column(Boolean, default=False)
    changed_fields: Mapped[Optional[str]] = mapped_column(String(256))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<RentalObservation listing_id={self.listing_id!r} "
            f"rent={self.rent_monthly} eligible={self.eligible_for_model}>"
        )


class RentCell(Base):
    """
    Spatial rent surface aggregated at H3 hexagon resolution.
    Stores empirical or model-derived percentile distributions (p25, p50, p75).
    """
    __tablename__ = "rent_cells"

    h3_index: Mapped[str] = mapped_column(String(20), primary_key=True)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    locality: Mapped[Optional[str]] = mapped_column(String(256), index=True)

    rent_p25: Mapped[Optional[float]] = mapped_column(Float)
    rent_p50: Mapped[Optional[float]] = mapped_column(Float)
    rent_p75: Mapped[Optional[float]] = mapped_column(Float)
    price_per_sqft_median: Mapped[Optional[float]] = mapped_column(Float)

    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_properties: Mapped[int] = mapped_column(Integer, default=0)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    latest_observation: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    confidence: Mapped[str] = mapped_column(String(32), default="INSUFFICIENT_DATA")
    model_version: Mapped[str] = mapped_column(String(64), default="none")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<RentCell h3={self.h3_index!r} p50={self.rent_p50} "
            f"conf={self.confidence}>"
        )

