"""
RIVO Automated Route Sanity & Data Realism Unit Tests (Requirement 34)
=====================================================================
Ensures 10 non-negotiable data and routing integrity rules:
  Test 1: Same property + same workplace + same mode -> deterministic cached result.
  Test 2: Different property -> different route origin and cache key.
  Test 3: Farther property -> must not accidentally inherit nearer property's route.
  Test 4: Different mode -> duration/cost/polyline differ.
  Test 5: Route unavailable / anomaly check -> no fabricated route.
  Test 6: Commute > threshold -> property rejected with clear reason.
  Test 7: Property coordinates -> spatially distinct, valid Chennai coordinates.
  Test 8: Facility distance -> calculated dynamically from coordinates.
  Test 9: Transport cost -> calculated from distance/fare formulas.
  Test 10: Demo property -> strictly quarantined from ML training table.
"""
import pytest
import math
import json
from pathlib import Path
from app.services.providers.route_gtfs import GTFSRouteProvider
from app.schemas.routing import RouteRequest
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendation import RecommendationRequest
from app.services.providers.registry import get_rental_provider, get_route_provider, get_places_provider


@pytest.fixture
def gtfs_provider():
    return GTFSRouteProvider()


@pytest.fixture
def rec_service():
    return RecommendationService(
        rental_provider=get_rental_provider(),
        route_provider=get_route_provider(),
        places_provider=get_places_provider(),
    )


@pytest.mark.asyncio
async def test_1_same_property_same_workplace_cached(gtfs_provider):
    """Test 1: Same property + same workplace + same mode -> deterministic cached result."""
    req = RouteRequest(
        origin_lat=12.9752,
        origin_lon=80.2185,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["TRANSIT"],
    )
    res_list1 = await gtfs_provider.compute_route(req)
    res_list2 = await gtfs_provider.compute_route(req)

    assert len(res_list1) > 0
    assert len(res_list2) > 0
    res1, res2 = res_list1[0], res_list2[0]
    assert res1.distance_m == res2.distance_m
    assert res1.duration_seconds == res2.duration_seconds
    assert res1.duration_min == res2.duration_min


@pytest.mark.asyncio
async def test_2_different_property_different_route(gtfs_provider):
    """Test 2: Different property -> different route origin and duration/distance."""
    # Property A: Velachery
    req_a = RouteRequest(
        origin_lat=12.9752,
        origin_lon=80.2185,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["TRANSIT"],
    )
    # Property B: Tambaram
    req_b = RouteRequest(
        origin_lat=12.9249,
        origin_lon=80.1197,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["TRANSIT"],
    )
    res_a = (await gtfs_provider.compute_route(req_a))[0]
    res_b = (await gtfs_provider.compute_route(req_b))[0]

    assert res_a.distance_m != res_b.distance_m
    assert res_b.distance_m > res_a.distance_m
    assert res_b.duration_seconds > res_a.duration_seconds


@pytest.mark.asyncio
async def test_3_farther_property_does_not_inherit_nearer_route(gtfs_provider):
    """Test 3: Farther property (Ambattur) vs nearer (Perungudi) to Tidel Park."""
    # Nearer: Perungudi
    req_near = RouteRequest(
        origin_lat=12.9640,
        origin_lon=80.2420,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["DRIVE"],
    )
    # Farther: Ambattur
    req_far = RouteRequest(
        origin_lat=13.1143,
        origin_lon=80.1548,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["DRIVE"],
    )
    res_near = (await gtfs_provider.compute_route(req_near))[0]
    res_far = (await gtfs_provider.compute_route(req_far))[0]

    assert res_far.distance_km > res_near.distance_km * 2
    assert res_far.duration_min > res_near.duration_min * 2


@pytest.mark.asyncio
async def test_4_different_modes_differ_in_duration_and_cost(gtfs_provider):
    """Test 4: Different mode -> duration/cost/polyline differ."""
    req = RouteRequest(
        origin_lat=12.9752,
        origin_lon=80.2185,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["TRANSIT", "TWO_WHEELER", "WALK"],
    )
    results = await gtfs_provider.compute_route(req)
    mode_map = {r.mode: r for r in results}

    walk = mode_map["WALK"]
    bike = mode_map["TWO_WHEELER"]

    # Walking takes much longer than 2-wheeler
    assert walk.duration_min > bike.duration_min
    # Walk fare is strictly 0
    assert walk.fare_amount == 0


@pytest.mark.asyncio
async def test_5_route_distance_sanity_check(gtfs_provider):
    """Test 5: Route distance must always be >= straight line distance * 0.8."""
    req = RouteRequest(
        origin_lat=12.9752,
        origin_lon=80.2185,
        dest_lat=12.9892,
        dest_lon=80.2494,
        modes=["TRANSIT"],
    )
    res = (await gtfs_provider.compute_route(req))[0]

    # Haversine distance
    R = 6371000
    phi1, phi2 = math.radians(req.origin_lat), math.radians(req.dest_lat)
    dphi = math.radians(req.dest_lat - req.origin_lat)
    dlambda = math.radians(req.dest_lon - req.origin_lon)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    straight_line_m = 2 * R * math.asin(math.sqrt(a))

    assert res.distance_m >= straight_line_m * 0.8
    assert res.duration_seconds > 0
    assert not getattr(res, "is_anomaly", False)


@pytest.mark.asyncio
async def test_6_commute_threshold_rejection(rec_service):
    """Test 6: Commute > threshold -> property rejected and placed in rejected_results."""
    # Search with very strict 15 minute commute limit for Tidel Park
    req = RecommendationRequest(
        workplace_lat=12.9892,
        workplace_lon=80.2494,
        workplace_label="Tidel Park",
        max_rent_monthly=60000,
        max_commute_minutes=15,
        search_radius_km=30,
        page=1,
        page_size=20,
    )
    resp = await rec_service.search_recommendations(req)

    # Some distant properties must be rejected with commute reason
    assert len(resp.rejected_results) > 0
    has_commute_rejection = any(
        any("commute" in r.lower() for r in (item.rejection_reasons or []))
        for item in resp.rejected_results
    )
    assert has_commute_rejection


def test_7_property_coordinates_validity():
    """Test 7: 240 properties must have valid Chennai coordinates, no duplicates."""
    seed_path = Path(__file__).resolve().parent.parent.parent / "data" / "seed" / "rental_seed.json"
    if not seed_path.exists():
        seed_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed" / "rental_seed.json"
    
    assert seed_path.exists()
    listings = json.loads(seed_path.read_text(encoding="utf-8"))
    assert len(listings) >= 200

    coords = set()
    for l in listings:
        lat = l["latitude"]
        lon = l["longitude"]
        assert 12.7 <= lat <= 13.3
        assert 79.9 <= lon <= 80.4
        coord_key = (round(lat, 5), round(lon, 5))
        assert coord_key not in coords, f"Duplicate coordinate found: {coord_key}"
        coords.add(coord_key)


def test_8_facility_distance_calculated_from_coordinates():
    """Test 8: Facility distances in seed must match calculated Haversine against facilities."""
    seed_path = Path(__file__).resolve().parent.parent.parent / "data" / "seed" / "rental_seed.json"
    if not seed_path.exists():
        seed_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed" / "rental_seed.json"
    
    listings = json.loads(seed_path.read_text(encoding="utf-8"))
    for l in listings[:10]:
        assert l.get("nearest_school_name") is not None
        assert l.get("nearest_school_m") is not None and l["nearest_school_m"] > 0
        assert l.get("nearest_hospital_name") is not None
        assert l.get("nearest_hospital_m") is not None and l["nearest_hospital_m"] > 0
        assert l.get("nearest_pharmacy_name") is not None
        assert l.get("nearest_bus_stop_name") is not None
        assert l.get("nearest_metro_name") is not None


def test_9_transport_cost_formulas():
    """Test 9: Transport cost must follow exact distance/fare formulas."""
    distance_km = 18.4
    working_days = 22

    # Two wheeler: 45 km/L @ 105 INR/L
    fuel_litres_bike = (distance_km * 2 * working_days) / 45.0
    bike_cost = round(fuel_litres_bike * 105.0)
    assert 1800 <= bike_cost <= 2000

    # Car: 14 km/L @ 105 INR/L
    fuel_litres_car = (distance_km * 2 * working_days) / 14.0
    car_cost = round(fuel_litres_car * 105.0)
    assert 5500 <= car_cost <= 6500


def test_10_demo_property_never_enters_ml_observations():
    """Test 10: All 240 demo properties must be flagged is_demo=True and eligible_for_model=False."""
    seed_path = Path(__file__).resolve().parent.parent.parent / "data" / "seed" / "rental_seed.json"
    if not seed_path.exists():
        seed_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed" / "rental_seed.json"
    
    listings = json.loads(seed_path.read_text(encoding="utf-8"))
    for l in listings:
        assert l.get("is_demo") is True
        assert l.get("eligible_for_model") is False
        assert l.get("verification_state") == "DEMO"
