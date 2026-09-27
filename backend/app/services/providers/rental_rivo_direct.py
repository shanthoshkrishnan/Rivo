"""
RIVO Backend — First-Party RIVO Direct Rental Provider
======================================================
Implements RentalProvider for direct owner/landlord/agent submitted listings.

Features:
  - First-party control without relying on unauthorized external scrapers.
  - Strict input validation and coordinate bounds checking for Chennai.
  - Generates unique RIVO-DIR-xxxx listing IDs.
  - Automatically records rental observations for market trend tracking.
  - Fully functional and immediately search-ready.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional
import uuid

from app.core.config import (
    AvailabilityStatus,
    ConfidenceLevel,
    DataFreshness,
    VerificationStatus,
)
from app.core.logging import logger
from app.schemas.rental import (
    DirectRentalSubmissionRequest,
    RentalListingCreate,
    RentalSearchParams,
    validate_chennai_coordinates,
)
from app.services.algorithms.normalization import (
    normalize_bhk,
    normalize_furnishing,
    normalize_locality,
    normalize_property_type,
    normalize_rent,
)
from app.services.providers.base import RentalProvider


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RivoDirectListingProvider(RentalProvider):
    """
    Manages direct, first-party Chennai rental listings submitted by owners or verified agents.
    """

    PROVIDER_NAME = "rivo_direct"

    def __init__(self) -> None:
        # In-memory store for active session direct listings
        self._listings: Dict[str, RentalListingCreate] = {}
        # Observation history log
        self._observations: List[dict] = []

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        return True

    def freshness(self) -> DataFreshness:
        return DataFreshness.LIVE

    def health(self) -> dict:
        return {
            "provider": self.provider_name,
            "available": True,
            "status": "ACTIVE",
            "active_listings": len(self._listings),
            "freshness": self.freshness().value,
        }

    def add_direct_listing(self, req: DirectRentalSubmissionRequest) -> RentalListingCreate:
        """
        Validate, geocode-check, normalize, and register a new direct rental listing.
        """
        valid_coords, coord_err = validate_chennai_coordinates(req.latitude, req.longitude)
        if not valid_coords:
            raise ValueError(coord_err or "Coordinates outside Chennai pilot region")

        now = datetime.now(timezone.utc)
        listing_id = f"RIVO-DIR-{uuid.uuid4().hex[:8].upper()}"

        norm_locality = normalize_locality(req.locality)
        norm_bhk = normalize_bhk(req.bhk) or 1
        norm_rent = normalize_rent(req.rent_monthly) or req.rent_monthly
        norm_furnishing = normalize_furnishing(req.furnishing)
        norm_prop_type = normalize_property_type(req.property_type) or "flat"

        listing = RentalListingCreate(
            listing_id=listing_id,
            provider=self.PROVIDER_NAME,
            city="Chennai",
            locality_raw=req.locality,
            locality_normalized=norm_locality,
            address_raw=req.address or req.locality,
            latitude=req.latitude,
            longitude=req.longitude,
            geocode_confidence=ConfidenceLevel.HIGH,
            rent_monthly=norm_rent,
            maintenance_monthly=req.maintenance_monthly,
            deposit=req.deposit,
            bhk=norm_bhk,
            bedrooms=norm_bhk,
            area_sqft=req.area_sqft,
            furnishing=norm_furnishing,
            property_type=norm_prop_type,
            is_available=True,
            availability_status=req.availability_status,
            verification_status=VerificationStatus.OWNER_ATTESTED,
            source_name="RIVO Direct (Owner Verified)",
            source_url=f"/rentals/direct/{listing_id}",
            data_freshness=DataFreshness.LIVE,
            observed_at=now,
            first_seen_at=now,
            last_seen_at=now,
            consent_given=req.consent_to_publish,
            is_canonical=True,
        )

        self._listings[listing_id] = listing

        # Record observation
        self.record_observation(
            listing_id=listing_id,
            rent=norm_rent,
            availability=req.availability_status.value,
            locality=norm_locality or req.locality,
            bhk=norm_bhk,
            source="rivo_direct",
        )

        logger.info(
            "[RIVO DIRECT] Ingested direct listing",
            listing_id=listing_id,
            locality=req.locality,
            rent=norm_rent,
            bhk=norm_bhk,
        )
        return listing

    def record_observation(
        self,
        listing_id: str,
        rent: float,
        availability: str,
        locality: str,
        bhk: int,
        source: str,
        changed_fields: Optional[List[str]] = None,
    ) -> None:
        """Log an empirical rental observation."""
        self._observations.append(
            {
                "listing_id": listing_id,
                "observed_at": datetime.now(timezone.utc),
                "rent_monthly": rent,
                "availability_status": availability,
                "locality": locality,
                "bhk": bhk,
                "source": source,
                "changed_fields": changed_fields or ["initial_observation"],
            }
        )

    def update_direct_listing(
        self,
        listing_id: str,
        rent_monthly: Optional[float] = None,
        availability_status: Optional[AvailabilityStatus] = None,
        area_sqft: Optional[float] = None,
    ) -> Optional[RentalListingCreate]:
        """
        Updates an existing direct listing and records a new observation without overwriting history.
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return None

        changed: List[str] = []
        if rent_monthly is not None and rent_monthly != listing.rent_monthly:
            listing.rent_monthly = rent_monthly
            changed.append("rent_monthly")

        if availability_status is not None and availability_status != listing.availability_status:
            listing.availability_status = availability_status
            changed.append("availability_status")

        if area_sqft is not None and area_sqft != listing.area_sqft:
            listing.area_sqft = area_sqft
            changed.append("area_sqft")

        now = datetime.now(timezone.utc)
        listing.last_seen_at = now
        listing.observed_at = now

        if changed:
            self.record_observation(
                listing_id=listing_id,
                rent=listing.rent_monthly or 0.0,
                availability=listing.availability_status.value if hasattr(listing.availability_status, "value") else str(listing.availability_status),
                locality=listing.locality_normalized or listing.locality_raw or "chennai",
                bhk=listing.bhk or 1,
                source=self.PROVIDER_NAME,
                changed_fields=changed,
            )

        return listing

    def get_all_observations(self) -> List[dict]:
        return list(self._observations)


    def get_all_listings(self) -> List[RentalListingCreate]:
        return list(self._listings.values())

    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        results: List[RentalListingCreate] = []

        for listing in self._listings.values():
            if params.available_only and not listing.is_available:
                continue
            if listing.rent_monthly is not None and listing.rent_monthly > params.max_rent_monthly:
                continue
            if params.bhk is not None and listing.bhk != params.bhk:
                continue
            if params.property_type and listing.property_type:
                if listing.property_type.lower() != params.property_type.lower():
                    continue

            # Spatial filter if coordinates supplied
            if params.latitude is not None and params.longitude is not None:
                if listing.latitude is not None and listing.longitude is not None:
                    d = _haversine_km(params.latitude, params.longitude, listing.latitude, listing.longitude)
                    if d > params.radius_km:
                        continue

            results.append(listing)

        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        return results[start:end]

    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        return self._listings.get(listing_id)


# Global singleton instance for in-memory direct listings
rivo_direct_provider = RivoDirectListingProvider()
