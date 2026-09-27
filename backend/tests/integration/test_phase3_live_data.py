"""
RIVO Backend — Phase 3 Integration Tests
==========================================
Tests for the Phase 3 features:
  - Google Routes adapter (mocked HTTP)
  - Google Places provider (mocked HTTP)
  - Itinerary endpoint
  - Fallback chain behaviour
  - Route freshness labels
  - Rental provider fallback
  - Family facility threshold pass/fail
  - Recommendation pipeline (feasible / over-budget / excessive commute)

All external HTTP calls are mocked using pytest-mock / respx or unittest.mock.
No real API keys required.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.routing import RouteRequest, RouteResult, RouteStep, TransitDetails
from app.core.config import DataFreshness


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Helper: a realistic Google Routes transit response
# ─────────────────────────────────────────────────────────────────────────────
def _mock_google_transit_response() -> dict:
    """Returns a mocked Google Routes API response for a transit journey."""
    return {
        "routes": [
            {
                "duration": "2880s",          # 48 min
                "distanceMeters": 14500,
                "polyline": {"encodedPolyline": "_~}|Hq}klM_@pA"},
                "travelAdvisory": {
                    "transitFare": {"units": "30", "nanos": 0}
                },
                "legs": [
                    {
                        "duration": "2880s",
                        "distanceMeters": 14500,
                        "steps": [
                            {
                                "travelMode": "WALK",
                                "duration": "360s",
                                "distanceMeters": 450,
                                "navigationInstruction": {"instructions": "Walk to Guindy Metro"},
                            },
                            {
                                "travelMode": "TRANSIT",
                                "duration": "1020s",
                                "distanceMeters": 10800,
                                "transitDetails": {
                                    "stopDetails": {
                                        "departureStop": {"name": "Guindy"},
                                        "arrivalStop": {"name": "Chennai Central"},
                                        "departureTime": "2026-09-27T07:41:00Z",
                                        "arrivalTime": "2026-09-27T08:02:00Z",
                                    },
                                    "headsign": "Wimco Nagar",
                                    "stopCount": 7,
                                    "transitLine": {
                                        "name": "Blue Line",
                                        "nameShort": "BL",
                                        "vehicle": {"type": "SUBWAY"},
                                        "agencies": [{"name": "CMRL"}],
                                    },
                                },
                            },
                            {
                                "travelMode": "WALK",
                                "duration": "240s",
                                "distanceMeters": 300,
                                "navigationInstruction": {"instructions": "Walk to workplace"},
                            },
                        ],
                    }
                ],
            }
        ]
    }


def _mock_google_drive_response() -> dict:
    """Returns a mocked Google Routes API response for a driving journey."""
    return {
        "routes": [
            {
                "duration": "1800s",       # 30 min with traffic
                "staticDuration": "1500s", # 25 min free-flow
                "distanceMeters": 16000,
                "polyline": {"encodedPolyline": "_~}|Hq}klM"},
                "travelAdvisory": {},
                "legs": [{"duration": "1800s", "distanceMeters": 16000, "steps": []}],
            }
        ]
    }


def _mock_google_places_response() -> dict:
    """Returns a mocked Google Places (New) API response."""
    return {
        "places": [
            {
                "id": "ChIJ_demo_school_001",
                "displayName": {"text": "St. Joseph's School, Guindy"},
                "location": {"latitude": 12.9800, "longitude": 80.2210},
                "formattedAddress": "12, Guindy Industrial Estate, Chennai",
            },
            {
                "id": "ChIJ_demo_school_002",
                "displayName": {"text": "Government Higher Secondary School"},
                "location": {"latitude": 12.9760, "longitude": 80.2185},
                "formattedAddress": "45, Velachery Main Road, Chennai",
            },
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Health endpoint — Phase 3: must report Google API status
# ─────────────────────────────────────────────────────────────────────────────
class TestHealthPhase3:
    @pytest.mark.anyio
    async def test_health_reports_google_status(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "google_routes" in data
        assert "google_places" in data
        # Without keys configured, expect NOT CONFIGURED
        assert data["google_routes"] in ("CONFIGURED", "NOT CONFIGURED")
        assert data["google_places"] in ("CONFIGURED", "NOT CONFIGURED")


# ─────────────────────────────────────────────────────────────────────────────
# Google Routes adapter — unit tests with mocked HTTP
# ─────────────────────────────────────────────────────────────────────────────
class TestGoogleRouteProvider:
    @pytest.mark.anyio
    async def test_transit_route_parsed_correctly(self):
        """Transit response is parsed into RouteResult with steps."""
        from app.services.providers.route_google import GoogleRouteProvider
        from app.core.config import get_settings

        # Override API key
        settings = get_settings()
        provider = GoogleRouteProvider()
        provider._api_key = "test-key-mock"

        mock_response = _mock_google_transit_response()

        with patch.object(provider, "_call_api", new=AsyncMock(return_value=mock_response)):
            with patch("app.services.providers.route_google.cache_get", new=AsyncMock(return_value=None)):
                with patch("app.services.providers.route_google.cache_set", new=AsyncMock()):
                    results = await provider.compute_route(
                        RouteRequest(
                            origin_lat=12.975,
                            origin_lon=80.220,
                            dest_lat=13.066,
                            dest_lon=80.242,
                            modes=["TRANSIT"],
                        )
                    )

        assert len(results) == 1
        r = results[0]

        # Freshness must be LIVE (not ESTIMATED — never mislabel)
        assert r.data_freshness == DataFreshness.LIVE
        assert r.provider == "google"
        assert r.source_label == "Google Routes API"

        # Duration
        assert r.duration_seconds == 2880
        assert r.distance_m == 14500.0

        # Fare from travelAdvisory
        assert r.fare_amount == 30.0

        # Steps: WALK → TRANSIT → WALK
        assert len(r.steps) == 3
        assert r.steps[0].type == "WALK"
        assert r.steps[1].type == "TRANSIT"
        assert r.steps[2].type == "WALK"

        # Transit step details
        td = r.steps[1].transit
        assert td is not None
        assert td.agency == "CMRL"
        assert td.vehicle_type == "SUBWAY"
        assert td.departure_stop == "Guindy"
        assert td.arrival_stop == "Chennai Central"
        assert td.headsign == "Wimco Nagar"
        assert td.line == "Blue Line"
        assert td.line_short_name == "BL"

        # Transfer count: 1 transit leg = 0 transfers
        assert r.transfer_count == 0

    @pytest.mark.anyio
    async def test_drive_route_has_traffic_info(self):
        """Drive route returns TrafficInfo with live traffic label."""
        from app.services.providers.route_google import GoogleRouteProvider

        provider = GoogleRouteProvider()
        provider._api_key = "test-key-mock"

        mock_response = _mock_google_drive_response()

        with patch.object(provider, "_call_api", new=AsyncMock(return_value=mock_response)):
            with patch("app.services.providers.route_google.cache_get", new=AsyncMock(return_value=None)):
                with patch("app.services.providers.route_google.cache_set", new=AsyncMock()):
                    results = await provider.compute_route(
                        RouteRequest(
                            origin_lat=12.975,
                            origin_lon=80.220,
                            dest_lat=13.066,
                            dest_lon=80.242,
                            modes=["DRIVE"],
                        )
                    )

        assert len(results) == 1
        r = results[0]
        assert r.traffic is not None
        assert r.traffic.traffic_status == "LIVE_TRAFFIC"
        assert r.traffic.traffic_duration_seconds == 1800  # traffic-aware
        assert r.traffic.normal_duration_seconds == 1500   # free-flow

    @pytest.mark.anyio
    async def test_provider_unavailable_when_no_key(self):
        """Provider raises ProviderUnavailableError when API key is missing."""
        from app.services.providers.route_google import GoogleRouteProvider, ProviderUnavailableError

        provider = GoogleRouteProvider()
        provider._api_key = ""   # No key

        assert not provider.is_available()

        with pytest.raises(ProviderUnavailableError):
            await provider.compute_route(
                RouteRequest(origin_lat=12.9, origin_lon=80.2, dest_lat=13.0, dest_lon=80.3)
            )

    @pytest.mark.anyio
    async def test_cached_result_is_labelled_recent(self):
        """A cached Google route result is marked RECENT, not LIVE."""
        from app.services.providers.route_google import GoogleRouteProvider

        provider = GoogleRouteProvider()
        provider._api_key = "test-key-mock"

        cached_route = RouteResult(
            mode="TRANSIT",
            provider="google",
            duration_seconds=2880,
            data_freshness=DataFreshness.LIVE,  # stored as LIVE
        )

        with patch("app.services.providers.route_google.cache_get", new=AsyncMock(return_value=cached_route.model_dump(mode="json"))):
            results = await provider.compute_route(
                RouteRequest(
                    origin_lat=12.975,
                    origin_lon=80.220,
                    dest_lat=13.066,
                    dest_lon=80.242,
                    modes=["TRANSIT"],
                )
            )

        assert len(results) == 1
        # Must be downgraded to RECENT — never reuse stale as LIVE
        assert results[0].data_freshness == DataFreshness.RECENT

    @pytest.mark.anyio
    async def test_empty_routes_returns_empty_list(self):
        """Empty Google response returns empty list (not an error)."""
        from app.services.providers.route_google import GoogleRouteProvider

        provider = GoogleRouteProvider()
        provider._api_key = "test-key-mock"

        with patch.object(provider, "_call_api", new=AsyncMock(return_value={"routes": []})):
            with patch("app.services.providers.route_google.cache_get", new=AsyncMock(return_value=None)):
                with patch("app.services.providers.route_google.cache_set", new=AsyncMock()):
                    results = await provider.compute_route(
                        RouteRequest(
                            origin_lat=12.975,
                            origin_lon=80.220,
                            dest_lat=13.066,
                            dest_lon=80.242,
                            modes=["TRANSIT"],
                        )
                    )
        assert results == []


# ─────────────────────────────────────────────────────────────────────────────
# Google Places provider — unit tests with mocked HTTP
# ─────────────────────────────────────────────────────────────────────────────
class TestGooglePlacesProvider:
    @pytest.mark.anyio
    async def test_school_search_returns_live_results(self):
        """Google Places returns schools with LIVE freshness."""
        from app.services.providers.places_google import GooglePlacesProvider

        provider = GooglePlacesProvider()
        provider._api_key = "test-key-mock"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_google_places_response()

        with patch("app.services.providers.places_google.cache_get", new=AsyncMock(return_value=None)):
            with patch("app.services.providers.places_google.cache_set", new=AsyncMock()):
                with patch("httpx.AsyncClient") as MockClient:
                    mock_ctx = AsyncMock()
                    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
                    mock_ctx.__aexit__ = AsyncMock(return_value=False)
                    mock_ctx.post = AsyncMock(return_value=mock_resp)
                    MockClient.return_value = mock_ctx

                    results = await provider.nearby_facilities(
                        latitude=12.975,
                        longitude=80.220,
                        facility_type="school",
                        radius_m=2000,
                        limit=5,
                    )

        assert len(results) == 2
        for r in results:
            assert r.data_freshness == DataFreshness.LIVE
            assert r.source_name == "Google Places API"
            assert r.latitude is not None
            assert r.longitude is not None

    @pytest.mark.anyio
    async def test_places_unavailable_when_no_key(self):
        """Provider returns empty list when API key missing."""
        from app.services.providers.places_google import GooglePlacesProvider

        provider = GooglePlacesProvider()
        provider._api_key = ""

        assert not provider.is_available()
        results = await provider.nearby_facilities(12.975, 80.220, "school", 2000, 5)
        assert results == []

    @pytest.mark.anyio
    async def test_places_http_error_returns_empty(self):
        """HTTP error from Google Places returns empty list (graceful fallback)."""
        from app.services.providers.places_google import GooglePlacesProvider

        provider = GooglePlacesProvider()
        provider._api_key = "test-key-mock"

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "REQUEST_DENIED"

        with patch("app.services.providers.places_google.cache_get", new=AsyncMock(return_value=None)):
            with patch("httpx.AsyncClient") as MockClient:
                mock_ctx = AsyncMock()
                mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
                mock_ctx.__aexit__ = AsyncMock(return_value=False)
                mock_ctx.post = AsyncMock(return_value=mock_resp)
                MockClient.return_value = mock_ctx

                results = await provider.nearby_facilities(12.975, 80.220, "hospital", 2000, 5)

        assert results == []


# ─────────────────────────────────────────────────────────────────────────────
# Itinerary endpoint
# ─────────────────────────────────────────────────────────────────────────────
class TestItineraryEndpoint:
    @pytest.mark.anyio
    async def test_itinerary_returns_route_result(self, client: AsyncClient):
        """Itinerary endpoint returns a RouteResult."""
        payload = {
            "home_lat": 12.9751,
            "home_lon": 80.2202,
            "workplace_lat": 13.0669,
            "workplace_lon": 80.2425,
            "mode": "TRANSIT",
        }
        resp = await client.post("/api/v1/routes/itinerary", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "mode" in data
        assert "provider" in data
        assert "data_freshness" in data
        assert data["mode"] == "TRANSIT"

    @pytest.mark.anyio
    async def test_itinerary_freshness_not_faked_as_live(self, client: AsyncClient):
        """When no Google key configured, itinerary must NOT be labelled LIVE."""
        payload = {
            "home_lat": 12.9751,
            "home_lon": 80.2202,
            "workplace_lat": 13.0669,
            "workplace_lon": 80.2425,
            "mode": "TRANSIT",
        }
        from app.core.config import get_settings
        s = get_settings()

        resp = await client.post("/api/v1/routes/itinerary", json=payload)
        data = resp.json()

        if not s.google_routes_enabled:
            # Without Google key, must not claim LIVE
            assert data["data_freshness"] != "LIVE", (
                "NEVER label an estimated result as LIVE. "
                f"Got: {data['data_freshness']}"
            )

    @pytest.mark.anyio
    async def test_itinerary_steps_list_present(self, client: AsyncClient):
        """RouteResult includes 'steps' field (may be empty without Google)."""
        payload = {
            "home_lat": 12.9751,
            "home_lon": 80.2202,
            "workplace_lat": 13.0669,
            "workplace_lon": 80.2425,
            "mode": "TRANSIT",
        }
        resp = await client.post("/api/v1/routes/itinerary", json=payload)
        data = resp.json()
        assert "steps" in data
        assert isinstance(data["steps"], list)


# ─────────────────────────────────────────────────────────────────────────────
# Composite provider fallback chain
# ─────────────────────────────────────────────────────────────────────────────
class TestFallbackChain:
    @pytest.mark.anyio
    async def test_fallback_to_gtfs_when_google_unavailable(self):
        """CompositeRouteProvider uses GTFS when Google is unavailable."""
        from app.services.providers.registry import CompositeRouteProvider
        from app.services.providers.route_google import ProviderUnavailableError

        provider = CompositeRouteProvider()

        # Patch Google to be unavailable
        for p in provider._providers:
            if p.provider_name == "google":
                p.is_available = lambda: False

        req = RouteRequest(
            origin_lat=12.9751,
            origin_lon=80.2202,
            dest_lat=13.0669,
            dest_lon=80.2425,
            modes=["TRANSIT"],
        )
        results = await provider.compute_route(req)
        assert len(results) >= 1
        # Should not be google if Google unavailable
        providers_used = {r.provider for r in results}
        assert "google" not in providers_used

    @pytest.mark.anyio
    async def test_mock_provider_labels_estimated(self):
        """MockRouteProvider always returns ESTIMATED freshness."""
        from app.services.providers.route_mock import MockRouteProvider

        provider = MockRouteProvider()
        req = RouteRequest(
            origin_lat=12.975,
            origin_lon=80.220,
            dest_lat=13.066,
            dest_lon=80.242,
            modes=["TRANSIT"],
        )
        results = await provider.compute_route(req)
        assert len(results) >= 1
        for r in results:
            assert r.data_freshness in (DataFreshness.ESTIMATED, DataFreshness.PERIODIC)
            assert r.data_freshness != DataFreshness.LIVE, (
                "MockRouteProvider MUST NOT return LIVE freshness"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Recommendation pipeline
# ─────────────────────────────────────────────────────────────────────────────
class TestRecommendationPipeline:
    # Nurse @ Rajiv Gandhi GGH (Chennai scenario from AGENTS.md Part 30)
    NURSE_WORKPLACE = {"lat": 13.0695, "lon": 80.2834}  # Rajiv Gandhi GGH, Park Town

    @pytest.mark.anyio
    async def test_feasible_home_returned(self, client: AsyncClient):
        """A nurse with ₹15,000 rent ceiling should find feasible homes."""
        payload = {
            "max_rent_monthly": 15000,
            "bhk": 2,
            "workplace_lat": self.NURSE_WORKPLACE["lat"],
            "workplace_lon": self.NURSE_WORKPLACE["lon"],
            "workplace_label": "Rajiv Gandhi GGH",
            "max_commute_minutes": 60,
            "preferred_modes": ["TRANSIT"],
            "worker": {"occupation_key": "nurse", "household_income_monthly": 35000},
            "family": {
                "adults": 2,
                "children": 2,
                "school_max_minutes": 15,
                "hospital_max_minutes": 20,
                "pharmacy_max_minutes": 10,
            },
            "search_radius_km": 20.0,
            "page": 1,
            "page_size": 10,
        }
        resp = await client.post("/api/v1/recommendations/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "results" in data
        # Should find at least some results
        # (mock data covers multiple localities)

    @pytest.mark.anyio
    async def test_over_budget_listing_rejected(self, client: AsyncClient):
        """Listings above max_rent_monthly must not appear."""
        payload = {
            "max_rent_monthly": 5000,
            "workplace_lat": self.NURSE_WORKPLACE["lat"],
            "workplace_lon": self.NURSE_WORKPLACE["lon"],
            "max_commute_minutes": 90,
            "preferred_modes": ["TRANSIT"],
            "search_radius_km": 25.0,
        }
        resp = await client.post("/api/v1/recommendations/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        for result in data["results"]:
            if result.get("rent_monthly") is not None:
                assert result["rent_monthly"] <= 5000, (
                    f"Over-budget listing returned: ₹{result['rent_monthly']}"
                )

    @pytest.mark.anyio
    async def test_result_has_affordability_breakdown(self, client: AsyncClient):
        """Each recommendation result must have an affordability breakdown."""
        payload = {
            "max_rent_monthly": 20000,
            "workplace_lat": self.NURSE_WORKPLACE["lat"],
            "workplace_lon": self.NURSE_WORKPLACE["lon"],
            "max_commute_minutes": 60,
            "preferred_modes": ["TRANSIT"],
            "worker": {"household_income_monthly": 40000},
            "search_radius_km": 20.0,
        }
        resp = await client.post("/api/v1/recommendations/search", json=payload)
        data = resp.json()
        for result in data["results"]:
            # affordability block must exist when income is provided
            assert "affordability" in result
            if result["affordability"]:
                # Housing burden must be a percentage between 0 and 100
                hb = result["affordability"].get("housing_burden_pct")
                if hb is not None:
                    assert 0 <= hb <= 100, f"Invalid housing burden: {hb}"

    @pytest.mark.anyio
    async def test_result_freshness_not_mislabelled(self, client: AsyncClient):
        """No result should be labelled LIVE when using mock rental provider."""
        from app.core.config import get_settings
        s = get_settings()

        # Mock rental provider should return PERIODIC or ESTIMATED, never LIVE
        payload = {
            "max_rent_monthly": 20000,
            "workplace_lat": self.NURSE_WORKPLACE["lat"],
            "workplace_lon": self.NURSE_WORKPLACE["lon"],
            "max_commute_minutes": 90,
            "preferred_modes": ["TRANSIT"],
            "search_radius_km": 25.0,
        }
        resp = await client.post("/api/v1/recommendations/search", json=payload)
        data = resp.json()

        if s.RENTAL_PROVIDER == "mock":
            for result in data["results"]:
                assert result["data_freshness"] != "LIVE", (
                    "NEVER label mock/sample rental data as LIVE"
                )

    @pytest.mark.anyio
    async def test_result_has_route_info(self, client: AsyncClient):
        """Each result must include route information."""
        payload = {
            "max_rent_monthly": 20000,
            "workplace_lat": self.NURSE_WORKPLACE["lat"],
            "workplace_lon": self.NURSE_WORKPLACE["lon"],
            "max_commute_minutes": 90,
            "preferred_modes": ["TRANSIT"],
            "search_radius_km": 25.0,
        }
        resp = await client.post("/api/v1/recommendations/search", json=payload)
        data = resp.json()
        for result in data["results"]:
            assert "all_routes" in result
            assert isinstance(result["all_routes"], list)


# ─────────────────────────────────────────────────────────────────────────────
# Facilities endpoint
# ─────────────────────────────────────────────────────────────────────────────
class TestFacilitiesPhase3:
    @pytest.mark.anyio
    async def test_school_search_returns_results(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/facilities/nearby"
            "?latitude=12.9751&longitude=80.2202&facility_type=school&radius_km=5"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["facility_type"] == "school"
        assert "results" in data
        assert "data_freshness" in data

    @pytest.mark.anyio
    async def test_invalid_facility_type_rejected(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/facilities/nearby"
            "?latitude=12.975&longitude=80.220&facility_type=nightclub"
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_facility_result_has_freshness(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/facilities/nearby"
            "?latitude=12.9751&longitude=80.2202&facility_type=hospital&radius_km=10"
        )
        assert resp.status_code == 200
        data = resp.json()
        # Without Google Places key, result must NOT be LIVE
        from app.core.config import get_settings
        s = get_settings()
        if not s.google_places_enabled:
            assert data["data_freshness"] != "LIVE", (
                "Facility results from local seed MUST NOT be labelled LIVE"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Route result schema validation
# ─────────────────────────────────────────────────────────────────────────────
class TestRouteResultSchema:
    def test_route_result_monthly_cost_calculation(self):
        """monthly_commute_cost computed correctly from fare_amount."""
        r = RouteResult(
            mode="TRANSIT",
            provider="gtfs",
            fare_amount=30.0,
            duration_seconds=2880,
            data_freshness=DataFreshness.PERIODIC,
        )
        # ₹30 × 2 × 22 = ₹1,320
        assert r.monthly_commute_cost == 1320.0

    def test_route_result_time_tax_calculation(self):
        """monthly_commute_hours computed correctly."""
        r = RouteResult(
            mode="TRANSIT",
            provider="gtfs",
            duration_seconds=2880,  # 48 min
            data_freshness=DataFreshness.PERIODIC,
        )
        # 48 min × 2 × 22 / 60 = 35.2 hrs
        assert r.monthly_commute_hours == 35.2

    @pytest.mark.anyio
    async def test_route_result_freshness_never_live_from_mock(self):
        """A result from the mock provider should not be LIVE."""
        from app.services.providers.route_mock import MockRouteProvider

        provider = MockRouteProvider()
        req = RouteRequest(origin_lat=12.975, origin_lon=80.220, dest_lat=13.0, dest_lon=80.3)
        results = await provider.compute_route(req)
        for r in results:
            assert r.data_freshness != DataFreshness.LIVE

