"""
RIVO Backend — Routing & Transit ORM Models
=============================================
Tables:
  route_cache         Cached route results (Google / OTP / mock)
  transit_stops       GTFS stops from CUMTA feed
  transit_routes      GTFS routes
  transit_fares       MTC bus fares + CMRL metro fares

Routing cache key:
    origin · destination · mode · departure_bucket · provider
This prevents re-computing identical routes and protects against
routing thousands of listings against every destination.

Freshness:
  - route_cache entries are tagged LIVE (just computed) or RECENT (cached)
  - transit data is PERIODIC (updated when GTFS feed changes)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RouteCache(Base):
    """
    Stores a single point-to-point route result so it can be re-used
    without calling the routing provider again.

    Cache key components:
        origin_lat, origin_lon, dest_lat, dest_lon,
        mode, departure_bucket, provider

    departure_bucket: time rounded to 30-min window (e.g. "08:00", "08:30")
    to avoid creating a new cache entry for every second of the day.

    Geometry of the route (polyline) is stored as GeoJSON text.
    """

    __tablename__ = "route_cache"
    __table_args__ = (
        Index(
            "ix_route_cache_key",
            "origin_h3", "dest_h3", "mode", "departure_bucket", "provider",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )

    # ── Cache key fields ──────────────────────────────────────────────────────
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lon: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lon: Mapped[float] = mapped_column(Float, nullable=False)
    # H3-based fields for cheap indexing
    origin_h3: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    dest_h3: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)   # TRANSIT/DRIVE/WALK/TWO_WHEELER
    departure_bucket: Mapped[Optional[str]] = mapped_column(String(8))  # "08:00"
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # google/otp/mock

    # ── Route result ──────────────────────────────────────────────────────────
    distance_m: Mapped[Optional[float]] = mapped_column(Float)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    walk_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    wait_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    in_vehicle_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    transfer_count: Mapped[Optional[int]] = mapped_column(Integer)
    fare_amount: Mapped[Optional[float]] = mapped_column(Float)
    route_geometry: Mapped[Optional[str]] = mapped_column(Text)  # GeoJSON LineString

    # ── Metadata ──────────────────────────────────────────────────────────────
    # LIVE = just computed; RECENT = from cache within TTL
    data_freshness: Mapped[str] = mapped_column(String(32), default="LIVE")
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TransitStop(Base):
    """
    GTFS stop from the CUMTA (Chennai Unified Metropolitan Transport Authority)
    feed.  Source: https://opendata.cumta.org/
    Freshness: PERIODIC
    """

    __tablename__ = "transit_stops"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    stop_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    stop_code: Mapped[Optional[str]] = mapped_column(String(32))
    stop_name: Mapped[str] = mapped_column(String(256), nullable=False)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    stop_desc: Mapped[Optional[str]] = mapped_column(Text)
    location_type: Mapped[Optional[int]] = mapped_column(Integer)  # 0=stop, 1=station
    parent_station: Mapped[Optional[str]] = mapped_column(String(64))
    wheelchair_boarding: Mapped[Optional[int]] = mapped_column(Integer)
    # Derived spatial
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)

    feed_version: Mapped[Optional[str]] = mapped_column(String(64))
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TransitFare(Base):
    """
    Fare rules for MTC buses and CMRL metro.
    Used to compute monthly commute cost accurately.

    Sources:
      MTC: https://mtcbus.tn.gov.in/Home/fares
      CMRL: https://chennaimetrorail.org/fare-calculator/
    """

    __tablename__ = "transit_fares"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    operator: Mapped[str] = mapped_column(String(32), nullable=False)  # MTC / CMRL
    # distance band in km
    distance_min_km: Mapped[Optional[float]] = mapped_column(Float)
    distance_max_km: Mapped[Optional[float]] = mapped_column(Float)
    fare_inr: Mapped[float] = mapped_column(Float, nullable=False)
    fare_type: Mapped[Optional[str]] = mapped_column(String(32))   # ordinary/ac/metro

    source_name: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
