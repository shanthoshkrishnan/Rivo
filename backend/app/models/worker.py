"""
RIVO Backend — Worker, Occupation & Income ORM Models
=======================================================
Three closely related tables:

worker_profiles
    A searchable worker profile (occupation + income band).
    Used by RIVO Home to understand what income thresholds apply.

income_profiles
    PLFS-derived income distribution per occupation × geography.
    Stores p25/median/p75 and a confidence level.
    If Chennai data is sparse, falls back to Tamil Nadu urban, then
    India urban — confidence drops accordingly.

workplaces
    Known employment locations (hospitals, schools, bus depots,
    logistics hubs, etc.) with estimated job counts.
    Do NOT claim exact counts unless a source provides them.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


# ─────────────────────────────────────────────────────────────────────────────
class WorkerProfile(Base):
    """
    Represents a worker type that RIVO can reason about.
    Occupation codes align with PLFS 2025 NIC/NCO codes.
    """

    __tablename__ = "worker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # e.g. "nurse", "teacher", "bus_driver", "delivery_rider"
    occupation_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    occupation_label: Mapped[str] = mapped_column(String(128), nullable=False)
    # NIC-2008 / NCO code for PLFS alignment
    nic_code: Mapped[Optional[str]] = mapped_column(String(16))
    nco_code: Mapped[Optional[str]] = mapped_column(String(16))
    description: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<WorkerProfile {self.occupation_key!r}>"


# ─────────────────────────────────────────────────────────────────────────────
class IncomeProfile(Base):
    """
    PLFS-derived income distribution for an occupation in a geography.

    geography_level: "chennai" | "tamil_nadu_urban" | "india_urban"
    Confidence decreases as we widen from Chennai to India.

    Source: PLFS 2025 — https://microdata.gov.in/NADA/index.php/catalog/284
    Freshness: PERIODIC (annual survey)
    """

    __tablename__ = "income_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    occupation_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # geography level used (Chennai → TN Urban → India Urban fallback)
    geography_level: Mapped[str] = mapped_column(String(32), nullable=False)
    # monthly income in INR
    income_p25: Mapped[Optional[float]] = mapped_column(Float)
    income_median: Mapped[Optional[float]] = mapped_column(Float)
    income_p75: Mapped[Optional[float]] = mapped_column(Float)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer)
    # HIGH / MEDIUM / LOW
    confidence: Mapped[Optional[str]] = mapped_column(String(16))
    # PLFS survey year
    survey_year: Mapped[Optional[int]] = mapped_column(Integer)
    source_name: Mapped[str] = mapped_column(String(128), default="PLFS 2025")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<IncomeProfile occ={self.occupation_key!r} "
            f"geo={self.geography_level!r} median={self.income_median}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
class Workplace(Base):
    """
    A known or estimated employment location.

    Rule: Do NOT claim exact employee counts unless a primary source provides
    them.  Always store estimate + lower + upper + confidence.

    Sources: Chennai Health OGD, UDISE+, OSM, MTC depot data, etc.
    """

    __tablename__ = "workplaces"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    # e.g. "hospital", "school", "bus_depot", "logistics_hub", "restaurant"
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(64))
    address: Mapped[Optional[str]] = mapped_column(Text)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    h3_index: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    gcc_ward: Mapped[Optional[str]] = mapped_column(String(16))

    # Estimated job opportunity (NOT a guaranteed headcount)
    estimated_jobs: Mapped[Optional[int]] = mapped_column(Integer)
    jobs_lower: Mapped[Optional[int]] = mapped_column(Integer)
    jobs_upper: Mapped[Optional[int]] = mapped_column(Integer)
    confidence: Mapped[Optional[str]] = mapped_column(String(16))   # HIGH/MEDIUM/LOW

    # Which occupation types this site is relevant to
    # e.g. '["nurse","doctor"]' — stored as JSON string for simplicity
    relevant_occupations: Mapped[Optional[str]] = mapped_column(Text)

    source_name: Mapped[Optional[str]] = mapped_column(String(128))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    data_freshness: Mapped[str] = mapped_column(String(32), default="PERIODIC")
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Workplace {self.name!r} cat={self.category!r}>"
