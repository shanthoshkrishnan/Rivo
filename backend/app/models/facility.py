"""
RIVO Backend — Facility ORM Models
=====================================
Three facility tables:
  - schools    (UDISE+ / mapped locations)
  - hospitals  (Chennai Health Infrastructure OGD)
  - pharmacies (OSM; optional Google Places enrichment)

Each facility has:
  - PostGIS geometry (POINT)
  - H3 index for cheap hex-level proximity
  - Freshness / source metadata

Family accessibility uses these tables to evaluate whether a home
meets the user's school / hospital / pharmacy distance thresholds.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class School(Base):
    """
    School record sourced from UDISE+ and mapped locations.
    Source: https://udiseplus.gov.in/
    Freshness: PERIODIC (annual)
    """

    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    udise_code: Mapped[Optional[str]] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    school_type: Mapped[Optional[str]] = mapped_column(String(64))   # govt/private/aided
    management: Mapped[Optional[str]] = mapped_column(String(64))
    medium_of_instruction: Mapped[Optional[str]] = mapped_column(String(128))
    classes_offered: Mapped[Optional[str]] = mapped_column(String(64))  # e.g. "1-12"
    enrollment_total: Mapped[Optional[int]] = mapped_column(Integer)
    teacher_count: Mapped[Optional[int]] = mapped_column(Integer)

    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    gcc_ward: Mapped[Optional[str]] = mapped_column(String(16))
    address: Mapped[Optional[str]] = mapped_column(Text)

    source_name: Mapped[str] = mapped_column(String(128), default="UDISE+")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Hospital(Base):
    """
    Hospital / health facility sourced from Chennai Health Infrastructure OGD.
    Source: https://ap.data.gov.in/catalog/health-infrastructure-chennai
    Freshness: PERIODIC

    bed_count and nurse_count are used to estimate nursing job opportunities
    (see algorithms.py → job_opportunity_nurse).
    """

    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    facility_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    facility_type: Mapped[Optional[str]] = mapped_column(String(64))   # govt/private/PHC
    bed_count: Mapped[Optional[int]] = mapped_column(Integer)
    nurse_count: Mapped[Optional[int]] = mapped_column(Integer)

    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    gcc_ward: Mapped[Optional[str]] = mapped_column(String(16))
    address: Mapped[Optional[str]] = mapped_column(Text)

    source_name: Mapped[str] = mapped_column(String(128), default="Chennai Health OGD")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Pharmacy(Base):
    """
    Pharmacy / chemist sourced from OSM with optional Google Places enrichment.
    Source: OpenStreetMap (ODbL) + optional Google Places API
    Freshness: PERIODIC

    NOTE: Google Places caching must comply with Google Maps Platform ToS.
    """

    __tablename__ = "pharmacies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    osm_id: Mapped[Optional[str]] = mapped_column(String(32), unique=True)
    google_place_id: Mapped[Optional[str]] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(256), nullable=False)

    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    gcc_ward: Mapped[Optional[str]] = mapped_column(String(16))
    address: Mapped[Optional[str]] = mapped_column(Text)

    source_name: Mapped[str] = mapped_column(String(128), default="OpenStreetMap")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
