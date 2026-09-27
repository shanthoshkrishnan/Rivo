"""
RIVO Backend — Data Sources Registry API Endpoint
===================================================
GET /api/v1/data/sources

Returns all registered data sources with license, attribution,
freshness and retrieval date information.

This endpoint implements the transparency requirement from DATA_LICENSES.md:
  - Every source must be disclosed
  - Attribution must be preserved
  - Redistribution and commercial use flags must be clear

The UI must surface this information so users can make informed
judgements about data quality and provenance.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.data_source import DataSource
from app.schemas.misc import DataSourceOut

router = APIRouter(prefix="/data", tags=["data-sources"])


@router.get(
    "/sources",
    response_model=List[DataSourceOut],
    summary="List all registered data sources",
    description=(
        "Returns the RIVO data source registry. "
        "Every data layer used by RIVO is listed here with license, "
        "attribution, and freshness information."
    ),
)
async def list_data_sources(
    db: AsyncSession | None = Depends(get_db),
) -> List[DataSourceOut]:
    if db is not None:
        try:
            stmt = select(DataSource).order_by(DataSource.layer, DataSource.source_name)
            result = await db.execute(stmt)
            sources = result.scalars().all()
            if sources:
                return [DataSourceOut.model_validate(s) for s in sources]
        except Exception:
            pass

    # Return hardcoded registry if DB not yet seeded or unavailable
    return _default_sources()


@router.post(
    "/refresh",
    summary="Refresh and reconcile data pipeline (Task 8)",
    description=(
        "Refreshes rental candidates, validates Places cache, and audits GTFS transit metadata. "
        "Pipeline: NEW DATA -> VALIDATE -> DEDUPLICATE -> UPSERT -> MARK OBSERVED_AT."
    ),
)
async def refresh_data_endpoint(
    db: AsyncSession | None = Depends(get_db),
):
    from app.services.data_refresh_service import DataRefreshService
    service = DataRefreshService(db=db)
    return await service.refresh_all()


def _default_sources() -> List[DataSourceOut]:
    """
    Hardcoded data source registry based on DATA_LICENSES.md and DATA_SOURCES.md.
    Replace with DB records after running scripts/seed_data_sources.py.
    """
    import uuid
    now = None

    def ds(**kwargs) -> DataSourceOut:
        return DataSourceOut(id=uuid.uuid4(), **kwargs)

    return [
        ds(
            source_name="GCC GIS 2025",
            layer="city_boundary",
            source_url="https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/EDPMobile2025/FeatureServer/layers",
            license="Verify current source terms",
            attribution="Greater Chennai Corporation",
            data_freshness="PERIODIC",
            update_frequency="annual",
        ),
        ds(
            source_name="CUMTA GTFS",
            layer="transit",
            source_url="https://opendata.cumta.org/",
            license="Verify feed-specific terms",
            attribution="Chennai Unified Metropolitan Transport Authority (CUMTA)",
            data_freshness="PERIODIC",
            update_frequency="periodic",
        ),
        ds(
            source_name="PLFS 2025",
            layer="income",
            source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
            license="Government of India microdata access terms",
            attribution="Ministry of Statistics and Programme Implementation, GoI",
            data_freshness="PERIODIC",
            update_frequency="annual",
        ),
        ds(
            source_name="Chennai Health Infrastructure OGD",
            layer="hospitals",
            source_url="https://ap.data.gov.in/catalog/health-infrastructure-chennai",
            license="Open Government Data License India (OGDL)",
            attribution="Government of Tamil Nadu / data.gov.in",
            data_freshness="PERIODIC",
            update_frequency="periodic",
        ),
        ds(
            source_name="UDISE+",
            layer="schools",
            source_url="https://udiseplus.gov.in/",
            license="Verify current reuse conditions",
            attribution="Ministry of Education, Government of India",
            data_freshness="PERIODIC",
            update_frequency="annual",
        ),
        ds(
            source_name="OpenStreetMap",
            layer="roads_pois",
            source_url="https://www.openstreetmap.org/",
            license="ODbL 1.0",
            attribution="© OpenStreetMap contributors",
            data_freshness="PERIODIC",
            update_frequency="continuous",
        ),
        ds(
            source_name="WorldPop 2025",
            layer="population",
            source_url="https://hub.worldpop.org/geodata/summary?id=73807",
            license="CC BY 4.0",
            attribution="WorldPop, University of Southampton",
            data_freshness="HISTORICAL",
            update_frequency="annual",
        ),
        ds(
            source_name="CMRL Phase II",
            layer="metro_scenario",
            source_url="https://chennaimetrorail.org/cmrl-profile/",
            license="Public information",
            attribution="Chennai Metro Rail Limited (CMRL)",
            data_freshness="HISTORICAL",
            update_frequency="project-based",
        ),
        ds(
            source_name="MTC Fares",
            layer="transit_fares",
            source_url="https://mtcbus.tn.gov.in/Home/fares",
            license="Public information",
            attribution="Metropolitan Transport Corporation (MTC), Tamil Nadu",
            data_freshness="PERIODIC",
            update_frequency="as-revised",
        ),
        ds(
            source_name="CMRL Fare Calculator",
            layer="transit_fares",
            source_url="https://chennaimetrorail.org/fare-calculator/",
            license="Public information",
            attribution="Chennai Metro Rail Limited (CMRL)",
            data_freshness="PERIODIC",
            update_frequency="as-revised",
        ),
        ds(
            source_name="RIVO Sample Data",
            layer="rentals",
            source_url=None,
            license="Internal sample — NOT real listings",
            attribution="RIVO Team CLAIRES (ST1010) — demo only",
            data_freshness="PERIODIC",
            update_frequency="static",
        ),
    ]
