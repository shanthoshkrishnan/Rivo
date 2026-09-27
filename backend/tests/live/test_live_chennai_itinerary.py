"""
RIVO Live Test — End-to-End Chennai Itinerary & Recommendation (Task 21)
=======================================================================
Performs end-to-end itinerary generation and recommendation search
with live external Google Route & Places endpoints when configured.
SKIPS automatically when credentials are not configured in .env.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import DataFreshness, get_settings
from app.main import app

settings = get_settings()
LIVE_CONFIGURED = bool(
    settings.google_routes_enabled
    and settings.google_places_enabled
    and settings.RIVO_LIVE_API_TESTS
)

VELACHERY_LAT = 12.9751
VELACHERY_LON = 80.2202
RGGGH_LAT = 13.0786
RGGGH_LON = 80.2785


@pytest.fixture
async def live_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as c:
        yield c


@pytest.mark.skipif(
    not LIVE_CONFIGURED,
    reason="Live API tests disabled (RIVO_LIVE_API_TESTS=false) or Google API keys not configured",
)
class TestLiveChennaiItinerary:
    """Full end-to-end verification of itinerary and recommendation with live APIs."""

    @pytest.mark.anyio
    async def test_live_itinerary_endpoint(self, live_client: AsyncClient):
        """POST /api/v1/routes/itinerary returns live Google transit itinerary."""
        payload = {
            "home_lat": VELACHERY_LAT,
            "home_lon": VELACHERY_LON,
            "workplace_lat": RGGGH_LAT,
            "workplace_lon": RGGGH_LON,
            "mode": "TRANSIT",
        }
        resp = await live_client.post("/api/v1/routes/itinerary", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["provider"] == "google"
        assert data["data_freshness"] in ("LIVE", "RECENT")
        assert data["duration_seconds"] > 0
        assert data["distance_meters"] > 0
        assert "steps" in data
        assert len(data["steps"]) > 0

    @pytest.mark.anyio
    async def test_live_recommendation_search_with_family(self, live_client: AsyncClient):
        """POST /api/v1/recommendations/search returns live-evaluated home candidate."""
        payload = {
            "max_rent_monthly": 20000,
            "bhk": 2,
            "workplace_lat": RGGGH_LAT,
            "workplace_lon": RGGGH_LON,
            "workplace_label": "Rajiv Gandhi Government General Hospital",
            "max_commute_minutes": 60,
            "preferred_modes": ["TRANSIT"],
            "worker": {
                "occupation_key": "nurse",
                "household_income_monthly": 38000,
            },
            "family": {
                "adults": 2,
                "children": 2,
                "school_max_minutes": 15,
                "hospital_max_minutes": 20,
                "pharmacy_max_minutes": 10,
            },
            "search_radius_km": 20.0,
            "page": 1,
            "page_size": 5,
        }
        resp = await live_client.post("/api/v1/recommendations/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] > 0
        assert len(data["results"]) > 0

        first_res = data["results"][0]
        assert first_res["best_route"] is not None
        assert first_res["affordability"] is not None
        assert first_res["school_access"] is not None
        assert "data_quality_score" in first_res["score_components"]
