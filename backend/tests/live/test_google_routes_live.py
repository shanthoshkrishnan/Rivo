"""
RIVO Live Test — Google Routes API Live Requests (Task 21)
==========================================================
Performs ACTUAL HTTP requests against Google Routes API.
SKIPS automatically when GOOGLE_ROUTES_API_KEY is not configured in .env.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.core.config import DataFreshness, get_settings
from app.schemas.routing import RouteRequest
from app.services.providers.route_google import GoogleRouteProvider

settings = get_settings()
ROUTES_CONFIGURED = bool(settings.google_routes_enabled and settings.RIVO_LIVE_API_TESTS)

# Real Chennai coordinates
# Home: Velachery
VELACHERY_LAT = 12.9751
VELACHERY_LON = 80.2202
# Workplace: Rajiv Gandhi Govt General Hospital (Park Town)
RGGGH_LAT = 13.0786
RGGGH_LON = 80.2785


@pytest.mark.skipif(
    not ROUTES_CONFIGURED,
    reason="Live API tests disabled (RIVO_LIVE_API_TESTS=false) or GOOGLE_ROUTES_API_KEY not configured",
)
class TestGoogleRoutesLive:
    """Live Google Routes API requests — only executed with valid credentials."""

    @pytest.mark.anyio
    async def test_live_transit_route(self):
        """Perform real TRANSIT route request from Velachery to RGGGH."""
        provider = GoogleRouteProvider()
        assert provider.is_available()

        # Future departure time for IST morning commute
        ist_offset = timedelta(hours=5, minutes=30)
        now_utc = datetime.now(timezone.utc)
        dep_ist = (now_utc + ist_offset).replace(hour=8, minute=30, second=0, microsecond=0)
        if dep_ist <= now_utc + ist_offset:
            dep_ist += timedelta(days=1)
        dep_utc = dep_ist - ist_offset

        req = RouteRequest(
            origin_lat=VELACHERY_LAT,
            origin_lon=VELACHERY_LON,
            dest_lat=RGGGH_LAT,
            dest_lon=RGGGH_LON,
            modes=["TRANSIT"],
            departure_time=dep_utc,
        )
        results = await provider.compute_route(req)

        assert len(results) >= 1
        route = results[0]
        assert route.provider == "google"
        assert route.mode == "TRANSIT"
        assert route.data_freshness in (DataFreshness.LIVE, DataFreshness.RECENT)
        assert route.duration_seconds is not None and route.duration_seconds > 0
        assert route.distance_meters is not None and route.distance_meters > 0
        assert route.polyline is not None and len(route.polyline) > 0
        assert isinstance(route.steps, list)

    @pytest.mark.anyio
    async def test_live_drive_route(self):
        """Perform real DRIVE request with traffic awareness from Velachery to RGGGH."""
        provider = GoogleRouteProvider()
        assert provider.is_available()

        req = RouteRequest(
            origin_lat=VELACHERY_LAT,
            origin_lon=VELACHERY_LON,
            dest_lat=RGGGH_LAT,
            dest_lon=RGGGH_LON,
            modes=["DRIVE"],
        )
        results = await provider.compute_route(req)

        assert len(results) >= 1
        route = results[0]
        assert route.provider == "google"
        assert route.mode == "DRIVE"
        assert route.duration_seconds is not None and route.duration_seconds > 0
        assert route.distance_meters is not None and route.distance_meters > 0
        assert route.polyline is not None

    @pytest.mark.anyio
    async def test_live_walk_route(self):
        """Perform real WALK request from Velachery home to nearest station."""
        provider = GoogleRouteProvider()
        assert provider.is_available()

        # Velachery home to Velachery MRTS (~500m)
        req = RouteRequest(
            origin_lat=VELACHERY_LAT,
            origin_lon=VELACHERY_LON,
            dest_lat=12.9785,
            dest_lon=80.2220,
            modes=["WALK"],
        )
        results = await provider.compute_route(req)

        assert len(results) >= 1
        route = results[0]
        assert route.provider == "google"
        assert route.mode == "WALK"
        assert route.duration_seconds is not None and route.duration_seconds > 0
