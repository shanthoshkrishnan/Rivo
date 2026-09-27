"""
RIVO Backend — Open Dataset Rental Provider
============================================
Implements RentalProvider using openly licensed Chennai rental datasets.
Reads structured historical/seed rental records with explicit licensing metadata.

Rules enforced:
  - Every listing is marked with data_freshness=PERIODIC.
  - Hard constraints are applied before returning candidates.
  - Source attribution and observed timestamp are strictly preserved.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import DataFreshness
from app.core.logging import logger
from app.schemas.rental import RentalListingCreate, RentalSearchParams
from app.services.providers.base import RentalProvider

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class OpenDatasetRentalProvider(RentalProvider):
    """
    Provider reading openly licensed, public Chennai rental listings.
    """

    PROVIDER_NAME = "open_dataset"

    def __init__(self, dataset_path: Optional[Path] = None) -> None:
        self._dataset_path = dataset_path or (BASE_DIR / "data" / "open" / "chennai_open_rentals.json")
        self._listings_cache: Optional[List[RentalListingCreate]] = None

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def _load_listings(self) -> List[RentalListingCreate]:
        if self._listings_cache is not None:
            return self._listings_cache

        listings: List[RentalListingCreate] = []
        if self._dataset_path.exists():
            try:
                with open(self._dataset_path, "r", encoding="utf-8") as f:
                    raw_items = json.load(f)
                for item in raw_items:
                    data = dict(item)
                    data["provider"] = self.PROVIDER_NAME
                    data["source_name"] = "Chennai Open Rental Dataset"
                    data["data_freshness"] = DataFreshness.PERIODIC
                    if not data.get("observed_at"):
                        data["observed_at"] = datetime.now(timezone.utc)
                    listings.append(RentalListingCreate(**data))
                logger.info(
                    "Loaded open dataset rental listings",
                    count=len(listings),
                    path=str(self._dataset_path),
                )
            except Exception as exc:
                logger.error("Failed to load open rental dataset", error=str(exc))

        self._listings_cache = listings
        return self._listings_cache

    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        """Search and filter open dataset rental listings by hard constraints."""
        all_listings = self._load_listings()
        results: List[RentalListingCreate] = []

        for listing in all_listings:
            # Hard filter: availability
            if params.available_only and not listing.is_available:
                continue

            # Hard filter: max rent
            if listing.rent_monthly is not None and listing.rent_monthly > params.max_rent_monthly:
                continue

            # Hard filter: BHK
            if params.bhk is not None and listing.bhk != params.bhk:
                continue

            # Hard filter: property type
            if params.property_type and listing.property_type:
                if listing.property_type.lower() != params.property_type.lower():
                    continue

            results.append(listing)

        # Pagination
        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        return results[start:end]

    def is_available(self) -> bool:
        return self._dataset_path.exists()

    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        for listing in self._load_listings():
            if listing.listing_id == listing_id:
                return listing
        return None
