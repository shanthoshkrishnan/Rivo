"""
RIVO Backend — Mock Rental Provider
=====================================
Provides deterministic, clearly-labelled SAMPLE rental listings
for Chennai so the application is fully demoable without any
external credentials or licensed data.

Rules enforced here:
  - Every listing is tagged data_freshness=PERIODIC and
    source_name="RIVO Sample Data" so the UI can warn users.
  - Listings are seeded from data/seed/rental_seed.json if it
    exists, otherwise generated from a fixture template.
  - No personal phone numbers or real individual data.
  - Values are realistic for Chennai 2024–25 but NOT ground truth.
  - This provider MUST NOT be used in production without review.

Label displayed to end users:
  ⚠ SAMPLE DATA — not verified rental listings
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.schemas.rental import RentalListingCreate, RentalSearchParams
from app.services.providers.base import RentalProvider

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded fixture listings (used when seed file absent)
# ─────────────────────────────────────────────────────────────────────────────
_FIXTURE_LISTINGS = [
    {
        "listing_id": "MOCK-001",
        "locality_raw": "Velachery",
        "locality_normalized": "velachery",
        "latitude": 12.9751,
        "longitude": 80.2202,
        "rent_monthly": 12000,
        "maintenance_monthly": 800,
        "deposit": 36000,
        "bhk": 2,
        "area_sqft": 850,
        "furnishing": "semi-furnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "family/working professional",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-002",
        "locality_raw": "Tambaram",
        "locality_normalized": "tambaram",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "rent_monthly": 8500,
        "maintenance_monthly": 500,
        "deposit": 25500,
        "bhk": 1,
        "area_sqft": 550,
        "furnishing": "unfurnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "any",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-003",
        "locality_raw": "Adyar",
        "locality_normalized": "adyar",
        "latitude": 13.0012,
        "longitude": 80.2565,
        "rent_monthly": 18000,
        "maintenance_monthly": 1200,
        "deposit": 54000,
        "bhk": 2,
        "area_sqft": 1050,
        "furnishing": "fully-furnished",
        "property_type": "flat",
        "bathrooms": 2,
        "tenant_preference": "family",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-004",
        "locality_raw": "Medavakkam",
        "locality_normalized": "medavakkam",
        "latitude": 12.9201,
        "longitude": 80.1929,
        "rent_monthly": 10000,
        "maintenance_monthly": 600,
        "deposit": 30000,
        "bhk": 2,
        "area_sqft": 780,
        "furnishing": "semi-furnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "any",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-005",
        "locality_raw": "Perambur",
        "locality_normalized": "perambur",
        "latitude": 13.1148,
        "longitude": 80.2320,
        "rent_monthly": 7000,
        "maintenance_monthly": 400,
        "deposit": 21000,
        "bhk": 1,
        "area_sqft": 480,
        "furnishing": "unfurnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "working professional",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-006",
        "locality_raw": "Sholinganallur",
        "locality_normalized": "sholinganallur",
        "latitude": 12.9010,
        "longitude": 80.2279,
        "rent_monthly": 15000,
        "maintenance_monthly": 1000,
        "deposit": 45000,
        "bhk": 3,
        "area_sqft": 1200,
        "furnishing": "semi-furnished",
        "property_type": "flat",
        "bathrooms": 2,
        "tenant_preference": "family",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-007",
        "locality_raw": "Porur",
        "locality_normalized": "porur",
        "latitude": 13.0358,
        "longitude": 80.1560,
        "rent_monthly": 11000,
        "maintenance_monthly": 700,
        "deposit": 33000,
        "bhk": 2,
        "area_sqft": 820,
        "furnishing": "unfurnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "any",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-008",
        "locality_raw": "Chromepet",
        "locality_normalized": "chromepet",
        "latitude": 12.9516,
        "longitude": 80.1462,
        "rent_monthly": 9000,
        "maintenance_monthly": 550,
        "deposit": 27000,
        "bhk": 2,
        "area_sqft": 700,
        "furnishing": "unfurnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "family",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-009",
        "locality_raw": "Anna Nagar",
        "locality_normalized": "anna_nagar",
        "latitude": 13.0850,
        "longitude": 80.2101,
        "rent_monthly": 22000,
        "maintenance_monthly": 1500,
        "deposit": 66000,
        "bhk": 3,
        "area_sqft": 1400,
        "furnishing": "fully-furnished",
        "property_type": "flat",
        "bathrooms": 2,
        "tenant_preference": "any",
        "is_available": True,
    },
    {
        "listing_id": "MOCK-010",
        "locality_raw": "Avadi",
        "locality_normalized": "avadi",
        "latitude": 13.1148,
        "longitude": 80.0989,
        "rent_monthly": 6000,
        "maintenance_monthly": 350,
        "deposit": 18000,
        "bhk": 1,
        "area_sqft": 420,
        "furnishing": "unfurnished",
        "property_type": "flat",
        "bathrooms": 1,
        "tenant_preference": "any",
        "is_available": True,
    },
]


class MockRentalProvider(RentalProvider):
    """
    Returns clearly-labelled sample listings for Chennai.
    Reads from data/seed/rental_seed.json if present, otherwise
    falls back to the hardcoded fixture above.

    WARNING: These are NOT real listings. Display prominently in the UI.
    """

    PROVIDER_NAME = "mock"

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        return True   # Mock is always available

    def _load_listings(self) -> List[dict]:
        seed_path = Path(settings.SEED_DATA_DIR) / "rental_seed.json"
        if seed_path.exists():
            try:
                data = json.loads(seed_path.read_text(encoding="utf-8"))
                logger.info("Loaded rental seed data", path=str(seed_path), count=len(data))
                return data
            except Exception as exc:
                logger.warning("Seed file unreadable; using fixture", error=str(exc))
        return _FIXTURE_LISTINGS

    def _to_schema(self, raw: dict) -> RentalListingCreate:
        return RentalListingCreate(
            listing_id=raw["listing_id"],
            provider=self.PROVIDER_NAME,
            city="Chennai",
            locality_raw=raw.get("locality_raw"),
            locality_normalized=raw.get("locality_normalized"),
            latitude=raw.get("latitude"),
            longitude=raw.get("longitude"),
            rent_monthly=raw.get("rent_monthly"),
            maintenance_monthly=raw.get("maintenance_monthly"),
            deposit=raw.get("deposit"),
            bhk=raw.get("bhk"),
            area_sqft=raw.get("area_sqft"),
            furnishing=raw.get("furnishing"),
            property_type=raw.get("property_type"),
            bathrooms=raw.get("bathrooms"),
            tenant_preference=raw.get("tenant_preference"),
            is_available=raw.get("is_available", True),
            observed_at=datetime.now(timezone.utc),
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            source_name="RIVO Sample Data",
            source_url=None,
            data_freshness=DataFreshness.PERIODIC,
        )

    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        """
        Apply hard filters (rent, BHK, property_type) then return matching
        sample listings.

        Filtering order per AGENTS.md:
          1. availability
          2. property type
          3. BHK
          4. hard rent budget
        """
        raw_listings = self._load_listings()
        results: List[RentalListingCreate] = []

        for raw in raw_listings:
            # 1. Availability
            if params.available_only and not raw.get("is_available", True):
                continue
            # 2. Property type (hard constraint if specified)
            if params.property_type and raw.get("property_type") != params.property_type.lower():
                continue
            # 3. BHK (hard constraint if specified)
            if params.bhk is not None and raw.get("bhk") != params.bhk:
                continue
            # 4. Hard rent budget
            rent = raw.get("rent_monthly", 0) or 0
            if rent > params.max_rent_monthly:
                continue
            # 5. Locality filter (partial match)
            if params.locality:
                loc_norm = (raw.get("locality_normalized") or "").lower()
                loc_raw = (raw.get("locality_raw") or "").lower()
                search_loc = params.locality.lower()
                if search_loc not in loc_norm and search_loc not in loc_raw:
                    continue
            results.append(self._to_schema(raw))

        logger.debug(
            "MockRentalProvider search",
            total_listings=len(raw_listings),
            matched=len(results),
        )
        return results

    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        for raw in self._load_listings():
            if raw.get("listing_id") == listing_id:
                return self._to_schema(raw)
        return None
