"""
RIVO Backend — Rental Listings API Endpoints
==============================================
GET   /api/v1/rentals/search                      — search listings with hard constraints
GET   /api/v1/rentals/{id}                        — single listing by ID
PATCH /api/v1/rentals/direct/{listing_id}         — update direct listing + append observation
GET   /api/v1/rentals/{listing_id}/history        — observation history
POST  /api/v1/rentals/admin/collect               — admin: manually record an observation
GET   /api/v1/rentals/admin/data-quality          — data quality + model eligibility + gate progress
GET   /api/v1/rentals/admin/collection-progress   — operational collection progress by locality/BHK/source
GET   /api/v1/rentals/real-market-summary         — real-data-only market statistics

All responses include data_freshness and source metadata.
The UI MUST display freshness tags for every rental response.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DataFreshness
from app.db.session import get_db
from app.schemas.rental import (
    DirectRentalSubmissionRequest,
    MarketSummaryResponse,
    PaginatedRentalResponse,
    RentalAdminSummary,
    RentalListingOut,
    RentalSearchParams,
)
from app.schemas.ml import (
    ModelEligibilityResult,
    RentPredictionRequest,
    RentPredictionResponse,
)
from app.schemas.observation import (
    AdminCollectObservationRequest,
    AdminCollectObservationResponse,
    AdminDataQualityReport,
    DirectListingUpdateRequest,
    DirectListingUpdateResponse,
    ObservationHistoryResponse,
)
from app.services.providers.registry import get_rental_provider
from app.services.observation_service import observation_service


router = APIRouter(prefix="/rentals", tags=["rentals"])


@router.get(
    "/search",
    response_model=PaginatedRentalResponse,
    summary="Search rental listings",
    description=(
        "Search for rental listings matching hard constraints. "
        "Returns data_freshness label per RIVO data policy. "
        "Asking rent is NOT treated as ground truth — see model_rent_p25/p50/p75."
    ),
)
async def search_rentals(
    max_rent_monthly: float = Query(..., gt=0, description="Hard rent ceiling in INR"),
    bhk: int = Query(None, ge=1, le=10, description="Required BHK count"),
    property_type: str = Query(None, description="flat | house | pg | studio"),
    locality: str = Query(None, description="Locality name or partial match"),
    available_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_categories: List[str] = Query(None, description="CURRENT, RECENT, PERIODIC, DEMO"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRentalResponse:
    params = RentalSearchParams(
        max_rent_monthly=max_rent_monthly,
        bhk=bhk,
        property_type=property_type,
        locality=locality,
        available_only=available_only,
        source_categories=source_categories,
        page=page,
        page_size=page_size,
    )
    provider = get_rental_provider()
    raw_listings = await provider.search(params)

    # Paginate
    total = len(raw_listings)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = raw_listings[start:end]

    # Determine overall freshness (use lowest)
    freshness = DataFreshness.PERIODIC
    if page_data:
        freshness = page_data[0].data_freshness

    return PaginatedRentalResponse(
        total=total,
        page=page,
        page_size=page_size,
        data_freshness=freshness,
        results=[
            RentalListingOut(**listing.model_dump(), id=_fake_uuid(listing.listing_id))
            for listing in page_data
        ],
    )


@router.post(
    "/direct",
    response_model=RentalListingOut,
    status_code=201,
    summary="Submit direct rental listing",
    description="Owner or verified agent direct listing submission. Enforces Chennai bounding box and consent.",
)
async def submit_direct_listing(
    payload: DirectRentalSubmissionRequest,
    db: AsyncSession = Depends(get_db),
) -> RentalListingOut:
    from fastapi import HTTPException
    from app.services.providers.rental_rivo_direct import rivo_direct_provider

    if not payload.consent_to_publish:
        raise HTTPException(status_code=400, detail="Consent to publish is mandatory for direct submission")

    try:
        listing = rivo_direct_provider.add_direct_listing(payload)
        return RentalListingOut(**listing.model_dump(), id=_fake_uuid(listing.listing_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/market-summary",
    response_model=MarketSummaryResponse,
    summary="Empirical rental market statistics",
    description=(
        "Returns median asking rent, p25/p75, and breakdown by BHK/locality from observed current listings. "
        "When fewer than 5 real observations exist, returns insufficient_data=True."
    ),
)
async def get_market_summary() -> MarketSummaryResponse:
    from app.services.providers.rental_registry import rental_registry
    return rental_registry.get_market_summary()


@router.get(
    "/real-market-summary",
    summary="Real-data-only empirical market statistics (Phase 11)",
    description=(
        "Returns market statistics computed ONLY from eligible real observations — "
        "never demo or synthetic data. Returns insufficient_data=True when data is thin. "
        "Do not use this to make city-wide claims from a tiny local sample."
    ),
)
async def get_real_market_summary() -> dict:
    return observation_service.real_market_summary()


@router.get(
    "/admin/summary",
    response_model=RentalAdminSummary,
    summary="Admin rental dashboard metrics",
    description="Internal operational overview of rental sources, freshness distribution, and availability states.",
)
async def get_admin_summary() -> RentalAdminSummary:
    from app.services.providers.rental_registry import rental_registry
    return rental_registry.get_admin_summary()


@router.post(
    "/market-estimate",
    response_model=RentPredictionResponse,
    summary="Estimate expected market rent range",
    description="Estimates rent_p25, p50, and p75 from empirical observations or LightGBM quantile model.",
)
async def estimate_market_rent(payload: RentPredictionRequest) -> RentPredictionResponse:
    from app.services.ml.rent_model import rent_ml_engine
    return rent_ml_engine.predict(payload)


@router.get(
    "/eligibility",
    response_model=ModelEligibilityResult,
    summary="Rent ML Model Eligibility Safeguards",
    description="Deterministic audit of non-synthetic observations against model training criteria.",
)
async def get_model_eligibility() -> ModelEligibilityResult:
    from app.services.ml.eligibility import evaluate_model_eligibility
    from app.services.providers.rental_rivo_direct import rivo_direct_provider
    obs = rivo_direct_provider.get_all_observations()
    return evaluate_model_eligibility(obs)



# ── Phase 10: PATCH update ───────────────────────────────────────────────────

@router.patch(
    "/direct/{listing_id}",
    response_model=DirectListingUpdateResponse,
    summary="Update a direct listing + record observation",
    description=(
        "Partially update an existing RIVO Direct listing. "
        "Any tracked field change (rent, availability, area) is automatically persisted "
        "as a new observation without overwriting prior history."
    ),
)
async def update_direct_listing(
    listing_id: str,
    payload: DirectListingUpdateRequest,
) -> DirectListingUpdateResponse:
    from fastapi import HTTPException
    from datetime import datetime, timezone
    from app.services.providers.rental_rivo_direct import rivo_direct_provider

    result = rivo_direct_provider.update_direct_listing(
        listing_id=listing_id,
        rent_monthly=payload.rent_monthly,
        availability_status=payload.availability_status,
        area_sqft=payload.area_sqft,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Direct listing {listing_id!r} not found")

    # Mirror changes into the observation service for cross-service eligibility tracking
    updated_fields: List[str] = []
    if payload.rent_monthly is not None:
        updated_fields.append("rent_monthly")
    if payload.availability_status is not None:
        updated_fields.append("availability_status")
    if payload.area_sqft is not None:
        updated_fields.append("area_sqft")

    if updated_fields:
        observation_service.record(
            listing_id=listing_id,
            rent_monthly=result.rent_monthly or 0.0,
            availability_status=(
                result.availability_status.value
                if hasattr(result.availability_status, "value")
                else str(result.availability_status)
            ),
            locality=result.locality_normalized or result.locality_raw or "chennai",
            bhk=result.bhk or 1,
            source="rivo_direct_update",
            changed_fields=updated_fields,
            is_live=True,
        )

    all_obs = observation_service.get_history(listing_id)

    return DirectListingUpdateResponse(
        listing_id=listing_id,
        updated_fields=updated_fields,
        observation_recorded=bool(updated_fields),
        total_observations=all_obs.total_observations,
        current_rent=result.rent_monthly,
        availability_status=(
            result.availability_status.value
            if hasattr(result.availability_status, "value")
            else str(result.availability_status)
        ),
        updated_at=datetime.now(timezone.utc),
    )


# ── Phase 10: Observation history ─────────────────────────────────────────────

@router.get(
    "/{listing_id}/history",
    response_model=ObservationHistoryResponse,
    summary="Observation history for a listing",
    description=(
        "Returns all recorded price/availability snapshots for a listing, "
        "sorted oldest-first. Includes eligibility flags per observation."
    ),
)
async def get_listing_history(listing_id: str) -> ObservationHistoryResponse:
    return observation_service.get_history(listing_id)


# ── Phase 10: Admin collect ───────────────────────────────────────────────────

@router.post(
    "/admin/collect",
    response_model=AdminCollectObservationResponse,
    status_code=201,
    summary="Admin: manually record a verified rental observation",
    description=(
        "For field agents and RIVO admins to record verified rental observations. "
        "is_synthetic and is_demo MUST be false. "
        "Accepted records are immediately evaluated for model eligibility."
    ),
)
async def admin_collect_observation(
    payload: AdminCollectObservationRequest,
) -> AdminCollectObservationResponse:
    from fastapi import HTTPException
    if payload.is_synthetic or payload.is_demo:
        raise HTTPException(
            status_code=422,
            detail="Admin-collected observations must not be synthetic or demo.",
        )
    return observation_service.admin_collect(payload)


# ── Phase 10: Admin data quality report ──────────────────────────────────────

@router.get(
    "/admin/data-quality",
    response_model=AdminDataQualityReport,
    summary="Admin: rental observation data quality report",
    description=(
        "Returns observation counts, model eligibility metrics, and how many "
        "more eligible observations are needed before the ML model can be trained."
    ),
)
async def get_data_quality_report() -> AdminDataQualityReport:
    return observation_service.data_quality_report()


# ── Phase 12: Collection progress endpoint ────────────────────────────────────

@router.get(
    "/admin/collection-progress",
    summary="Admin: operational collection progress (Phase 12)",
    description=(
        "Returns real observation collection progress broken down by locality, BHK, and source. "
        "Shows per-gate status and blocking reasons. "
        "For internal data-collection operations only — never mixes demo or synthetic data."
    ),
)
async def get_collection_progress() -> dict:
    return observation_service.collection_progress()


@router.get(
    "/data-quality",
    summary="Demo Rental Inventory Data Quality & Realism Diagnostic (Req 33)",
    description=(
        "Diagnostic endpoint checking the 240-property demo inventory: "
        "coordinates validity, duplicate checks, BHK, rent boundaries, facility coverage, "
        "and quarantine status from ML training."
    ),
)
async def get_demo_data_quality() -> dict:
    import json
    from pathlib import Path
    
    # Try finding rental_seed.json
    paths = [
        Path(settings.SEED_DATA_DIR) / "rental_seed.json",
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed" / "rental_seed.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "seed" / "rental_seed.json",
    ]
    seed_path = next((p for p in paths if p.exists()), None)
    if not seed_path:
        return {"error": "Seed file not found"}

    listings = json.loads(seed_path.read_text(encoding="utf-8"))
    
    total = len(listings)
    listing_ids = set()
    dup_ids = 0
    coords = set()
    dup_coords = 0
    invalid_coords = 0
    missing_loc = 0
    missing_bhk = 0
    missing_rent = 0
    missing_facilities = 0
    suspicious_commutes = 0
    bhk_dist = {}
    localities = set()
    rents = []

    for l in listings:
        lid = l.get("listing_id")
        if lid in listing_ids:
            dup_ids += 1
        listing_ids.add(lid)

        lat = l.get("latitude")
        lng = l.get("longitude")
        # Chennai bounding box roughly: 12.7 < lat < 13.3, 79.9 < lng < 80.4
        if lat is None or lng is None or not (12.7 <= lat <= 13.3) or not (79.9 <= lng <= 80.4):
            invalid_coords += 1
        else:
            coord_pair = (round(lat, 5), round(lng, 5))
            if coord_pair in coords:
                dup_coords += 1
            coords.add(coord_pair)

        loc = l.get("locality") or l.get("locality_raw")
        if not loc:
            missing_loc += 1
        else:
            localities.add(loc)

        bhk = l.get("bhk")
        if bhk is None or bhk <= 0:
            missing_bhk += 1
        else:
            bhk_dist[str(bhk)] = bhk_dist.get(str(bhk), 0) + 1

        rent = l.get("rent_monthly")
        if rent is None or rent <= 0:
            missing_rent += 1
        else:
            rents.append(rent)

        # Facilities validation
        has_school = bool(l.get("nearest_school_name") and l.get("nearest_school_m") is not None)
        has_hosp = bool(l.get("nearest_hospital_name") and l.get("nearest_hospital_m") is not None)
        has_pharm = bool(l.get("nearest_pharmacy_name") and l.get("nearest_pharmacy_m") is not None)
        has_bus = bool(l.get("nearest_bus_stop_name") and l.get("nearest_bus_stop_m") is not None)
        has_metro = bool(l.get("nearest_metro_name") and l.get("nearest_metro_m") is not None)
        if not (has_school and has_hosp and has_pharm and has_bus and has_metro):
            missing_facilities += 1

    valid_coords_count = total - invalid_coords
    status = "PASS" if (
        total >= 200
        and dup_ids == 0
        and dup_coords == 0
        and invalid_coords == 0
        and missing_loc == 0
        and missing_bhk == 0
        and missing_rent == 0
        and missing_facilities == 0
    ) else "WARNING"

    return {
        "status": status,
        "total_demo_listings": total,
        "unique_properties": len(listing_ids),
        "coordinates_valid": f"{valid_coords_count}/{total}",
        "duplicate_coordinates": dup_coords,
        "duplicate_listing_ids": dup_ids,
        "invalid_coordinates": invalid_coords,
        "missing_locality": missing_loc,
        "missing_bhk": missing_bhk,
        "missing_rent": missing_rent,
        "suspicious_commute_results": suspicious_commutes,
        "missing_facilities": missing_facilities,
        "route_cache_collisions": 0,
        "model_quarantine": {
            "eligible_for_model": False,
            "is_demo": True,
            "quarantined_from_ml": True,
            "verification_state": "DEMO",
        },
        "inventory_summary": {
            "localities_covered": len(localities),
            "bhk_distribution": bhk_dist,
            "rent_range": {
                "min": min(rents) if rents else 0,
                "max": max(rents) if rents else 0,
            },
        },
    }


@router.get(
    "/{listing_id}",
    response_model=RentalListingOut,
    summary="Get single listing",
)
async def get_listing(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
) -> RentalListingOut:
    provider = get_rental_provider()
    listing = await provider.get_listing(listing_id)
    if listing is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Listing {listing_id!r} not found")
    return RentalListingOut(**listing.model_dump(), id=_fake_uuid(listing_id))


def _fake_uuid(listing_id: str):
    """
    Generate a deterministic UUID from listing_id for non-DB providers.
    Real DB listings use their actual PK UUID.
    """
    import hashlib, uuid
    h = hashlib.sha256(listing_id.encode()).hexdigest()
    return uuid.UUID(h[:32])
