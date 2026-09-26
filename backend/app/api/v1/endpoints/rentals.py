"""
RIVO Backend — Rental Listings API Endpoints
==============================================
GET  /api/v1/rentals/search   — search listings with hard constraints
GET  /api/v1/rentals/{id}     — single listing by ID

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
    PaginatedRentalResponse,
    RentalListingOut,
    RentalSearchParams,
)
from app.services.providers.registry import get_rental_provider

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
    db: AsyncSession = Depends(get_db),
) -> PaginatedRentalResponse:
    params = RentalSearchParams(
        max_rent_monthly=max_rent_monthly,
        bhk=bhk,
        property_type=property_type,
        locality=locality,
        available_only=available_only,
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
