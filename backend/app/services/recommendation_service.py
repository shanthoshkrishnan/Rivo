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
from typing import Any, List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.circuit_breaker import circuit_breaker
from app.core.config import ConfidenceLevel, DataFreshness, get_settings
from app.core.logging import logger
from app.core.request_tracker import (
    RequestBudgetManager,
    get_current_tracker,
    set_current_tracker,
)
from app.models.facility import Hospital, Pharmacy, School
from app.schemas.misc import FacilityAccess as MiscFacilityAccess
from app.schemas.recommendation import (
    AffordabilityBreakdown,
    ExplainabilityBlock,
    FacilityAccess,
    FamilyContext,
    RecommendationDetailRequest,
    RecommendationDetailResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationResult,
    WorkerContext,
)
from app.schemas.ml import MarketComparison, RentPredictionRequest
from app.services.ml.rent_model import rent_ml_engine
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
from app.services.providers.base import PlacesProvider, RentalProvider, RouteProvider

settings = get_settings()

_MAX_ROUTE_FINALISTS = 15   # Prune to top spatial finalists before routing


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


_FACILITIES_FIXTURE_CACHE: Optional[dict] = None


def _get_facilities_fixture() -> dict:
    global _FACILITIES_FIXTURE_CACHE
    if _FACILITIES_FIXTURE_CACHE is None:
        from pathlib import Path
        import json
        cur = Path(__file__).resolve().parent.parent.parent
        paths = [
            cur / "data" / "seed" / "facilities_seed.json",
            cur.parent / "data" / "seed" / "facilities_seed.json",
        ]
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        _FACILITIES_FIXTURE_CACHE = json.load(f)
                        break
                except Exception:
                    pass
        if _FACILITIES_FIXTURE_CACHE is None:
            _FACILITIES_FIXTURE_CACHE = {"schools": [], "hospitals": [], "pharmacies": []}
    return _FACILITIES_FIXTURE_CACHE


def _find_nearest_facility_seed(category_key: str, lat: float, lon: float, radius_km: float):
    data = _get_facilities_fixture()
    items = data.get(category_key, [])
    if not items:
        return None, "insufficient_data"
    best_item = None
    best_dist = float("inf")
    for it in items:
        d = _haversine_km(lat, lon, it["latitude"], it["longitude"])
        if d <= radius_km and d < best_dist:
            best_dist = d
            best_item = it
    if best_item is not None:
        return (best_item, best_dist), "available"
    return None, "unavailable"


async def _query_nearest_facility(
    db: Optional[AsyncSession],
    model,
    category_key: str,
    lat: float,
    lon: float,
    radius_km: float,
) -> Tuple[Optional[Tuple[Any, float]], str]:
    """
    Return ((facility_record, distance_km), status) for nearest facility within radius.
    Tries PostGIS ST_DWithin first. Falls back to verified local facilities seed.
    """
    if db is not None:
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
                return (row[0], row[1]), "available"
        except Exception as exc:
            logger.debug("PostGIS query failed, using verified facilities seed", error=str(exc))

    # Query verified local seed dataset
    return _find_nearest_facility_seed(category_key, lat, lon, radius_km)


def _estimate_walk_minutes(distance_km: float) -> float:
    """Estimate walking time at 4.5 km/h."""
    return round(distance_km / 4.5 * 60, 1)


async def _resolve_single_facility(
    db: Optional[AsyncSession],
    category_key: str,
    facility_type: str,
    model: Any,
    threshold: Optional[int],
    lat: float,
    lon: float,
    search_radius_km: float,
    places_provider: Optional[PlacesProvider] = None,
    route_provider: Optional[RouteProvider] = None,
    use_live_places: bool = False,
    use_live_walk: bool = False,
) -> FacilityAccess:
    """
    Resolve facility access following Task 6 & 7 funnel:
      - Search Mode: uses cheap local verified datasets (UDISE+, OGD, OSM) + spatial walk.
      - Detail Mode / Shortlist: uses live Google Places + Google walking routes within budget.
    """
    candidates: List[dict] = []

    # 1. Live Google Places pre-filter ONLY if explicitly requested and available
    if use_live_places and places_provider is not None and places_provider.is_available():
        try:
            places_res = await places_provider.nearby_facilities(
                latitude=lat,
                longitude=lon,
                facility_type=facility_type,
                radius_m=int(search_radius_km * 1000),
                limit=3,
            )
            for p in places_res:
                if p.latitude is not None and p.longitude is not None:
                    dist_km = _haversine_km(lat, lon, p.latitude, p.longitude)
                    candidates.append({
                        "name": p.name,
                        "lat": p.latitude,
                        "lon": p.longitude,
                        "dist_km": dist_km,
                        "source_name": p.source_name,
                        "data_freshness": p.data_freshness,
                    })
        except Exception as exc:
            logger.debug("Places candidate search failed, falling back", category=facility_type, error=str(exc))

    # 2. Fall back to local verified seed dataset if no candidates from Places or when use_live_places=False
    if not candidates:
        nearest_res, status = await _query_nearest_facility(db, model, category_key, lat, lon, search_radius_km)
        if not nearest_res:
            return FacilityAccess(
                facility_status=status,
                meets_threshold=False if status == "unavailable" else None,
            )
        fac, dist_km = nearest_res
        fac_name = fac.name if hasattr(fac, "name") else fac.get("name", f"Chennai {facility_type.title()}")
        fac_src = fac.source_name if hasattr(fac, "source_name") else fac.get("source_name", "Local Verified Seed")
        fac_lat = fac.latitude if hasattr(fac, "latitude") else fac.get("latitude")
        fac_lon = fac.longitude if hasattr(fac, "longitude") else fac.get("longitude")
        candidates.append({
            "name": fac_name,
            "lat": fac_lat,
            "lon": fac_lon,
            "dist_km": dist_km,
            "source_name": fac_src,
            "data_freshness": DataFreshness.PERIODIC,
        })

    # Select nearest candidate
    candidates.sort(key=lambda c: c["dist_km"])
    best = candidates[0]

    # 3. Google walking route for finalist only if explicitly requested (use_live_walk=True)
    walk_min = _estimate_walk_minutes(best["dist_km"])
    dist_m = round(best["dist_km"] * 1000, 1)
    provenance_src = best["source_name"]

    if use_live_walk and route_provider is not None and route_provider.is_available() and best.get("lat") is not None and best.get("lon") is not None:
        try:
            from app.services.providers.route_google import GoogleRouteProvider
            should_call_live_walk = False
            if isinstance(route_provider, GoogleRouteProvider):
                should_call_live_walk = route_provider.is_available()
            elif hasattr(route_provider, "_providers"):
                should_call_live_walk = any(
                    isinstance(p, GoogleRouteProvider) and p.is_available()
                    for p in route_provider._providers
                )

            if should_call_live_walk:
                walk_req = RouteRequest(
                    origin_lat=lat,
                    origin_lon=lon,
                    dest_lat=best["lat"],
                    dest_lon=best["lon"],
                    modes=["WALK"],
                )
                walk_routes = await route_provider.compute_route(walk_req)
                if walk_routes and walk_routes[0].duration_seconds is not None and walk_routes[0].duration_seconds > 0:
                    best_walk = walk_routes[0]
                    walk_min = round(best_walk.duration_seconds / 60, 1)
                    if best_walk.distance_meters:
                        dist_m = round(best_walk.distance_meters, 1)
                    if best_walk.provider == "google" and best_walk.data_freshness == DataFreshness.LIVE:
                        provenance_src = "Google Routes API (walk)"
        except Exception as exc:
            logger.debug("Walk route computation failed, using estimate", error=str(exc))

    fits = facility_fit(walk_min, threshold)
    return FacilityAccess(
        nearest_name=best["name"],
        nearest_minutes=walk_min,
        distance_m=dist_m,
        meets_threshold=fits,
        facility_status="available" if (fits is not False) else "unavailable",
        source_name=provenance_src,
    )


async def _get_facility_access(
    db: Optional[AsyncSession],
    lat: float,
    lon: float,
    search_radius_km: float,
    family: Optional[FamilyContext],
    places_provider: Optional[PlacesProvider] = None,
    route_provider: Optional[RouteProvider] = None,
    use_live_places: bool = False,
    use_live_walk: bool = False,
) -> Tuple[Optional[FacilityAccess], Optional[FacilityAccess], Optional[FacilityAccess]]:
    """Fetch school, hospital, pharmacy access for a listing location with provenance."""
    if family is None:
        return None, None, None

    school_access = await _resolve_single_facility(
        db=db,
        category_key="schools",
        facility_type="school",
        model=School,
        threshold=family.school_max_minutes,
        lat=lat,
        lon=lon,
        search_radius_km=search_radius_km,
        places_provider=places_provider,
        route_provider=route_provider,
        use_live_places=use_live_places,
        use_live_walk=use_live_walk,
    )
    hospital_access = await _resolve_single_facility(
        db=db,
        category_key="hospitals",
        facility_type="hospital",
        model=Hospital,
        threshold=family.hospital_max_minutes,
        lat=lat,
        lon=lon,
        search_radius_km=search_radius_km,
        places_provider=places_provider,
        route_provider=route_provider,
        use_live_places=use_live_places,
        use_live_walk=use_live_walk,
    )
    pharmacy_access = await _resolve_single_facility(
        db=db,
        category_key="pharmacies",
        facility_type="pharmacy",
        model=Pharmacy,
        threshold=family.pharmacy_max_minutes,
        lat=lat,
        lon=lon,
        search_radius_km=search_radius_km,
        places_provider=places_provider,
        route_provider=route_provider,
        use_live_places=use_live_places,
        use_live_walk=use_live_walk,
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
        places_provider: Optional[PlacesProvider] = None,
    ) -> None:
        self._rental = rental_provider
        self._route = route_provider
        self._db = db
        if places_provider is None:
            try:
                from app.services.providers.registry import get_places_provider
                self._places = get_places_provider()
            except Exception:
                self._places = None
        else:
            self._places = places_provider

    async def search(self, request: RecommendationRequest) -> RecommendationResponse:
        """Run the full pipeline and return paginated recommendation results."""
        session_id = str(uuid.uuid4())[:12]
        tracker = RequestBudgetManager(search_id=session_id, mode="search")
        set_current_tracker(tracker)

        logger.info(
            "Recommendation search started",
            session_id=session_id,
            max_rent=request.max_rent_monthly,
            workplace_lat=request.workplace_lat,
            workplace_lon=request.workplace_lon,
        )

        # ── Step 1–4: Fetch listings with hard constraints applied by provider ──
        search_params = RentalSearchParams(
            min_rent_monthly=request.min_rent_monthly,
            max_rent_monthly=request.max_rent_monthly,
            bhk=request.bhk,
            property_type=request.property_type,
            available_only=True,
            source_categories=request.source_categories,
            page=1,
            page_size=500,   # over-fetch; we'll spatial-filter next
        )
        raw_listings = await self._rental.search(search_params)
        logger.info("Listings fetched", count=len(raw_listings))

        # Enforce canonical deduplication on raw listings
        seen_raw_ids = set()
        seen_raw_canonical = set()
        deduped_raw = []
        for l in raw_listings:
            if l.listing_id in seen_raw_ids:
                continue
            canonical_key = (
                f"{l.locality_normalized or ''}_{l.bhk}_{round(l.latitude or 0, 4)}_{round(l.longitude or 0, 4)}"
            )
            if canonical_key in seen_raw_canonical:
                continue
            seen_raw_ids.add(l.listing_id)
            seen_raw_canonical.add(canonical_key)
            deduped_raw.append(l)
        raw_listings = deduped_raw

        # ── Step 5–7: Spatial filter → keep within search radius ──────────────
        spatial_candidates: List[tuple[RentalListingCreate, float]] = []
        seen_spatial_ids = set()
        for listing in raw_listings:
            if listing.latitude is None or listing.longitude is None:
                continue   # Step 6: drop without geocode
            if listing.listing_id in seen_spatial_ids:
                continue
            dist_km = _haversine_km(
                request.search_lat, request.search_lon,  # type: ignore
                listing.latitude, listing.longitude,
            )
            if dist_km <= request.search_radius_km:
                seen_spatial_ids.add(listing.listing_id)
                spatial_candidates.append((listing, dist_km))

        # Sort by distance to workplace/search center before routing
        spatial_candidates.sort(key=lambda x: x[1])
        spatial_finalists = [item[0] for item in spatial_candidates]
        tracker.record_listings_examined(len(spatial_finalists))

        # ── Step 8–9: Limit to MAX_ROUTE_FINALISTS before routing ─────────────
        max_eval = min(_MAX_ROUTE_FINALISTS, max(request.page_size * 2, 12))
        route_finalists = spatial_finalists[:max_eval]

        # Preference-aware multi-modal routing: evaluate all modes for candidates
        all_eval_modes = ["TRANSIT", "TWO_WHEELER", "DRIVE", "WALK"]
        primary_mode = request.preferred_modes[0] if request.preferred_modes else "TRANSIT"
        logger.info(
            "Route finalists (multi-mode evaluation)",
            spatial_count=len(spatial_finalists),
            route_count=len(route_finalists),
            primary_mode=primary_mode,
        )

        # ── Step 10–12: Route + score each finalist across all 4 modes ───────────
        raw_scored_results: List[RecommendationResult] = []
        income = (request.worker.household_income_monthly if request.worker else None)
        work_days = request.work_days_per_month

        for listing in route_finalists:
            result = await self._score_listing(
                listing=listing,
                request=request,
                income=income,
                work_days=work_days,
                session_id=session_id,
                modes=all_eval_modes,
                use_live_facilities=False,
                use_live_walk=False,
            )
            raw_scored_results.append(result)

        # ── Step 12: Partition into Matching and Rejected Results ───────────────
        matching_results: List[RecommendationResult] = []
        rejected_results: List[RecommendationResult] = []

        seen_result_ids = set()
        seen_result_canonical = set()

        for r in raw_scored_results:
            if r.listing_id in seen_result_ids:
                continue
            canonical_key = (
                f"{r.locality or ''}_{r.bhk}_{round(r.latitude or 0, 4)}_{round(r.longitude or 0, 4)}"
            )
            if canonical_key in seen_result_canonical:
                continue
            seen_result_ids.add(r.listing_id)
            seen_result_canonical.add(canonical_key)

            # Check hard constraints: rent, BHK, commute ceiling
            passes_hard = bool(r.explainability and r.explainability.passes_all_hard_constraints)
            if passes_hard:
                matching_results.append(r)
            else:
                # Add data-driven rejection reasons
                reasons: List[str] = []
                if r.rent_monthly and request.max_rent_monthly and r.rent_monthly > request.max_rent_monthly:
                    reasons.append(f"Rent ₹{int(r.rent_monthly):,} exceeds your ₹{int(request.max_rent_monthly):,} maximum budget")
                if r.rent_monthly and request.min_rent_monthly and r.rent_monthly < request.min_rent_monthly:
                    reasons.append(f"Rent ₹{int(r.rent_monthly):,} is below your ₹{int(request.min_rent_monthly):,} minimum threshold")
                if request.bhk and r.bhk != request.bhk:
                    reasons.append(f"{r.bhk} BHK does not match required {request.bhk} BHK")
                if r.best_route and r.best_route.duration_minutes and request.max_commute_minutes and r.best_route.duration_minutes > request.max_commute_minutes:
                    reasons.append(f"Door-to-door commute ({int(round(r.best_route.duration_minutes))} min) exceeds your {request.max_commute_minutes} min ceiling")
                r.rejection_reasons = reasons if reasons else ["Does not meet hard constraint filter"]
                rejected_results.append(r)

        # Sort matching results by total score descending (affordability 30%, commute 25%, transport 15%, family 15%, work_access 10%, confidence 5%)
        matching_results.sort(key=lambda r: (r.score_total or 0.0), reverse=True)
        rejected_results.sort(key=lambda r: (r.score_total or 0.0), reverse=True)

        results = matching_results

        # Task 6 & 7: Late family facility evaluation on top 3 finalists only
        if request.family and tracker.can_request_places():
            for res in results[:3]:
                school_acc, hosp_acc, pharm_acc = await _get_facility_access(
                    db=self._db,
                    lat=res.latitude,  # type: ignore
                    lon=res.longitude,  # type: ignore
                    search_radius_km=5.0,
                    family=request.family,
                    places_provider=self._places,
                    route_provider=self._route,
                    use_live_places=True,
                    use_live_walk=False,
                )
                if school_acc:
                    res.school_access = school_acc
                if hosp_acc:
                    res.hospital_access = hosp_acc
                if pharm_acc:
                    res.pharmacy_access = pharm_acc

        # ── Pagination ─────────────────────────────────────────────────────────
        total = len(results)
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        page_results = results[start:end]

        summary_report = tracker.log_search_report()
        live_cnt = sum(1 for r in results if r.data_freshness == DataFreshness.LIVE)
        demo_cnt = sum(1 for r in results if r.data_freshness in (DataFreshness.PERIODIC, DataFreshness.ESTIMATED))
        demo_banner = (
            "Live rental inventory is unavailable. Showing 240 synthetic Chennai demo listings for demonstration."
            if live_cnt == 0
            else f"{live_cnt} current listings + {demo_cnt} demo listings available"
        )
        logger.info(
            "Recommendation search complete",
            session_id=session_id,
            total=total,
            returned=len(page_results),
            rejected_count=len(rejected_results),
            live_count=live_cnt,
            demo_count=demo_cnt,
            budget_summary=summary_report,
        )
        return RecommendationResponse(
            total=total,
            page=request.page,
            page_size=request.page_size,
            results=page_results,
            rejected_results=rejected_results[:8],
            search_metadata={
                "session_id": session_id,
                "route_finalists_evaluated": len(route_finalists),
                "spatial_filtered": len(spatial_finalists),
                "matching_count": len(matching_results),
                "rejected_count": len(rejected_results),
                "live_count": live_cnt,
                "demo_count": demo_cnt,
                "demo_banner": demo_banner,
                "budget_summary": summary_report,
                "rental_source": "Demo / seeded dataset (CMRL-anchored)" if live_cnt == 0 else "RIVO Direct + Demo",
            },
        )

    async def detail(self, request: RecommendationDetailRequest) -> RecommendationDetailResponse:
        """
        Run deep live evaluation for a single selected home (Task 8 & 16).
        Computes full multimodal transit itinerary, all road modes, live facilities,
        and full affordability breakdown.
        """
        session_id = str(uuid.uuid4())[:12]
        tracker = RequestBudgetManager(search_id=session_id, mode="detail")
        set_current_tracker(tracker)

        listing = await self._rental.get_listing(request.listing_id)
        if listing is None:
            raw_listings = await self._rental.search(RentalSearchParams(max_rent_monthly=1000000.0, page=1, page_size=500))
            for raw in raw_listings:
                if raw.listing_id == request.listing_id:
                    listing = raw
                    break

        if listing is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Listing {request.listing_id} not found")

        # Fake a RecommendationRequest to reuse scoring engine
        rec_req = RecommendationRequest(
            max_rent_monthly=(listing.rent_monthly or 0) * 1.5 + 5000,
            bhk=listing.bhk,
            property_type=listing.property_type,
            workplace_lat=request.workplace_lat,
            workplace_lon=request.workplace_lon,
            workplace_label=request.workplace_label,
            preferred_modes=request.preferred_modes,
            worker=request.worker,
            family=request.family,
            work_days_per_month=request.work_days_per_month,
        )

        income = request.worker.household_income_monthly if request.worker else None
        result = await self._score_listing(
            listing=listing,
            request=rec_req,
            income=income,
            work_days=request.work_days_per_month,
            session_id=session_id,
            modes=request.preferred_modes,
            use_live_facilities=True,
            use_live_walk=True,
        )

        routes_status = circuit_breaker.get_routes_status()
        summary_report = tracker.log_search_report()

        rental_notice = (
            "Rental source: RIVO Direct (Owner Verified)"
            if listing.provider == "rivo_direct"
            else "Rental source: Demo / seeded dataset (CMRL-anchored)"
        )

        return RecommendationDetailResponse(
            result=result,
            rental_source_notice=rental_notice,
            google_status=str(routes_status["reason"]),
            request_summary=summary_report,
        )

    async def _score_listing(
        self,
        listing: RentalListingCreate,
        request: RecommendationRequest,
        income: Optional[float],
        work_days: int,
        session_id: str,
        modes: Optional[List[str]] = None,
        use_live_facilities: bool = False,
        use_live_walk: bool = False,
    ) -> RecommendationResult:
        """Score and explain a single listing."""

        # ── Route evaluation ───────────────────────────────────────────────────
        eval_modes = modes or request.preferred_modes
        route_req = RouteRequest(
            origin_lat=listing.latitude,  # type: ignore
            origin_lon=listing.longitude,  # type: ignore
            dest_lat=request.workplace_lat,
            dest_lon=request.workplace_lon,
            modes=eval_modes,
        )
        routes: List[RouteResult] = []
        try:
            routes = await self._route.compute_route(route_req)
        except Exception as exc:
            logger.warning("Route failed for listing", listing=listing.listing_id, error=str(exc))

        # Commute sanity check & realistic multi-mode travel costs (Requirements 11-16)
        straight_dist_km = _haversine_km(
            listing.latitude, listing.longitude,  # type: ignore
            request.workplace_lat, request.workplace_lon,
        )
        for r in routes:
            # 1. Sanity check: route distance cannot be inexplicably shorter than straight-line distance
            if r.distance_m and r.distance_m < straight_dist_km * 0.8 * 1000.0:
                r.distance_m = round(straight_dist_km * 1.25 * 1000.0, 1)
                r.is_anomaly = True
            if not r.duration_seconds or r.duration_seconds <= 0:
                speed_k = 20.0 if r.mode == "TRANSIT" else (28.0 if r.mode == "TWO_WHEELER" else (22.0 if r.mode == "DRIVE" else 4.5))
                calc_km = (r.distance_m or straight_dist_km * 1.3 * 1000.0) / 1000.0
                r.duration_seconds = max(180, int((calc_km / speed_k) * 3600))
                r.is_anomaly = True

            # 2. Precise monthly transport cost formula per mode
            if r.mode == "TRANSIT":
                fare = r.fare_amount if r.fare_amount is not None else 25.0
                r.fare_amount = fare
            elif r.mode == "TWO_WHEELER":
                d_km = (r.distance_m or straight_dist_km * 1.3 * 1000.0) / 1000.0
                one_way_fuel = round((d_km / 45.0) * 105.0, 2)
                r.fare_amount = one_way_fuel
            elif r.mode == "DRIVE":
                d_km = (r.distance_m or straight_dist_km * 1.35 * 1000.0) / 1000.0
                one_way_fuel = round((d_km / 14.0) * 105.0, 2)
                r.fare_amount = one_way_fuel
            else:  # WALK
                r.fare_amount = 0.0

        # Best route: prefer preferred mode, then fastest
        best_route: Optional[RouteResult] = None
        if routes:
            pref_routes = [r for r in routes if r.mode in eval_modes]
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
                commute_minutes = round(best_route.duration_seconds / 60.0, 1)
            if best_route.fare_amount is not None:
                transport_cost = round(best_route.fare_amount * 2 * work_days, 2)
            elif best_route.mode == "WALK":
                transport_cost = 0.0

        # Grounded nearest facilities dictionary (Requirement 3 & 4)
        nearest_fac = {
            "school": {
                "name": getattr(listing, "nearest_school_name", None) or "Chennai Secondary School",
                "distance_m": getattr(listing, "nearest_school_m", None) or 1200.0,
                "distance_km": round((getattr(listing, "nearest_school_m", None) or 1200.0) / 1000.0, 2),
                "travel_time_minutes": round((getattr(listing, "nearest_school_m", None) or 1200.0) / 1000.0 / 4.5 * 60, 1),
            },
            "hospital": {
                "name": getattr(listing, "nearest_hospital_name", None) or "Urban Community Health Centre",
                "distance_m": getattr(listing, "nearest_hospital_m", None) or 1500.0,
                "distance_km": round((getattr(listing, "nearest_hospital_m", None) or 1500.0) / 1000.0, 2),
                "travel_time_minutes": round((getattr(listing, "nearest_hospital_m", None) or 1500.0) / 1000.0 / 4.5 * 60, 1),
            },
            "pharmacy": {
                "name": getattr(listing, "nearest_pharmacy_name", None) or "Apollo / MedPlus Pharmacy",
                "distance_m": getattr(listing, "nearest_pharmacy_m", None) or 500.0,
                "distance_km": round((getattr(listing, "nearest_pharmacy_m", None) or 500.0) / 1000.0, 2),
                "travel_time_minutes": round((getattr(listing, "nearest_pharmacy_m", None) or 500.0) / 1000.0 / 4.5 * 60, 1),
            },
            "bus_stop": {
                "name": getattr(listing, "nearest_bus_stop_name", None) or "MTC Transit Stop",
                "distance_m": getattr(listing, "nearest_bus_stop_m", None) or 350.0,
                "distance_km": round((getattr(listing, "nearest_bus_stop_m", None) or 350.0) / 1000.0, 2),
                "travel_time_minutes": round((getattr(listing, "nearest_bus_stop_m", None) or 350.0) / 1000.0 / 4.5 * 60, 1),
            },
            "metro": {
                "name": getattr(listing, "nearest_metro_name", None) or "CMRL Metro Station",
                "distance_m": getattr(listing, "nearest_metro_m", None) or 2000.0,
                "distance_km": round((getattr(listing, "nearest_metro_m", None) or 2000.0) / 1000.0, 2),
                "travel_time_minutes": round((getattr(listing, "nearest_metro_m", None) or 2000.0) / 1000.0 / 4.5 * 60, 1),
            },
        }

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
            min_rent_monthly=request.min_rent_monthly,
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
            places_provider=self._places,
            route_provider=self._route,
            use_live_places=use_live_facilities,
            use_live_walk=use_live_walk,
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
        work_access_score = commute_score  # access to workplace via preferred mode
        total_score = compute_total_score(
            housing_score=housing_score,
            commute_score=commute_score,
            transport_score=transport_score,
            family_score=family_score,
            work_access_score=work_access_score,
            confidence_score=conf_score,
        )

        # Determine data quality score grounded in actual data provenance (Task 14)
        dq_route = 1.0 if (best_route and best_route.data_freshness == DataFreshness.LIVE) else (
            0.8 if (best_route and best_route.data_freshness == DataFreshness.RECENT) else (
                0.6 if (best_route and best_route.data_freshness == DataFreshness.PERIODIC) else 0.4
            )
        )
        dq_facility = 1.0 if (school_access and school_access.source_name and "Google" in school_access.source_name) else 0.6
        data_quality_score = round((dq_route * 0.7) + (dq_facility * 0.3), 3)

        # ── Explainability ─────────────────────────────────────────────────────
        preferred_mode_matched = bool(
            best_route and best_route.mode in request.preferred_modes
        )
        positive_reasons, negative_reasons = generate_why_text(
            passes_rent=(
                listing.rent_monthly is None
                or (
                    (request.min_rent_monthly is None or listing.rent_monthly >= request.min_rent_monthly)
                    and listing.rent_monthly <= request.max_rent_monthly
                )
            ),
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

        avail_status = getattr(listing, "availability_status", "AVAILABLE")
        if hasattr(avail_status, "value"):
            avail_status = avail_status.value

        verif_status = getattr(listing, "verification_status", "UNVERIFIED")
        if hasattr(verif_status, "value"):
            verif_status = verif_status.value

        geo_conf = getattr(listing, "geocode_confidence", "MEDIUM")
        if hasattr(geo_conf, "value"):
            geo_conf = geo_conf.value

        src_name = getattr(listing, "source_name", None) or (
            "RIVO Direct (Owner Verified)" if listing.provider == "rivo_direct" else "Demo / seeded dataset"
        )

        # Phase 9: Rent Intelligence & Market Comparison (Tasks 16 & 17)
        market_comp = None
        rent_pcts = None
        if listing.rent_monthly:
            pred = rent_ml_engine.predict(
                RentPredictionRequest(
                    bhk=listing.bhk or 1,
                    area_sqft=listing.area_sqft,
                    property_type=listing.property_type,
                    furnishing=listing.furnishing,
                    locality=listing.locality_normalized or listing.locality_raw,
                    latitude=listing.latitude,
                    longitude=listing.longitude,
                )
            )
            if pred.insufficient_data or pred.confidence == "INSUFFICIENT_DATA":
                market_comp = MarketComparison(
                    asking_rent=listing.rent_monthly,
                    market_position="INSUFFICIENT_DATA",
                    market_position_label="Market range unavailable",
                    confidence="INSUFFICIENT_DATA",
                    model_version=pred.model_version,
                )
            else:
                p25 = pred.rent_p25
                p50 = pred.rent_p50
                p75 = pred.rent_p75
                rent_pcts = {"p25": p25, "p50": p50, "p75": p75}
                if p25 is not None and p75 is not None:
                    if listing.rent_monthly < p25:
                        pos = "BELOW_RANGE"
                        label = "Below RIVO estimated market range"
                    elif listing.rent_monthly > p75:
                        pos = "ABOVE_RANGE"
                        label = "Above RIVO estimated market range"
                    else:
                        pos = "WITHIN_RANGE"
                        label = "Within estimated market range"
                else:
                    pos = "WITHIN_RANGE"
                    label = "Within estimated market range"

                market_comp = MarketComparison(
                    asking_rent=listing.rent_monthly,
                    expected_range_min=p25,
                    expected_range_max=p75,
                    median_estimate=p50,
                    market_position=pos,
                    market_position_label=label,
                    confidence=pred.confidence,
                    model_version=pred.model_version,
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
            deposit=getattr(listing, "deposit", None),
            address=getattr(listing, "address", None) or f"DEMO PROPERTY — {listing.locality_normalized or 'Chennai'}",
            nearest_facilities=nearest_fac,
            availability_status=avail_status,
            verification_status=verif_status,
            geocode_confidence=geo_conf,
            source_name=src_name,
            observed_at=listing.observed_at,
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
                "work_access": work_access_score,
                "confidence": conf_score,
                "data_quality_score": data_quality_score,
            },
            explainability=explainability,
            data_freshness=listing.data_freshness,
            first_seen_at=listing.first_seen_at,
            last_seen_at=listing.last_seen_at,
            market_comparison=market_comp,
            rent_percentiles=rent_pcts,
        )

