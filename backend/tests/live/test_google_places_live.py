"""
RIVO Live Test — Google Places API Live Requests (Task 21)
==========================================================
Performs ACTUAL HTTP requests against Google Places (New) Nearby Search.
SKIPS automatically when GOOGLE_PLACES_API_KEY is not configured in .env.
"""
from __future__ import annotations

import pytest

from app.core.config import DataFreshness, get_settings
from app.services.providers.places_google import GooglePlacesProvider

settings = get_settings()
PLACES_CONFIGURED = bool(settings.google_places_enabled and settings.RIVO_LIVE_API_TESTS)

VELACHERY_LAT = 12.9751
VELACHERY_LON = 80.2202


@pytest.mark.skipif(
    not PLACES_CONFIGURED,
    reason="Live API tests disabled (RIVO_LIVE_API_TESTS=false) or GOOGLE_PLACES_API_KEY not configured",
)
class TestGooglePlacesLive:
    """Live Google Places Nearby Search requests — only executed with valid credentials."""

    @pytest.mark.anyio
    async def test_live_school_search(self):
        """Search real schools near Velachery candidate home."""
        provider = GooglePlacesProvider()
        assert provider.is_available()

        results = await provider.nearby_facilities(
            latitude=VELACHERY_LAT,
            longitude=VELACHERY_LON,
            facility_type="school",
            radius_m=3000,
            limit=3,
        )
        assert len(results) >= 1
        fac = results[0]
        assert fac.name is not None and len(fac.name) > 0
        assert fac.latitude is not None
        assert fac.longitude is not None
        assert fac.data_freshness in (DataFreshness.LIVE, DataFreshness.RECENT)
        assert "Google Places" in fac.source_name

    @pytest.mark.anyio
    async def test_live_hospital_search(self):
        """Search real hospitals near Velachery candidate home."""
        provider = GooglePlacesProvider()
        assert provider.is_available()

        results = await provider.nearby_facilities(
            latitude=VELACHERY_LAT,
            longitude=VELACHERY_LON,
            facility_type="hospital",
            radius_m=3000,
            limit=3,
        )
        assert len(results) >= 1
        fac = results[0]
        assert fac.name is not None
        assert fac.data_freshness in (DataFreshness.LIVE, DataFreshness.RECENT)

    @pytest.mark.anyio
    async def test_live_pharmacy_search(self):
        """Search real pharmacies near Velachery candidate home."""
        provider = GooglePlacesProvider()
        assert provider.is_available()

        results = await provider.nearby_facilities(
            latitude=VELACHERY_LAT,
            longitude=VELACHERY_LON,
            facility_type="pharmacy",
            radius_m=3000,
            limit=3,
        )
        assert len(results) >= 1
        fac = results[0]
        assert fac.name is not None
        assert fac.data_freshness in (DataFreshness.LIVE, DataFreshness.RECENT)
