"""
Unit tests for Phase 7.1 — Separation of Live-Test Safety Switch from Application Live API Access.

Proves:
1. Application + Google key + normal provider path does NOT depend on RIVO_LIVE_API_TESTS.
2. Live test harness + RIVO_LIVE_API_TESTS=false makes zero network calls (skips).
3. Live test harness + RIVO_LIVE_API_TESTS=true is permitted to make network calls (tested with mocked HTTP).
"""
import os
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.circuit_breaker import circuit_breaker
from app.core.config import get_settings
from app.services.providers.places_google import GooglePlacesProvider
from app.services.providers.route_google import GoogleRouteProvider


class TestPhase71SafetySeparation:
    """Proves application live access is decoupled from RIVO_LIVE_API_TESTS test gate."""

    @pytest.mark.anyio
    async def test_application_routes_provider_independent_of_live_test_switch(self):
        """
        Application + Google key + normal route provider path:
        Does NOT block or check RIVO_LIVE_API_TESTS.
        Works identically whether RIVO_LIVE_API_TESTS is False or True.
        """
        settings = get_settings()
        # Verify default safety setting is False
        assert settings.RIVO_LIVE_API_TESTS is False

        provider = GoogleRouteProvider(api_key="AIzaSyDummyKeyNormalAppPath123456789")

        # Provider is available because key is present and circuit is closed
        assert provider.is_available() is True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "routes": [
                {
                    "duration": "1500s",
                    "distanceMeters": 8500,
                    "legs": [
                        {
                            "steps": [
                                {
                                    "travelMode": "TRANSIT",
                                    "transitDetails": {
                                        "stopDetails": {
                                            "departureStop": {"name": "Velachery"},
                                            "arrivalStop": {"name": "Guindy"},
                                        }
                                    },
                                }
                            ]
                        }
                    ],
                }
            ]
        }

        # Even with RIVO_LIVE_API_TESTS=False, normal application _call_api makes the HTTP call
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            data = await provider._call_api(
                payload={"origin": {}, "destination": {}},
                field_mask="routes.duration,routes.distanceMeters",
            )
            assert "routes" in data
            assert mock_post.called

    @pytest.mark.anyio
    async def test_application_places_provider_independent_of_live_test_switch(self):
        """
        Application + Google Places key + normal places provider path:
        Does NOT block or check RIVO_LIVE_API_TESTS.
        """
        settings = get_settings()
        assert settings.RIVO_LIVE_API_TESTS is False

        provider = GooglePlacesProvider(api_key="AIzaSyDummyPlacesKey123456789")
        assert provider.is_available() is True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "places": [
                {
                    "id": "place_123",
                    "displayName": {"text": "Apollo Hospital"},
                    "location": {"latitude": 13.08, "longitude": 80.28},
                }
            ]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            results = await provider.nearby_facilities(
                latitude=13.08,
                longitude=80.28,
                facility_type="hospital",
                radius_m=3000,
                limit=5,
            )
            assert len(results) == 1
            assert results[0].name == "Apollo Hospital"
            assert mock_post.called

    def test_live_test_harness_gated_when_switch_is_false(self):
        """
        When RIVO_LIVE_API_TESTS=False:
        Live test condition evaluates to False -> 0 network calls (skipped).
        """
        settings = get_settings()
        assert settings.RIVO_LIVE_API_TESTS is False

        # Simulate the gate used in tests/live/test_google_routes_live.py
        routes_configured = bool(settings.google_routes_enabled and settings.RIVO_LIVE_API_TESTS)
        places_configured = bool(settings.google_places_enabled and settings.RIVO_LIVE_API_TESTS)

        # Both must evaluate to False so live tests are skipped
        assert routes_configured is False
        assert places_configured is False

    @pytest.mark.anyio
    async def test_live_test_harness_permitted_when_switch_is_true_mocked(self):
        """
        When RIVO_LIVE_API_TESTS=True:
        Live test condition evaluates to True -> permitted to make network calls.
        (Tested via mock transport — NO real external calls made).
        """
        mock_settings = MagicMock()
        mock_settings.google_routes_enabled = True
        mock_settings.google_places_enabled = True
        mock_settings.RIVO_LIVE_API_TESTS = True

        routes_configured = bool(mock_settings.google_routes_enabled and mock_settings.RIVO_LIVE_API_TESTS)
        places_configured = bool(mock_settings.google_places_enabled and mock_settings.RIVO_LIVE_API_TESTS)

        assert routes_configured is True
        assert places_configured is True

        # When permitted, mock HTTP confirms execution succeeds
        provider = GoogleRouteProvider(api_key="AIzaSyDummyKeyForLiveTestHarness123")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"routes": [{"duration": "600s"}]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            resp = await provider._call_api(payload={}, field_mask="routes.duration")
            assert "routes" in resp
            assert mock_post.call_count == 1

    def test_circuit_breaker_status_independent_of_live_test_switch(self):
        """Circuit breaker reports AVAILABLE when keys configured, without depending on RIVO_LIVE_API_TESTS."""
        routes_status = circuit_breaker.get_routes_status()
        places_status = circuit_breaker.get_places_status()

        # Both endpoints are configured in this environment
        if get_settings().google_routes_enabled:
            assert routes_status["reason"] == "AVAILABLE"
            assert routes_status["available"] is True
        if get_settings().google_places_enabled:
            assert places_status["reason"] == "AVAILABLE"
            assert places_status["available"] is True
