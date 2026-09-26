"""
RIVO Backend — Facilities API Endpoint
========================================
GET /api/v1/facilities/nearby

Returns nearby schools, hospitals, or pharmacies for a given coordinate.
Used by the Family Accessibility layer in RIVO Home and the map in RIVO City.

Data sources:
  - Google Places API (LIVE) when GOOGLE_PLACES_API_KEY is configured
  - Schools:    UDISE+ (PERIODIC)
  - Hospitals:  Chennai Health OGD (PERIODIC)
  - Pharmacies: OSM (PERIODIC)
"""
from __future__ import annotations

import math
import uuid
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.db.session import get_db
from app.models.facility import Hospital, Pharmacy, School
from app.schemas.misc import FacilityNearbyResponse, FacilityOut

router = APIRouter(prefix="/facilities", tags=["facilities"])
settings = get_settings()

_FACILITY_MODELS = {
    "school": School,
    "hospital": Hospital,
    "pharmacy": Pharmacy,
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def _fetch_google_places(
    latitude: float,
    longitude: float,
    facility_type: str,
    radius_km: float,
    limit: int,
) -> List[FacilityOut]:
    """Query live nearby facilities using Google Places API."""
    if not settings.GOOGLE_PLACES_API_KEY:
        return []
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    type_map = {
        "school": "school",
        "hospital": "hospital",
        "pharmacy": "pharmacy",
    }
    params = {
        "location": f"{latitude},{longitude}",
        "radius": int(radius_km * 1000),
        "type": type_map.get(facility_type, facility_type),
        "key": settings.GOOGLE_PLACES_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Google Places API error", status=resp.status_code)
                return []
            data = resp.json()
            items = data.get("results", [])
            results = []
            for item in items[:limit]:
                loc = item.get("geometry", {}).get("location", {})
                p_lat = loc.get("lat")
                p_lon = loc.get("lng")
                if p_lat is None or p_lon is None:
                    continue
                dist_km = _haversine_km(latitude, longitude, p_lat, p_lon)
                results.append(
                    FacilityOut(
                        id=uuid.uuid4(),
                        name=item.get("name", f"Local {facility_type.title()}"),
                        facility_type=facility_type,
                        latitude=p_lat,
                        longitude=p_lon,
                        address=item.get("vicinity"),
                        distance_m=round(dist_km * 1000, 1),
                        travel_time_minutes=round(dist_km / 4.5 * 60, 1),  # walk estimate at 4.5 km/h
                        data_freshness=DataFreshness.LIVE,
                        source_name="Google Places API",
                    )
                )
            return results
    except Exception as exc:
        logger.warning("Google Places query failed, falling back", error=str(exc))
        return []


@router.get(
    "/nearby",
    response_model=FacilityNearbyResponse,
    summary="Find nearby facilities",
)
async def nearby_facilities(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    facility_type: str = Query(..., description="school | hospital | pharmacy"),
    radius_km: float = Query(5.0, gt=0, le=20),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession | None = Depends(get_db),
) -> FacilityNearbyResponse:
    if facility_type not in _FACILITY_MODELS:
        raise HTTPException(status_code=400, detail=f"facility_type must be one of {list(_FACILITY_MODELS)}")

    # 1. Try Google Places API first if configured
    if settings.google_places_enabled:
        live_places = await _fetch_google_places(latitude, longitude, facility_type, radius_km, limit)
        if live_places:
            return FacilityNearbyResponse(
                facility_type=facility_type,
                results=live_places,
                data_freshness=DataFreshness.LIVE,
            )

    # 2. Try DB if available
    results: List[FacilityOut] = []
    if db is not None:
        model = _FACILITY_MODELS[facility_type]
        try:
            stmt = (
                select(
                    model,
                    text(
                        f"ST_Distance(geom::geography, "
                        f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)::geography) AS dist_m"
                    ),
                )
                .where(
                    text(
                        f"geom IS NOT NULL AND "
                        f"ST_DWithin(geom::geography, "
                        f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)::geography, "
                        f"{radius_km * 1000})"
                    )
                )
                .order_by(text("dist_m"))
                .limit(limit)
            )
            rows = (await db.execute(stmt)).all()
            for row in rows:
                fac, dist_m = row
                results.append(
                    FacilityOut(
                        id=fac.id,
                        name=fac.name,
                        facility_type=getattr(fac, "facility_type", None) or getattr(fac, "school_type", None),
                        latitude=fac.latitude,
                        longitude=fac.longitude,
                        address=fac.address,
                        distance_m=round(dist_m, 1),
                        travel_time_minutes=round(dist_m / 1000 / 4.5 * 60, 1),
                        data_freshness=DataFreshness(fac.data_freshness),
                        source_name=fac.source_name,
                    )
                )
        except Exception:
            pass

    return FacilityNearbyResponse(
        facility_type=facility_type,
        results=results,
        data_freshness=DataFreshness.PERIODIC,
    )
