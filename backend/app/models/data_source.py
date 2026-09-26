"""
RIVO Backend — Data Source Registry ORM Model
==============================================
Every data source used by RIVO is registered here with:
  - license information
  - attribution string
  - retrieval and effective dates
  - redistribution/commercial use flags

This implements the Data License Registry defined in DATA_LICENSES.md.

Rule: Downloadable ≠ redistributable.  API access ≠ cacheable forever.
Always check and record the license before ingesting a new source.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DataSource(Base):
    """
    Registry entry for every external data source RIVO uses.
    Required fields mirror DATA_LICENSES.md metadata block.
    """

    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    source_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    layer: Mapped[Optional[str]] = mapped_column(String(64))    # e.g. "transit", "income"
    source_url: Mapped[Optional[str]] = mapped_column(Text)

    # ── Temporal ──────────────────────────────────────────────────────────────
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ── License ───────────────────────────────────────────────────────────────
    license: Mapped[Optional[str]] = mapped_column(String(128))     # e.g. "ODbL", "CC BY 4.0"
    attribution: Mapped[Optional[str]] = mapped_column(Text)
    commercial_use_allowed: Mapped[Optional[bool]] = mapped_column(Boolean)
    redistribution_allowed: Mapped[Optional[bool]] = mapped_column(Boolean)
    retention_limits: Mapped[Optional[str]] = mapped_column(Text)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # ── Freshness ─────────────────────────────────────────────────────────────
    # LIVE / PERIODIC / HISTORICAL / ESTIMATED
    data_freshness: Mapped[Optional[str]] = mapped_column(String(32))
    update_frequency: Mapped[Optional[str]] = mapped_column(String(64))   # e.g. "annual"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<DataSource {self.source_name!r}>"
