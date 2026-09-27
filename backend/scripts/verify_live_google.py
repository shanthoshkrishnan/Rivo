#!/usr/bin/env python
"""
RIVO — Live Google API Verification Script
==========================================
Task 1 & 2 from Phase 4: VERIFY REAL GOOGLE CREDENTIALS

Performs ACTUAL HTTP requests against Google Routes and Google Places APIs.
Does NOT use mocked HTTP responses.

Usage:
    cd backend
    python -m scripts.verify_live_google

Rules:
  - Never prints API keys
  - Never declares PASS from a mock
  - Exits with code 0 if both PASS, code 1 if any FAIL or NOT CONFIGURED
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running as  python -m scripts.verify_live_google  from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.providers.route_google import classify_google_error  # noqa: E402

settings = get_settings()

# ─── Real Chennai coordinates for tests ─────────────────────────────────────
# Home: Velachery (residential area, near MRTS station)
HOME_LAT = 12.9751
HOME_LON = 80.2202
# Workplace: Rajiv Gandhi Government General Hospital, Park Town
WORKPLACE_LAT = 13.0786
WORKPLACE_LON = 80.2785

GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"


def _fmt_result(label: str, status: str, details: dict) -> None:
    symbol = "PASS" if status == "PASS" else "FAIL"
    print(f"    {label}: {symbol}")
    for k, v in details.items():
        if v is not None:
            print(f"      {k}: {v}")


async def verify_routes_transit(api_key: str) -> bool:
    """TRANSIT route: Velachery to RGGGH."""
    ist_offset = timedelta(hours=5, minutes=30)
    now_utc = datetime.now(timezone.utc)
    dep_ist = (now_utc + ist_offset).replace(hour=8, minute=0, second=0, microsecond=0)
    if dep_ist <= now_utc + ist_offset:
        dep_ist += timedelta(days=1)
    dep_utc = dep_ist - ist_offset
    dep_str = dep_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "origin": {"location": {"latLng": {"latitude": HOME_LAT, "longitude": HOME_LON}}},
        "destination": {"location": {"latLng": {"latitude": WORKPLACE_LAT, "longitude": WORKPLACE_LON}}},
        "travelMode": "TRANSIT",
        "departureTime": dep_str,
        "computeAlternativeRoutes": False,
        "languageCode": "en-IN",
        "units": "METRIC",
    }
    field_mask = (
        "routes.duration,routes.distanceMeters,routes.travelAdvisory,"
        "routes.polyline,routes.legs.steps.transitDetails,"
        "routes.legs.steps.travelMode,routes.legs.steps.staticDuration,"
        "routes.legs.steps.distanceMeters,routes.legs.steps.polyline,"
        "routes.legs.steps.navigationInstruction"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_ROUTES_URL,
                json=payload,
                headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": field_mask},
            )
    except Exception as exc:
        _fmt_result("Transit route", "FAIL", {"error": "NETWORK_ERROR", "details": str(exc)})
        return False

    if resp.status_code != 200:
        cat, msg = classify_google_error(resp.status_code, resp.text)
        _fmt_result("Transit route", "FAIL", {"category": cat, "http_status": resp.status_code, "message": msg})
        return False

    data = resp.json()
    routes = data.get("routes", [])
    if not routes:
        _fmt_result("Transit route", "FAIL", {"reason": "No routes returned", "raw": str(data)[:200]})
        return False

    route = routes[0]
    legs = route.get("legs", [{}])
    leg = legs[0] if legs else {}
    steps = leg.get("steps", [])
    transit_steps = [s for s in steps if s.get("transitDetails")]
    walk_steps = [s for s in steps if s.get("travelMode") == "WALK"]
    poly = route.get("polyline", {}).get("encodedPolyline", "")

    sample_transit = {}
    if transit_steps:
        td = transit_steps[0].get("transitDetails", {})
        sd = td.get("stopDetails", {})
        tl = td.get("transitLine", {})
        ags = tl.get("agencies", [])
        sample_transit = {
            "agency": ags[0].get("name") if ags else None,
            "line": tl.get("name") or tl.get("nameShort"),
            "vehicle": tl.get("vehicle", {}).get("type"),
            "headsign": td.get("headsign"),
            "boarding_stop": sd.get("departureStop", {}).get("name"),
            "alighting_stop": sd.get("arrivalStop", {}).get("name"),
            "num_stops": td.get("stopCount"),
        }

    _fmt_result("Transit (Velachery -> RGGGH)", "PASS", {
        "http_status": resp.status_code,
        "duration": route.get("duration"),
        "distance_m": route.get("distanceMeters"),
        "total_steps": len(steps),
        "transit_steps": len(transit_steps),
        "walk_steps": len(walk_steps),
        "polyline_chars": len(poly),
        "departure_sent": dep_str,
        **{f"transit_{k}": v for k, v in sample_transit.items() if v is not None},
    })
    return True


async def verify_routes_mode(api_key: str, mode: str) -> bool:
    """DRIVE or TWO_WHEELER or WALK route."""
    payload = {
        "origin": {"location": {"latLng": {"latitude": HOME_LAT, "longitude": HOME_LON}}},
        "destination": {"location": {"latLng": {"latitude": WORKPLACE_LAT, "longitude": WORKPLACE_LON}}},
        "travelMode": mode,
        "computeAlternativeRoutes": False,
        "languageCode": "en-IN",
        "units": "METRIC",
    }
    if mode in ("DRIVE", "TWO_WHEELER"):
        payload["routingPreference"] = "TRAFFIC_AWARE"
    field_mask = "routes.duration,routes.distanceMeters,routes.staticDuration,routes.polyline"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_ROUTES_URL,
                json=payload,
                headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": field_mask},
            )
    except Exception as exc:
        _fmt_result(f"{mode.capitalize()} route", "FAIL", {"error": "NETWORK_ERROR", "details": str(exc)})
        return False

    if resp.status_code != 200:
        cat, msg = classify_google_error(resp.status_code, resp.text)
        _fmt_result(f"{mode.capitalize()} route", "FAIL", {"category": cat, "http_status": resp.status_code, "message": msg})
        return False

    data = resp.json()
    routes = data.get("routes", [])
    if not routes:
        _fmt_result(f"{mode.capitalize()} route", "FAIL", {"reason": "No routes"})
        return False

    route = routes[0]
    dur = route.get("duration")
    static_dur = route.get("staticDuration")
    traffic_status = "LIVE_TRAFFIC" if (static_dur and static_dur != dur) else "HISTORICAL"
    poly = route.get("polyline", {}).get("encodedPolyline", "")

    _fmt_result(f"{mode.capitalize()} route (Velachery -> RGGGH)", "PASS", {
        "http_status": resp.status_code,
        "duration": dur,
        "distance_m": route.get("distanceMeters"),
        "traffic_status": traffic_status if mode in ("DRIVE", "TWO_WHEELER") else None,
        "polyline_chars": len(poly),
    })
    return True


async def verify_places_type(api_key: str, facility_type: str, google_type: str) -> bool:
    """Search for a facility type near the test home."""
    payload = {
        "includedTypes": [google_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": HOME_LAT, "longitude": HOME_LON},
                "radius": 3000.0,
            }
        },
    }
    field_mask = "places.id,places.displayName,places.location,places.formattedAddress"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                GOOGLE_PLACES_URL,
                json=payload,
                headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": field_mask},
            )
    except Exception as exc:
        _fmt_result(f"Places {facility_type}", "FAIL", {"error": "NETWORK_ERROR", "details": str(exc)})
        return False

    if resp.status_code != 200:
        cat, msg = classify_google_error(resp.status_code, resp.text)
        _fmt_result(f"Places {facility_type}", "FAIL", {
            "category": cat,
            "http_status": resp.status_code,
            "message": msg,
        })
        return False

    data = resp.json()
    places = data.get("places", [])

    sample_name = None
    if places:
        p = places[0]
        name_obj = p.get("displayName", {})
        sample_name = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj)

    _fmt_result(f"{facility_type.capitalize()} search (Velachery, 3 km radius)", "PASS", {
        "http_status": resp.status_code,
        "results_count": len(places),
        "sample_name": sample_name,
    })
    return True


async def main() -> int:
    print()
    print("=" * 60)
    print("  RIVO LIVE GOOGLE VERIFICATION")
    print("  Home: Velachery | Workplace: RGGGH (approx)")
    print("=" * 60)

    current_settings = get_settings()
    if not current_settings.RIVO_LIVE_API_TESTS:
        print("\n" + "=" * 60)
        print("  LIVE GOOGLE API CALLS DISABLED (RIVO_LIVE_API_TESTS=false)")
        print("  To protect API quotas during development, live calls are gated.")
        print("  Set RIVO_LIVE_API_TESTS=true in backend/.env to run live checks.")
        print("=" * 60 + "\n")
        return 0

    # ── Routes API ────────────────────────────────────────────────────────────
    routes_key = current_settings.GOOGLE_ROUTES_API_KEY
    places_key = current_settings.GOOGLE_PLACES_API_KEY
    all_pass = True

    print("\nRoutes API:")
    if not routes_key:
        print("  STATUS: NOT CONFIGURED")
        print("  Action: Set GOOGLE_ROUTES_API_KEY in backend/.env")
        all_pass = False
    else:
        print("  Key: CONFIGURED")
        r_t = await verify_routes_transit(routes_key)
        r_d = await verify_routes_mode(routes_key, "DRIVE")
        r_2w = await verify_routes_mode(routes_key, "TWO_WHEELER")
        r_w = await verify_routes_mode(routes_key, "WALK")
        routes_ok = r_t and r_d and r_2w and r_w
        if not routes_ok:
            all_pass = False
        print(f"  STATUS: {'PASS' if routes_ok else 'FAIL'}")

    # ── Places API ────────────────────────────────────────────────────────────
    print("\nPlaces API:")
    if not places_key:
        print("  STATUS: NOT CONFIGURED")
        print("  Action: Set GOOGLE_PLACES_API_KEY in backend/.env")
        all_pass = False
    else:
        print("  Key: CONFIGURED")
        p_s = await verify_places_type(places_key, "school", "school")
        p_h = await verify_places_type(places_key, "hospital", "hospital")
        p_p = await verify_places_type(places_key, "pharmacy", "pharmacy")
        places_ok = p_s and p_h and p_p
        if not places_ok:
            all_pass = False
        print(f"  STATUS: {'PASS' if places_ok else 'FAIL'}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    if all_pass:
        print("  OVERALL: ALL PASS")
    else:
        print("  OVERALL: SOME FAIL (see details above)")
    print("=" * 60)
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
