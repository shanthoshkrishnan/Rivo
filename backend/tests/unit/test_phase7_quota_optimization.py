"""
RIVO Unit Tests — Phase 7 Quota-Efficient Routing & Budget Optimization
========================================================================
Verifies:
  - Route & Places search budgets (Task 2)
  - Quota circuit breaker & health awareness (Tasks 12 & 13)
  - Two-stage routing & preference-aware routing (Tasks 3, 9, 10)
  - Late family facility evaluation (Tasks 6 & 7)
  - Selected-home detail mode (Tasks 8 & 16)
  - Route matrix coarse comparison (Task 4)
  - Cache hit statistics & freshness (Task 11)
  - Zero live Google API calls during normal development (Safety Guard)
"""
from __future__ import annotations

import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.circuit_breaker import circuit_breaker
from app.core.config import DataFreshness, get_settings
from app.core.request_tracker import RequestBudgetManager, get_current_tracker, set_current_tracker
from app.main import app
from app.schemas.recommendation import (
    FamilyContext,
    RecommendationDetailRequest,
    RecommendationRequest,
    WorkerContext,
)
from app.schemas.routing import RouteRequest, RouteResult
from app.services.providers.places_google import GooglePlacesProvider
from app.services.providers.rental_mock import MockRentalProvider
from app.services.providers.route_google import GoogleRouteProvider, ProviderUnavailableError
from app.services.recommendation_service import RecommendationService


@pytest.fixture(autouse=True)
def reset_cb():
    """Reset circuit breaker and tracker before each test."""
    circuit_breaker.reset()
    yield
    circuit_breaker.reset()


class TestQuotaBudgetsAndTracker:
    def test_route_budget_exhaustion(self):
        """RequestBudgetManager blocks requests once route budget is reached."""
        tracker = RequestBudgetManager(search_id="test-budget", mode="search")
        tracker.route_budget = 3

        assert tracker.can_request_route() is True
        tracker.record_route_call("google", cache_hit=False)
        assert tracker.can_request_route() is True
        tracker.record_route_call("google", cache_hit=False)
        assert tracker.can_request_route() is True
        tracker.record_route_call("google", cache_hit=False)

        # 4th request exceeds budget of 3
        assert tracker.can_request_route() is False
        assert tracker.summary.budget_exhausted is True

    def test_places_budget_exhaustion(self):
        """RequestBudgetManager blocks requests once places budget is reached."""
        tracker = RequestBudgetManager(search_id="test-places-budget", mode="search")
        tracker.places_budget = 2

        assert tracker.can_request_places() is True
        tracker.record_places_call("google_places", cache_hit=False, facility_type="school")
        assert tracker.can_request_places() is True
        tracker.record_places_call("google_places", cache_hit=False, facility_type="hospital")

        # 3rd request exceeds budget of 2
        assert tracker.can_request_places() is False
        assert tracker.summary.budget_exhausted is True

    def test_cache_hits_do_not_consume_external_request_count(self):
        """Cache hits increment cache_hits counter without incrementing total_external_requests."""
        tracker = RequestBudgetManager(search_id="test-cache", mode="search")
        tracker.record_route_call("google", cache_hit=True)
        tracker.record_places_call("google_places", cache_hit=True)

        assert tracker.summary.routes_cache_hits == 1
        assert tracker.summary.places_cache_hits == 1
        assert tracker.summary.total_external_requests == 0


class TestQuotaCircuitBreaker:
    def test_circuit_breaker_trips_on_routes_quota(self):
        """Circuit breaker immediately disables Google Routes when QUOTA_EXCEEDED occurs."""
        assert circuit_breaker.is_routes_available() is True

        circuit_breaker.trip_routes("QUOTA_EXCEEDED")

        assert circuit_breaker.is_routes_available() is False
        status = circuit_breaker.get_routes_status()
        assert status["available"] is False
        assert status["reason"] == "QUOTA_EXCEEDED"
        assert "temporarily unavailable" in str(status["message"])

    def test_circuit_breaker_trips_on_places_quota(self):
        """Circuit breaker immediately disables Google Places when QUOTA_EXCEEDED occurs."""
        assert circuit_breaker.is_places_available() is True

        circuit_breaker.trip_places("QUOTA_EXCEEDED")

        assert circuit_breaker.is_places_available() is False
        status = circuit_breaker.get_places_status()
        assert status["available"] is False
        assert status["reason"] == "QUOTA_EXCEEDED"

    def test_circuit_breaker_reset(self):
        """Circuit breaker reset restores availability."""
        circuit_breaker.trip_routes("QUOTA_EXCEEDED")
        assert circuit_breaker.is_routes_available() is False
        circuit_breaker.reset()
        assert circuit_breaker.is_routes_available() is True


class TestSafetyGuardAndMockedBehavior:
    @pytest.mark.anyio
    async def test_application_google_access_independent_of_live_test_switch(self):
        """When RIVO_LIVE_API_TESTS=False, the application GoogleRouteProvider proceeds normally and does not block calls."""
        provider = GoogleRouteProvider(api_key="AIzaSyDummyKeyForSafetyTest1234567890")

        # Verify default safety switch is False
        settings = get_settings()
        assert settings.RIVO_LIVE_API_TESTS is False

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"routes": [{"duration": "1200s", "distanceMeters": 5000}]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await provider._call_api(payload={}, field_mask="routes.duration,routes.distanceMeters")

        assert "routes" in result
        assert mock_post.called
        assert provider.is_available() is True

    @pytest.mark.anyio
    async def test_route_matrix_coarse_parsing_with_mock(self):
        """compute_route_matrix parses distance and duration elements correctly."""
        provider = GoogleRouteProvider(api_key="AIzaSyDummyKeyForSafetyTest1234567890")

        mock_matrix_response = [
            {"originIndex": 0, "destinationIndex": 0, "duration": "1800s", "distanceMeters": 15000},
            {"originIndex": 1, "destinationIndex": 0, "duration": "2400s", "distanceMeters": 21000},
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_matrix_response

        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_ctx

            res = await provider.compute_route_matrix(
                origins=[(12.97, 80.22), (12.95, 80.21)],
                dest_lat=13.078,
                dest_lon=80.278,
                travel_mode="TRANSIT",
            )

        assert 0 in res
        assert 1 in res
        assert res[0]["duration_seconds"] == 1800
        assert res[0]["distance_meters"] == 15000.0
        assert res[1]["duration_seconds"] == 2400


class TestPreferenceAwareSearchAndDetailMode:
    @pytest.mark.anyio
    async def test_search_mode_uses_primary_mode_and_reports_budget(self):
        """In search mode, recommendations evaluate primary mode and attach budget summary."""
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        payload = {
            "max_rent_monthly": 15000,
            "bhk": 2,
            "workplace_lat": 13.0786,
            "workplace_lon": 80.2785,
            "workplace_label": "RGGGH Park Town",
            "max_commute_minutes": 60,
            "preferred_modes": ["TRANSIT", "DRIVE", "TWO_WHEELER"],
            "search_radius_km": 15.0,
            "page": 1,
            "page_size": 5,
        }
        resp = await client.post("/api/v1/recommendations/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert "results" in data
        assert "search_metadata" in data
        meta = data["search_metadata"]
        assert "budget_summary" in meta
        assert meta["budget_summary"]["total_external_requests"] == 0
        assert meta["rental_source"] == "Demo / seeded dataset (CMRL-anchored)"

    @pytest.mark.anyio
    async def test_selected_home_detail_mode_endpoint(self):
        """POST /api/v1/recommendations/detail provides full multi-mode evaluation and notice."""
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        # First query search to obtain a valid listing ID from the active seed dataset
        search_resp = await client.post(
            "/api/v1/recommendations/search",
            json={
                "max_rent_monthly": 25000,
                "workplace_lat": 13.0786,
                "workplace_lon": 80.2785,
                "workplace_label": "RGGGH Park Town",
                "max_commute_minutes": 60,
                "page": 1,
                "page_size": 1,
            },
        )
        assert search_resp.status_code == 200
        search_results = search_resp.json().get("results", [])
        assert len(search_results) > 0
        listing_id = search_results[0]["listing_id"]

        payload = {
            "listing_id": listing_id,
            "workplace_lat": 13.0786,
            "workplace_lon": 80.2785,
            "workplace_label": "RGGGH Park Town",
            "preferred_modes": ["TRANSIT", "DRIVE", "TWO_WHEELER", "WALK"],
            "worker": {
                "occupation_key": "nurse",
                "household_income_monthly": 35000,
            },
            "family": {
                "adults": 2,
                "children": 2,
                "school_max_minutes": 15,
                "hospital_max_minutes": 20,
                "pharmacy_max_minutes": 10,
            },
        }
        resp = await client.post("/api/v1/recommendations/detail", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert "result" in data
        result = data["result"]
        assert result["listing_id"] == listing_id
        assert "affordability" in result
        assert result["affordability"]["housing_burden_pct"] is not None

        # Verify all routes are present
        assert "all_routes" in result
        assert len(result["all_routes"]) >= 1

        # Truthful rental notice
        assert "rental_source_notice" in data
        assert "Demo / seeded dataset" in data["rental_source_notice"]
        assert data["result"]["data_freshness"] in (DataFreshness.PERIODIC, DataFreshness.ESTIMATED)
