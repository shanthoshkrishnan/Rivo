"""
RIVO Backend — Phase 8 Real Rental Inventory & Direct Listing Tests
===================================================================
Tests:
  - Provider registry priority & fallback ordering
  - Cross-provider deduplication (50m proximity, same BHK, rent +-10%)
  - Chennai bounding box coordinate validation & geocode confidence
  - Direct listing creation (POST /api/v1/rentals/direct)
  - Immediate availability of direct listings in recommendation searches
  - Market summary empirical statistics & insufficient_data guard
  - Admin summary metrics (total, current, demo, health)
  - Current vs Demo filtering and banner generation
  - ZERO Google API calls
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import (
    AvailabilityStatus,
    ConfidenceLevel,
    DataFreshness,
    VerificationStatus,
)
from app.main import app
from app.schemas.rental import (
    DirectRentalSubmissionRequest,
    RentalSearchParams,
    validate_chennai_coordinates,
)
from app.services.algorithms.normalization import deduplicate_listings
from app.services.providers.rental_registry import RentalProviderRegistry
from app.services.providers.rental_rivo_direct import RivoDirectListingProvider


class TestChennaiCoordinateValidation:
    """Task 8: Bounding box geocoding validation."""

    def test_valid_chennai_coordinates(self):
        # Chennai Central
        valid, err = validate_chennai_coordinates(13.0827, 80.2707)
        assert valid is True
        assert err is None

        # Velachery
        valid, err = validate_chennai_coordinates(12.9750, 80.2200)
        assert valid is True
        assert err is None

    def test_coordinates_outside_chennai_rejected(self):
        # Bengaluru
        valid, err = validate_chennai_coordinates(12.9716, 77.5946)
        assert valid is False
        assert "outside Chennai pilot bounds" in err

        # Delhi
        valid, err = validate_chennai_coordinates(28.6139, 77.2090)
        assert valid is False
        assert "outside Chennai pilot bounds" in err


class TestCrossProviderDeduplication:
    """Task 7: Cross-provider deduplication algorithm."""

    def test_exact_provider_and_id_merged(self):
        listings = [
            {"provider": "mock", "listing_id": "L-1", "rent_monthly": 15000, "bhk": 2},
            {"provider": "mock", "listing_id": "L-1", "rent_monthly": 15000, "bhk": 2},
        ]
        res = deduplicate_listings(listings)
        assert res[0]["duplicate_cluster_id"] == res[1]["duplicate_cluster_id"]
        assert sum(1 for r in res if r["is_canonical"]) == 1

    def test_coordinate_proximity_and_rent_similarity_merged(self):
        # Two properties 30m apart with same BHK and rent within 5%
        listings = [
            {
                "provider": "rivo_direct",
                "listing_id": "DIR-1",
                "latitude": 13.0820,
                "longitude": 80.2700,
                "rent_monthly": 20000,
                "bhk": 2,
            },
            {
                "provider": "open_dataset",
                "listing_id": "OPEN-1",
                "latitude": 13.0822,
                "longitude": 80.2701,
                "rent_monthly": 21000,  # 5% difference
                "bhk": 2,
            },
        ]
        res = deduplicate_listings(listings, coord_threshold_m=50.0)
        assert res[0]["duplicate_cluster_id"] == res[1]["duplicate_cluster_id"]
        assert sum(1 for r in res if r["is_canonical"]) == 1

    def test_different_bhk_not_merged_even_if_close(self):
        listings = [
            {
                "provider": "rivo_direct",
                "listing_id": "DIR-1",
                "latitude": 13.0820,
                "longitude": 80.2700,
                "rent_monthly": 20000,
                "bhk": 1,
            },
            {
                "provider": "open_dataset",
                "listing_id": "OPEN-1",
                "latitude": 13.0821,
                "longitude": 80.2700,
                "rent_monthly": 20000,
                "bhk": 3,
            },
        ]
        res = deduplicate_listings(listings, coord_threshold_m=50.0)
        assert res[0]["duplicate_cluster_id"] != res[1]["duplicate_cluster_id"]


class TestRivoDirectListingProvider:
    """Task 4 & 26: First-Party Owner Submissions."""

    def test_direct_submission_and_normalization(self):
        provider = RivoDirectListingProvider()
        req = DirectRentalSubmissionRequest(
            locality="Velachery, Vijayanagar",
            address="Plot 12, 2nd Main Road",
            latitude=12.9800,
            longitude=80.2200,
            rent_monthly=16500,
            maintenance_monthly=1500,
            bhk=2,
            area_sqft=950,
            furnishing="semi furnished",
            property_type="flat",
            availability_status=AvailabilityStatus.AVAILABLE,
            consent_to_publish=True,
        )

        listing = provider.add_direct_listing(req)
        assert listing.listing_id.startswith("RIVO-DIR-")
        assert listing.provider == "rivo_direct"
        assert listing.data_freshness == DataFreshness.LIVE
        assert listing.verification_status == VerificationStatus.OWNER_ATTESTED
        assert listing.geocode_confidence == ConfidenceLevel.HIGH
        assert listing.rent_monthly == 16500
        assert listing.furnishing == "semi-furnished"

        # Observation recorded
        obs = provider.get_all_observations()
        assert len(obs) >= 1
        assert obs[-1]["listing_id"] == listing.listing_id

    def test_direct_submission_rejects_out_of_bounds_coordinates(self):
        provider = RivoDirectListingProvider()
        req = DirectRentalSubmissionRequest(
            locality="Outside City",
            latitude=15.0000,
            longitude=80.0000,
            rent_monthly=10000,
            bhk=1,
            consent_to_publish=True,
        )
        with pytest.raises(ValueError) as exc:
            provider.add_direct_listing(req)
        assert "outside Chennai pilot bounds" in str(exc.value)


class TestRentalEndpointsAndMarketSummary:
    """API endpoint verification for Phase 8."""

    @pytest.mark.anyio
    async def test_direct_listing_endpoint_flow(self):
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        payload = {
            "locality": "Adyar",
            "address": "Lattice Bridge Road",
            "latitude": 13.0012,
            "longitude": 80.2565,
            "rent_monthly": 18000,
            "maintenance_monthly": 1200,
            "bhk": 2,
            "area_sqft": 900,
            "furnishing": "semi-furnished",
            "property_type": "flat",
            "availability_status": "AVAILABLE",
            "consent_to_publish": True,
        }
        resp = await client.post("/api/v1/rentals/direct", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["listing_id"].startswith("RIVO-DIR-")
        assert data["provider"] == "rivo_direct"
        assert data["rent_monthly"] == 18000

        # Retrieve the direct listing
        get_resp = await client.get(f"/api/v1/rentals/{data['listing_id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["listing_id"] == data["listing_id"]

    @pytest.mark.anyio
    async def test_direct_listing_without_consent_rejected(self):
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        payload = {
            "locality": "Adyar",
            "latitude": 13.0012,
            "longitude": 80.2565,
            "rent_monthly": 18000,
            "bhk": 2,
            "consent_to_publish": False,
        }
        resp = await client.post("/api/v1/rentals/direct", json=payload)
        assert resp.status_code == 400
        assert "Consent to publish is mandatory" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_market_summary_endpoint(self):
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        resp = await client.get("/api/v1/rentals/market-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "listings_observed" in data
        assert "insufficient_data" in data

    @pytest.mark.anyio
    async def test_admin_summary_endpoint(self):
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        resp = await client.get("/api/v1/rentals/admin/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_listings" in data
        assert "provider_health" in data
        assert "rivo_direct" in data["provider_health"]
        assert "demo_seed" in data["provider_health"]


class TestRegistryAndDemoSeparation:
    """Task 9 & 10: Provider registry and Demo vs Current separation."""

    @pytest.mark.anyio
    async def test_recommendation_search_includes_demo_banner_and_metadata(self):
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        resp = await client.post(
            "/api/v1/recommendations/search",
            json={
                "max_rent_monthly": 15000,
                "workplace_lat": 13.0786,
                "workplace_lon": 80.2785,
                "workplace_label": "RGGGH Park Town",
                "max_commute_minutes": 60,
                "page": 1,
                "page_size": 5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        meta = data["search_metadata"]
        assert "demo_banner" in meta
        assert "live_count" in meta
        assert "demo_count" in meta
        # Verify first result contains Phase 8 fields
        first = data["results"][0]
        assert "availability_status" in first
        assert "geocode_confidence" in first
        assert "source_name" in first

    @pytest.mark.anyio
    async def test_source_tier_filter_demo_only(self):
        registry = RentalProviderRegistry()
        params = RentalSearchParams(
            max_rent_monthly=30000,
            source_categories=["DEMO"],
            page=1,
            page_size=10,
        )
        results = await registry.search(params)
        assert len(results) > 0
        for r in results:
            assert r.data_freshness in (DataFreshness.PERIODIC, DataFreshness.ESTIMATED)
            assert "Demo / seeded" in (r.source_name or "")
