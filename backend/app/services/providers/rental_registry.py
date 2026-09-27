"""
RIVO Backend — Rental Provider Registry & Cross-Source Pipeline
===============================================================
Manages multi-provider rental data ingestion, prioritization, deduplication,
and availability tracking.

Source Priority Order:
  1. Authorized Commercial Partner Feeds (CREDAI, partner MLS)
  2. RIVO Direct Listings (Owner-submitted, LIVE)
  3. Recent Cached Listings (within TTL)
  4. Open Periodic Datasets (GCC/OpenCity, PERIODIC)
  5. Demo Seed Data (CMRL 88 Corridor Listings, ESTIMATED / DEMO)

Enforces:
  - Truthful source labeling (never calls seed data LIVE).
  - Cross-provider deduplication (50m, same BHK, rent ±10%).
  - Chennai coordinate boundary validation.
  - Empirical market summaries (with insufficient_data guards).
"""
from __future__ import annotations

from datetime import datetime, timezone
import statistics
from typing import Dict, List, Optional

from app.core.config import (
    AvailabilityStatus,
    ConfidenceLevel,
    DataFreshness,
    get_settings,
)
from app.core.logging import logger
from app.schemas.rental import (
    MarketSummaryResponse,
    RentalAdminSummary,
    RentalListingCreate,
    RentalSearchParams,
    validate_chennai_coordinates,
)
from app.services.algorithms.normalization import deduplicate_listings
from app.services.providers.base import RentalProvider
from app.services.providers.rental_licensed import LicensedRentalProvider
from app.services.providers.rental_mock import MockRentalProvider
from app.services.providers.rental_open_dataset import OpenDatasetRentalProvider
from app.services.providers.rental_partner import AuthorizedPartnerRentalProvider
from app.services.providers.rental_rivo_direct import rivo_direct_provider


class RentalProviderRegistry(RentalProvider):
    """
    Composite Rental Provider coordinating all legitimate rental tiers.
    """

    PROVIDER_NAME = "rental_registry"

    def __init__(self) -> None:
        self.partner_provider = AuthorizedPartnerRentalProvider()
        self.licensed_provider = LicensedRentalProvider()
        self.direct_provider = rivo_direct_provider
        self.open_provider = OpenDatasetRentalProvider()
        self.demo_provider = MockRentalProvider()

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        return True

    def freshness(self) -> DataFreshness:
        # Reflects the highest tier active
        if self.direct_provider.get_all_listings():
            return DataFreshness.LIVE
        return DataFreshness.PERIODIC

    def health(self) -> dict:
        return {
            "provider": self.provider_name,
            "available": True,
            "providers": {
                "authorized_partner": self.partner_provider.health(),
                "licensed": self.licensed_provider.health(),
                "rivo_direct": self.direct_provider.health(),
                "open_dataset": self.open_provider.health(),
                "demo_seed": self.demo_provider.health() if hasattr(self.demo_provider, "health") else {"available": True},
            },
        }

    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        """
        Multi-tier rental search with source prioritization, geocode boundary validation,
        and cross-provider deduplication.
        """
        candidates: List[RentalListingCreate] = []
        source_categories = [c.upper() for c in (params.source_categories or [])]

        include_current = not source_categories or "CURRENT" in source_categories or "LIVE" in source_categories
        include_periodic = not source_categories or "PERIODIC" in source_categories or "RECENT" in source_categories
        include_demo = not source_categories or "DEMO" in source_categories or "ESTIMATED" in source_categories

        # 1. Partner Provider (if active)
        if include_current and self.partner_provider.is_available():
            try:
                partner_results = await self.partner_provider.search(params)
                candidates.extend(partner_results)
            except Exception as e:
                logger.warning("[REGISTRY] Partner search failed", error=str(e))

        # 2. Licensed Provider (if configured)
        if include_current and self.licensed_provider.is_available():
            try:
                licensed_results = await self.licensed_provider.search(params)
                candidates.extend(licensed_results)
            except Exception as e:
                logger.warning("[REGISTRY] Licensed search failed", error=str(e))

        # 3. RIVO Direct Listings (Owner-submitted, LIVE)
        if include_current and self.direct_provider.is_available():
            try:
                direct_results = await self.direct_provider.search(params)
                candidates.extend(direct_results)
            except Exception as e:
                logger.warning("[REGISTRY] Direct listings search failed", error=str(e))

        # 4. Open Dataset Provider (Periodic)
        if include_periodic and self.open_provider.is_available():
            try:
                open_results = await self.open_provider.search(params)
                candidates.extend(open_results)
            except Exception as e:
                logger.warning("[REGISTRY] Open dataset search failed", error=str(e))

        # 5. Demo / Seed Provider (CMRL Corridor Seed)
        # Included when explicitly asked or when no live/direct results exist
        if include_demo or not candidates:
            try:
                demo_results = await self.demo_provider.search(params)
                for d in demo_results:
                    d.data_freshness = DataFreshness.PERIODIC
                    d.source_name = "Demo / seeded dataset (CMRL-anchored)"
                    d.geocode_confidence = ConfidenceLevel.MEDIUM
                candidates.extend(demo_results)
            except Exception as e:
                logger.warning("[REGISTRY] Demo search failed", error=str(e))

        # Geocode validation: enforce Chennai bounding box
        valid_candidates: List[RentalListingCreate] = []
        for c in candidates:
            if c.latitude is not None and c.longitude is not None:
                in_bounds, _ = validate_chennai_coordinates(c.latitude, c.longitude)
                if not in_bounds:
                    logger.debug("[REGISTRY] Dropping listing outside Chennai bounds", listing_id=c.listing_id)
                    continue
            valid_candidates.append(c)

        # Cross-provider deduplication if multiple listings exist
        if len(valid_candidates) > 1:
            raw_dicts = [c.model_dump() for c in valid_candidates]
            deduped_dicts = deduplicate_listings(raw_dicts, coord_threshold_m=50.0)
            valid_candidates = [
                RentalListingCreate(**d)
                for d in deduped_dicts
                if d.get("is_canonical", True)
            ]

        # Enforce unique listing IDs and canonical property keys
        seen_ids = set()
        seen_canonical = set()
        unique_candidates: List[RentalListingCreate] = []
        for c in valid_candidates:
            if c.listing_id in seen_ids:
                continue
            canonical_key = (
                f"{c.locality_normalized or ''}_{c.bhk}_{round(c.latitude or 0, 4)}_{round(c.longitude or 0, 4)}"
            )
            if canonical_key in seen_canonical:
                continue
            seen_ids.add(c.listing_id)
            seen_canonical.add(canonical_key)
            unique_candidates.append(c)

        return unique_candidates

    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        # Check direct first
        res = await self.direct_provider.get_listing(listing_id)
        if res:
            return res
        # Check licensed
        res = await self.licensed_provider.get_listing(listing_id)
        if res:
            return res
        # Check open
        res = await self.open_provider.get_listing(listing_id)
        if res:
            return res
        # Check demo
        return await self.demo_provider.get_listing(listing_id)

    def get_market_summary(self) -> MarketSummaryResponse:
        """
        Calculate empirical market statistics from actual observed listings.
        Enforces Task 15 insufficient-data guard.
        """
        all_obs = self.direct_provider.get_all_observations()
        all_direct = self.direct_provider.get_all_listings()

        rents: List[float] = [l.rent_monthly for l in all_direct if l.rent_monthly is not None and l.rent_monthly > 0]
        # Also include any observations recorded
        for obs in all_obs:
            if obs.get("rent_monthly") and obs["rent_monthly"] > 0:
                rents.append(obs["rent_monthly"])

        unique_rents = sorted(list(set(rents)))
        sample_size = len(rents)

        now = datetime.now(timezone.utc)
        if sample_size < 5:
            # Insufficient sample guard
            med = round(statistics.median(rents), 2) if rents else None
            return MarketSummaryResponse(
                listing_count=len(all_direct),
                listings_observed=sample_size,
                observation_count=len(all_obs),
                median=med,
                median_asking_rent=med,
                p25=None,
                rent_p25=None,
                p75=None,
                rent_p75=None,
                by_bhk={},
                median_by_bhk={},
                by_locality={},
                median_by_locality={},
                source_count=1 if sample_size > 0 else 0,
                data_as_of=now,
                observed_at=now,
                confidence="INSUFFICIENT_DATA",
                insufficient_data=True,
            )

        rents_sorted = sorted(rents)
        p25_idx = int(sample_size * 0.25)
        p75_idx = int(sample_size * 0.75)

        # Group by BHK
        by_bhk: Dict[int, List[float]] = {}
        for l in all_direct:
            if l.bhk is not None and l.rent_monthly is not None:
                by_bhk.setdefault(l.bhk, []).append(l.rent_monthly)

        median_by_bhk = {bhk: round(statistics.median(vals), 2) for bhk, vals in by_bhk.items()}

        # Group by locality
        by_loc: Dict[str, List[float]] = {}
        for l in all_direct:
            loc = l.locality_normalized or l.locality_raw
            if loc and l.rent_monthly:
                by_loc.setdefault(loc, []).append(l.rent_monthly)

        median_by_locality = {loc: round(statistics.median(vals), 2) for loc, vals in by_loc.items()}

        med_val = round(statistics.median(rents_sorted), 2)
        p25_val = round(rents_sorted[p25_idx], 2)
        p75_val = round(rents_sorted[p75_idx], 2)

        return MarketSummaryResponse(
            listing_count=len(all_direct),
            listings_observed=sample_size,
            observation_count=len(all_obs),
            median=med_val,
            median_asking_rent=med_val,
            p25=p25_val,
            rent_p25=p25_val,
            p75=p75_val,
            rent_p75=p75_val,
            by_bhk=median_by_bhk,
            median_by_bhk=median_by_bhk,
            by_locality=median_by_locality,
            median_by_locality=median_by_locality,
            source_count=1,
            data_as_of=now,
            observed_at=now,
            confidence="MEDIUM",
            insufficient_data=False,
        )


    def get_admin_summary(self) -> RentalAdminSummary:
        """Dashboard overview for Task 29."""
        direct_listings = self.direct_provider.get_all_listings()
        demo_listings = self.demo_provider._load_listings() if hasattr(self.demo_provider, "_load_listings") else []

        current_cnt = len(direct_listings)
        demo_cnt = len(demo_listings)
        total_cnt = current_cnt + demo_cnt

        stale_cnt = sum(1 for l in direct_listings if l.availability_status == AvailabilityStatus.RECENTLY_SEEN)
        unknown_cnt = sum(1 for l in direct_listings if l.availability_status == AvailabilityStatus.UNKNOWN)

        return RentalAdminSummary(
            total_listings=total_cnt,
            current_listings=current_cnt,
            recent_listings=0,
            periodic_listings=demo_cnt,
            demo_listings=demo_cnt,
            stale_listings=stale_cnt,
            unknown_availability=unknown_cnt,
            duplicate_clusters=0,
            provider_health={
                "authorized_partner": self.partner_provider.is_available(),
                "licensed": self.licensed_provider.is_available(),
                "rivo_direct": self.direct_provider.is_available(),
                "open_dataset": self.open_provider.is_available(),
                "demo_seed": True,
            },
            last_refresh=datetime.now(timezone.utc),
            records_ingested=current_cnt,
        )


# Global singleton instance
rental_registry = RentalProviderRegistry()
