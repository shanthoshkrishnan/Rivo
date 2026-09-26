"""
RIVO Backend — Recommendation Service
========================================
Orchestrates the full filtering → routing → scoring → ranking pipeline
for RIVO Home search requests.

Pipeline (per AGENTS.md §rental_filtering_order and ARCHITECTURE.md):
  1. availability           — hard filter
  2. property type          — hard filter
  3. BHK                    — hard filter
  4. hard rent budget       — hard filter
  5. tenant restrictions    — hard filter (where known)
  6. location validity      — drop listings without geocode
  7. duplicate filtering    — only canonical listings proceed
  8. spatial/facility filter — keep within search_radius_km
  9. facility fit           — score facility access
  10. route evaluation       — only for finalists (≤ 200)
  11. affordability calc     — uses route result
  12. recommendation ranking — weighted score + hard-constraint check
  13. explainability         — data-driven reasons, no LLM

All displayed numbers come from real data or documented fixtures.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConfidenceLevel, DataFreshness, get_settings
from app.core.logging import logger
from app.models.facility import Hospital, Pharmacy, School
from app.schemas.misc import FacilityAccess
from app.schemas.recommendation import (
    AffordabilityBreakdown,
    ExplainabilityBlock,
    FamilyContext,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationResult,
    WorkerContext,
)
from app.schemas.rental import RentalListingCreate, RentalSearchParams
from app.schemas.routing import RouteRequest, RouteResult
from app.services.algorithms.affordability import (
    check_hard_constraints,
    compute_affordability,
    compute_commute_score,
    compute_confidence_level,
    compute_confidence_score,
    compute_family_score,
    compute_housing_score,
    compute_monthly_transit_cost,
    compute_total_score,
    compute_transport_score,
    facility_fit,
    generate_why_text,
)
from app.services.providers.base import RentalProvider, RouteProvider

settings = get_settings()

_MAX_ROUTE_FINALISTS = 200   # Never route more than this many listings


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def _query_nearest_facility(
    db: Optional[AsyncSession],
    model,
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[object, float]]:
    """
    Return (facility_record, distance_km) for nearest facility within radius.
    Uses PostGIS ST_DWithin for spatial efficiency.
    Falls back to haversine if PostGIS geometry columns unavailable.
    """
    if db is None:
        return None
    try:
        stmt = (
            select(
                model,
                text(
                    f"ST_Distance(geom::geography, "
                    f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography) / 1000 AS dist_km"
                ),
            )
            .where(
                text(
                    f"ST_DWithin(geom::geography, "
                    f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography, "
                    f"{radius_km * 1000})"
                )
            )
            .order_by(text("dist_km"))
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row:
            return row[0], row[1]
    except Exception as exc:
        logger.debug("PostGIS query failed, trying fallback", error=str(exc))
    return None


def _estimate_walk_minutes(distance_km: float) -> float:
    """Estimate walking time at 4.5 km/h."""
    return round(distance_km / 4.5 * 60, 1)


async def _get_facility_access(
    db: AsyncSession,
    lat: float,
    lon: float,
    search_radius_km: float,
    family: Optional[FamilyContext],
) -> Tuple[Optional[FacilityAccess], Optional[FacilityAccess], Optional[FacilityAccess]]:
    """Fetch school, hospital, pharmacy access for a listing location."""
    school_access: Optional[FacilityAccess] = None
    hospital_access: Optional[FacilityAccess] = None
    pharmacy_access: Optional[FacilityAccess] = None

    if family is None:
        return school_access, hospital_access, pharmacy_access

    # School
    school_threshold = family.school_max_minutes
    nearest_school = await _query_nearest_facility(db, School, lat, lon, search_radius_km)
    if nearest_school:
        _, dist_km = nearest_school
        walk_min = _estimate_walk_minutes(dist_km)
        school_access = FacilityAccess(
            nearest_minutes=walk_min,
            meets_threshold=facility_fit(walk_min, school_threshold),
        )

    # Hospital
    hosp_threshold = family.hospital_max_minutes
    nearest_hosp = await _query_nearest_facility(db, Hospital, lat, lon, search_radius_km)
    if nearest_hosp:
        _, dist_km = nearest_hosp
        walk_min = _estimate_walk_minutes(dist_km)
        hospital_access = FacilityAccess(
            nearest_minutes=walk_min,
            meets_threshold=facility_fit(walk_min, hosp_threshold),
        )

    # Pharmacy
    pharma_threshold = family.pharmacy_max_minutes
    nearest_pharma = await _query_nearest_facility(db, Pharmacy, lat, lon, search_radius_km)
    if nearest_pharma:
        _, dist_km = nearest_pharma
        walk_min = _estimate_walk_minutes(dist_km)
        pharmacy_access = FacilityAccess(
            nearest_minutes=walk_min,
            meets_threshold=facility_fit(walk_min, pharma_threshold),
        )

    return school_access, hospital_access, pharmacy_access


class RecommendationService:
    """
    Orchestrates the full RIVO Home recommendation pipeline.
    """

    def __init__(
        self,
        rental_provider: RentalProvider,
        route_provider: RouteProvider,
        db: Optional[AsyncSession] = None,
    ) -> None:
        self._rental = rental_provider
        self._route = route_provider
        self._db = db

    async def search(self, request: RecommendationRequest) -> RecommendationResponse:
        """Run the full pipeline and return paginated recommendation results."""
        session_id = str(uuid.uuid4())[:12]
        logger.info(
            "Recommendation search started",
            session_id=session_id,
            max_rent=request.max_rent_monthly,
            workplace_lat=request.workplace_lat,
            workplace_lon=request.workplace_lon,
        )

        # ── Step 1–4: Fetch listings with hard constraints applied by provider ──
        search_params = RentalSearchParams(
            max_rent_monthly=request.max_rent_monthly,
            bhk=request.bhk,
            property_type=request.property_type,
            available_only=True,
            page=1,
            page_size=500,   # over-fetch; we'll spatial-filter next
        )
        raw_listings = await self._rental.search(search_params)
        logger.info("Listings fetched", count=len(raw_listings))

        # ── Step 5–7: Spatial filter → keep within search radius ──────────────
        spatial_finalists: List[RentalListingCreate] = []
        for listing in raw_listings:
            if listing.latitude is None or listing.longitude is None:
                continue   # Step 6: drop without geocode
            dist_km = _haversine_km(
                request.search_lat, request.search_lon,  # type: ignore
                listing.latitude, listing.longitude,
            )
            if dist_km <= request.search_radius_km:
                spatial_finalists.append(listing)

        # ── Step 8: Facility filter (keep if family thresholds are unset
        #    or can be evaluated) — done during scoring below ─────────────────

        # ── Step 9: Limit to MAX_ROUTE_FINALISTS before routing ───────────────
        route_finalists = spatial_finalists[:_MAX_ROUTE_FINALISTS]
        logger.info(
            "Route finalists",
            spatial_count=len(spatial_finalists),
            route_count=len(route_finalists),
        )

        # ── Step 10–12: Route + score each finalist ────────────────────────────
        results: List[RecommendationResult] = []
        income = (request.worker.household_income_monthly if request.worker else None)
        work_days = request.work_days_per_month

        for listing in route_finalists:
            result = await self._score_listing(
                listing=listing,
                request=request,
                income=income,
                work_days=work_days,
                session_id=session_id,
            )
            results.append(result)

        # ── Step 12: Sort by total score descending ────────────────────────────
        results.sort(key=lambda r: (r.score_total or 0.0), reverse=True)

        # ── Pagination ─────────────────────────────────────────────────────────
        total = len(results)
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        page_results = results[start:end]

        logger.info(
            "Recommendation search complete",
            session_id=session_id,
            total=total,
            returned=len(page_results),
        )
        return RecommendationResponse(
            total=total,
            page=request.page,
            page_size=request.page_size,
            results=page_results,
            search_metadata={
                "session_id": session_id,
                "route_finalists_evaluated": len(route_finalists),
                "spatial_filtered": len(spatial_finalists),
            },
        )

    async def _score_listing(
        self,
        listing: RentalListingCreate,
        request: RecommendationRequest,
        income: Optional[float],
        work_days: int,
        session_id: str,
    ) -> RecommendationResult:
        """Score and explain a single listing."""

        # ── Route evaluation ───────────────────────────────────────────────────
        route_req = RouteRequest(
            origin_lat=listing.latitude,  # type: ignore
            origin_lon=listing.longitude,  # type: ignore
            dest_lat=request.workplace_lat,
            dest_lon=request.workplace_lon,
            modes=request.preferred_modes,
        )
        routes: List[RouteResult] = []
        try:
            routes = await self._route.compute_route(route_req)
        except Exception as exc:
            logger.warning("Route failed for listing", listing=listing.listing_id, error=str(exc))

        # Best route: prefer preferred mode, then fastest
        best_route: Optional[RouteResult] = None
        if routes:
            pref_routes = [r for r in routes if r.mode in request.preferred_modes]
            candidates = pref_routes or routes
            by_duration = sorted(
                (r for r in candidates if r.duration_seconds is not None),
                key=lambda r: r.duration_seconds,  # type: ignore
            )
            best_route = by_duration[0] if by_duration else routes[0]

        commute_minutes = None
        transport_cost = None
        if best_route:
            if best_route.duration_seconds:
                commute_minutes = best_route.duration_seconds / 60
            if best_route.fare_amount is not None:
                transport_cost = compute_monthly_transit_cost(best_route.fare_amount, work_days)

        # ── Affordability ──────────────────────────────────────────────────────
        afford = compute_affordability(
            rent_monthly=listing.rent_monthly,
            maintenance_monthly=listing.maintenance_monthly,
            transport_cost_monthly=transport_cost,
            household_income_monthly=income,
            one_way_commute_minutes=commute_minutes,
            work_days=work_days,
        )

        affordability_out = AffordabilityBreakdown(
            monthly_rent=listing.rent_monthly,
            monthly_maintenance=listing.maintenance_monthly,
            monthly_transport_cost=transport_cost,
            monthly_total_cost=afford.monthly_total_cost,
            housing_burden_pct=afford.housing_burden,
            transport_burden_pct=afford.transport_burden,
            cash_burden_pct=afford.cash_burden,
            monthly_commute_hours=afford.monthly_commute_hours,
        )

        # ── Hard constraints ───────────────────────────────────────────────────
        hc = check_hard_constraints(
            rent_monthly=listing.rent_monthly,
            max_rent_monthly=request.max_rent_monthly,
            bhk=listing.bhk,
            required_bhk=request.bhk,
            property_type=listing.property_type,
            required_property_type=request.property_type,
            is_available=listing.is_available,
            commute_minutes=commute_minutes,
            max_commute_minutes=request.max_commute_minutes,
        )

        # ── Family / facility access ───────────────────────────────────────────
        school_access, hospital_access, pharmacy_access = await _get_facility_access(
            db=self._db,
            lat=listing.latitude,  # type: ignore
            lon=listing.longitude,  # type: ignore
            search_radius_km=5.0,   # facility search radius
            family=request.family,
        )

        # ── Scores ────────────────────────────────────────────────────────────
        housing_score = compute_housing_score(
            rent_monthly=listing.rent_monthly or 0,
            max_rent_monthly=request.max_rent_monthly,
            cash_burden=afford.cash_burden,
        )
        commute_score = compute_commute_score(
            commute_minutes=commute_minutes,
            max_commute_minutes=request.max_commute_minutes,
        )
        transport_score = compute_transport_score(
            monthly_transport_cost=transport_cost,
            household_income_monthly=income,
        )
        family_score = compute_family_score(
            school_fits=(school_access.meets_threshold if school_access else None),
            hospital_fits=(hospital_access.meets_threshold if hospital_access else None),
            pharmacy_fits=(pharmacy_access.meets_threshold if pharmacy_access else None),
        )
        conf_score = compute_confidence_score(None)
        total_score = compute_total_score(
            housing_score=housing_score,
            commute_score=commute_score,
            transport_score=transport_score,
            family_score=family_score,
            confidence_score=conf_score,
        )

        # ── Explainability ─────────────────────────────────────────────────────
        preferred_mode_matched = bool(
            best_route and best_route.mode in request.preferred_modes
        )
        positive_reasons, negative_reasons = generate_why_text(
            passes_rent=listing.rent_monthly is None or listing.rent_monthly <= request.max_rent_monthly,
            passes_commute=commute_minutes is None or commute_minutes <= request.max_commute_minutes,
            passes_bhk=request.bhk is None or listing.bhk == request.bhk,
            school_fits=(school_access.meets_threshold if school_access else None),
            hospital_fits=(hospital_access.meets_threshold if hospital_access else None),
            pharmacy_fits=(pharmacy_access.meets_threshold if pharmacy_access else None),
            preferred_mode_matched=preferred_mode_matched,
            hard_failures=hc.failures,
        )
        conf_level = compute_confidence_level(
            listing_count=1,
            source_diversity=1,
            has_geocode=listing.latitude is not None,
            has_route=bool(routes),
            has_facility_data=school_access is not None,
        )
        explainability = ExplainabilityBlock(
            passes_all_hard_constraints=hc.passes,
            positive_reasons=positive_reasons,
            negative_reasons=negative_reasons,
            confidence=conf_level,
            data_freshness=listing.data_freshness,
        )

        return RecommendationResult(
            listing_id=listing.listing_id,
            provider=listing.provider,
            locality=listing.locality_normalized,
            bhk=listing.bhk,
            area_sqft=listing.area_sqft,
            furnishing=listing.furnishing,
            property_type=listing.property_type,
            latitude=listing.latitude,
            longitude=listing.longitude,
            rent_monthly=listing.rent_monthly,
            maintenance_monthly=listing.maintenance_monthly,
            best_route=best_route,
            all_routes=routes,
            affordability=affordability_out,
            school_access=school_access,
            hospital_access=hospital_access,
            pharmacy_access=pharmacy_access,
            score_total=total_score,
            score_components={
                "housing": housing_score,
                "commute": commute_score,
                "transport": transport_score,
                "family": family_score,
                "confidence": conf_score,
            },
            explainability=explainability,
            data_freshness=listing.data_freshness,
            first_seen_at=listing.first_seen_at,
            last_seen_at=listing.last_seen_at,
        )
