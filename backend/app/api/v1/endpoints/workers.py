"""
RIVO Backend — Workers & Occupations API Endpoints
====================================================
GET /api/v1/workers/occupations   — list all supported occupations
GET /api/v1/workers/income/{key}  — income profile for one occupation

Data sources:
  - PLFS 2025 (Periodic Labour Force Survey)
  - Geography fallback: Chennai → TN Urban → India Urban
  - Freshness: PERIODIC (annual survey)

Important: Income estimates are from survey data.
  Do not treat them as exact salary figures.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.worker import IncomeProfile, WorkerProfile
from app.schemas.misc import IncomeProfileOut, WorkerOccupationOut

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get(
    "/occupations",
    response_model=List[WorkerOccupationOut],
    summary="List supported occupations",
)
async def list_occupations(
    db: AsyncSession | None = Depends(get_db),
) -> List[WorkerOccupationOut]:
    if db is not None:
        try:
            stmt = select(WorkerProfile).order_by(WorkerProfile.occupation_label)
            result = await db.execute(stmt)
            occupations = result.scalars().all()
            if occupations:
                return [
                    WorkerOccupationOut(
                        occupation_key=o.occupation_key,
                        occupation_label=o.occupation_label,
                        nic_code=o.nic_code,
                        description=o.description,
                    )
                    for o in occupations
                ]
        except Exception:
            pass
    # Return hardcoded set if DB is empty or unavailable
    return _default_occupations()


@router.get(
    "/income/{occupation_key}",
    response_model=IncomeProfileOut,
    summary="Get income profile for occupation",
)
async def get_income_profile(
    occupation_key: str,
    db: AsyncSession | None = Depends(get_db),
) -> IncomeProfileOut:
    if db is not None:
        try:
            # Try Chennai first, then TN urban, then India urban
            for geo in ("chennai", "tamil_nadu_urban", "india_urban"):
                stmt = (
                    select(IncomeProfile)
                    .where(
                        IncomeProfile.occupation_key == occupation_key,
                        IncomeProfile.geography_level == geo,
                    )
                    .limit(1)
                )
                result = await db.execute(stmt)
                profile = result.scalar_one_or_none()
                if profile:
                    return IncomeProfileOut.model_validate(profile)
        except Exception:
            pass

    # Return fixture if no DB record
    fixture = _income_fixtures().get(occupation_key)
    if fixture:
        return fixture
    raise HTTPException(status_code=404, detail=f"No income profile for {occupation_key!r}")


def _default_occupations() -> List[WorkerOccupationOut]:
    """Hardcoded occupation list used before DB is seeded."""
    return [
        WorkerOccupationOut(
            occupation_key="nurse",
            occupation_label="Nurse / Healthcare Worker",
            nic_code="Q8610",
            description="Registered nurses and other healthcare support staff",
        ),
        WorkerOccupationOut(
            occupation_key="teacher",
            occupation_label="School Teacher",
            nic_code="P8510",
            description="Primary, secondary and higher secondary teachers",
        ),
        WorkerOccupationOut(
            occupation_key="bus_driver",
            occupation_label="MTC Bus Driver",
            nic_code="H4931",
            description="Metropolitan Transport Corporation bus drivers",
        ),
        WorkerOccupationOut(
            occupation_key="delivery_rider",
            occupation_label="Delivery Rider",
            nic_code="H5320",
            description="Food, parcel and logistics delivery riders",
        ),
        WorkerOccupationOut(
            occupation_key="construction_worker",
            occupation_label="Construction Worker",
            nic_code="F4110",
            description="Informal and formal construction labourers",
        ),
    ]


def _income_fixtures() -> dict:
    """
    PLFS 2025-based income estimates.
    Source: PLFS 2025 microdata, Tamil Nadu urban (Chennai too sparse in sample).
    Confidence: MEDIUM (survey; Chennai-specific may differ).
    Freshness: PERIODIC (annual).
    """
    from app.core.config import ConfidenceLevel, DataFreshness
    shared = dict(
        geography_level="tamil_nadu_urban",
        confidence=ConfidenceLevel.MEDIUM,
        survey_year=2025,
        data_freshness=DataFreshness.PERIODIC,
        source_name="PLFS 2025",
    )
    return {
        "nurse": IncomeProfileOut(
            occupation_key="nurse",
            income_p25=18000, income_median=24000, income_p75=35000,
            sample_size=None, **shared
        ),
        "teacher": IncomeProfileOut(
            occupation_key="teacher",
            income_p25=15000, income_median=22000, income_p75=40000,
            sample_size=None, **shared
        ),
        "bus_driver": IncomeProfileOut(
            occupation_key="bus_driver",
            income_p25=18000, income_median=22000, income_p75=28000,
            sample_size=None, **shared
        ),
        "delivery_rider": IncomeProfileOut(
            occupation_key="delivery_rider",
            income_p25=12000, income_median=16000, income_p75=22000,
            sample_size=None, **shared
        ),
        "construction_worker": IncomeProfileOut(
            occupation_key="construction_worker",
            income_p25=9000, income_median=13000, income_p75=18000,
            sample_size=None, **shared
        ),
    }
