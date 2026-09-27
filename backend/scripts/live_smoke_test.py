#!/usr/bin/env python
"""
RIVO — Live Smoke Test Script (Task 22)
=======================================
Performs ACTUAL HTTP calls against live Google APIs when credentials
are configured in backend/.env:
  1. Google Routes Transit request
  2. Google Routes Driving request
  3. Google Routes Walking request
  4. Google Places School search
  5. Google Places Hospital search
  6. Google Places Pharmacy search
  7. One complete selected-home door-to-door itinerary

Rules:
  - NEVER mark PASS based on mocked fixtures.
  - Never print API keys.
  - Exits 0 if all tests PASS, 1 if any FAIL or NOT CONFIGURED.

Usage:
  python -m scripts.live_smoke_test
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import httpx
from app.core.config import get_settings

settings = get_settings()

# Real Chennai coordinates
HOME_LAT = 12.9751      # Velachery
HOME_LON = 80.2202
WORK_LAT = 13.0786      # Rajiv Gandhi Govt General Hospital (Park Town)
WORK_LON = 80.2785

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"


async def test_route_transit(routes_key: str) -> bool:
    ist_offset = timedelta(hours=5, minutes=30)
    now_utc = datetime.now(timezone.utc)
    dep_ist = (now_utc + ist_offset).replace(hour=8, minute=30, second=0, microsecond=0)
    if dep_ist <= now_utc + ist_offset:
        dep_ist += timedelta(days=1)
    dep_utc = dep_ist - ist_offset

    payload = {
        "origin": {"location": {"latLng": {"latitude": HOME_LAT, "longitude": HOME_LON}}},
        "destination": {"location": {"latLng": {"latitude": WORK_LAT, "longitude": WORK_LON}}},
        "travelMode": "TRANSIT",
        "departureTime": dep_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "computeAlternativeRoutes": False,
        "languageCode": "en-IN",
        "units": "METRIC",
    }
    field_mask = "routes.duration,routes.distanceMeters,routes.legs.steps.travelMode"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                ROUTES_URL,
                json=payload,
                headers={"X-Goog-Api-Key": routes_key, "X-Goog-FieldMask": field_mask},
            )
        if resp.status_code == 200:
            data = resp.json()
            return bool(data.get("routes"))
    except Exception:
        pass
    return False


async def test_route_mode(routes_key: str, mode: str) -> bool:
    payload = {
        "origin": {"location": {"latLng": {"latitude": HOME_LAT, "longitude": HOME_LON}}},
        "destination": {"location": {"latLng": {"latitude": WORK_LAT, "longitude": WORK_LON}}},
        "travelMode": mode,
        "computeAlternativeRoutes": False,
        "languageCode": "en-IN",
        "units": "METRIC",
    }
    field_mask = "routes.duration,routes.distanceMeters,routes.polyline"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                ROUTES_URL,
                json=payload,
                headers={"X-Goog-Api-Key": routes_key, "X-Goog-FieldMask": field_mask},
            )
        if resp.status_code == 200:
            data = resp.json()
            return bool(data.get("routes"))
    except Exception:
        pass
    return False


async def test_places(places_key: str, place_type: str) -> bool:
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 3,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": HOME_LAT, "longitude": HOME_LON},
                "radius": 3000.0,
            }
        },
    }
    field_mask = "places.id,places.displayName,places.location"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                PLACES_URL,
                json=payload,
                headers={"X-Goog-Api-Key": places_key, "X-Goog-FieldMask": field_mask},
            )
        if resp.status_code == 200:
            data = resp.json()
            return "places" in data
    except Exception:
        pass
    return False


async def test_itinerary(routes_key: str) -> bool:
    """Test full door-to-door transit itinerary parsing with real Google Routes API."""
    from app.schemas.routing import RouteRequest
    from app.services.providers.route_google import GoogleRouteProvider

    provider = GoogleRouteProvider()
    if not provider.is_available():
        return False
    try:
        req = RouteRequest(
            origin_lat=HOME_LAT,
            origin_lon=HOME_LON,
            dest_lat=WORK_LAT,
            dest_lon=WORK_LON,
            modes=["TRANSIT"],
        )
        routes = await provider.compute_route(req)
        return bool(routes and routes[0].steps is not None and len(routes[0].steps) > 0)
    except Exception:
        return False


async def main() -> int:
    routes_key = settings.GOOGLE_ROUTES_API_KEY
    places_key = settings.GOOGLE_PLACES_API_KEY

    print()
    print("LIVE SMOKE TEST")
    print("===============")

    if not settings.RIVO_LIVE_API_TESTS:
        print("\nLIVE API CALLS ARE DISABLED (RIVO_LIVE_API_TESTS=false)")
        print("To protect API quotas during development, live calls are gated.")
        print("Set RIVO_LIVE_API_TESTS=true in backend/.env to run smoke tests.\n")
        return 0

    results = {}

    # Routes Transit
    if not routes_key:
        results["Routes Transit"] = "NOT CONFIGURED"
    else:
        ok = await test_route_transit(routes_key)
        results["Routes Transit"] = "PASS" if ok else "FAIL"

    # Routes Drive
    if not routes_key:
        results["Routes Drive"] = "NOT CONFIGURED"
    else:
        ok = await test_route_mode(routes_key, "DRIVE")
        results["Routes Drive"] = "PASS" if ok else "FAIL"

    # Routes Walk
    if not routes_key:
        results["Routes Walk"] = "NOT CONFIGURED"
    else:
        ok = await test_route_mode(routes_key, "WALK")
        results["Routes Walk"] = "PASS" if ok else "FAIL"

    # Places School
    if not places_key:
        results["Places School"] = "NOT CONFIGURED"
    else:
        ok = await test_places(places_key, "school")
        results["Places School"] = "PASS" if ok else "FAIL"

    # Places Hospital
    if not places_key:
        results["Places Hospital"] = "NOT CONFIGURED"
    else:
        ok = await test_places(places_key, "hospital")
        results["Places Hospital"] = "PASS" if ok else "FAIL"

    # Places Pharmacy
    if not places_key:
        results["Places Pharmacy"] = "NOT CONFIGURED"
    else:
        ok = await test_places(places_key, "pharmacy")
        results["Places Pharmacy"] = "PASS" if ok else "FAIL"

    # Itinerary
    if not routes_key:
        results["Itinerary"] = "NOT CONFIGURED"
    else:
        ok = await test_itinerary(routes_key)
        results["Itinerary"] = "PASS" if ok else "FAIL"

    for label, status in results.items():
        print(f"{label:<20} {status}")

    print()
    all_pass = all(s == "PASS" for s in results.values())
    if all_pass:
        print("OVERALL: ALL PASS (Verified with live Google APIs)")
        return 0
    else:
        print("OVERALL: SOME NOT CONFIGURED / FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
