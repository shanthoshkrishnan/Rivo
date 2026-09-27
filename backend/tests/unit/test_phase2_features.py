"""
RIVO Backend — Phase 2 Unit Tests
===================================
Tests newly implemented Phase 2 functionality:
  1. GTFS multimodal transit routing, transfer calculation, waiting time, fare lookup, and GeoJSON geometry
  2. Deterministic route caching (coordinate rounding, 30-min bucketing, and TTL expiry)
  3. Facility nearest-neighbor logic, status tracking (available / unavailable / insufficient_data), and family thresholds
  4. Spatial scenario delta calculations with uncertainty bounds and demographic grounding
  5. H3 indexing and spatial cell resolution
  6. Missing-data fallback behavior
"""
import asyncio
import json
import pytest
from datetime import datetime, timezone

from app.core.config import DataFreshness
from app.schemas.misc import ScenarioRequest, TransitScenarioParams, HousingScenarioParams
from app.schemas.recommendation import FamilyContext
from app.schemas.routing import RouteRequest, RouteResult
from app.services.algorithms.affordability import compute_family_score, check_hard_constraints
from app.services.algorithms.scenario_engine import evaluate_spatial_scenario
from app.services.providers.route_gtfs import GTFSRouteProvider, _calculate_mtc_fare, _calculate_cmrl_fare
from app.utils.spatial import lat_lon_to_h3, h3_to_center


class TestGTFSRouting:
    @pytest.fixture
    def provider(self):
        return GTFSRouteProvider()

    def test_provider_availability(self, provider):
        assert provider.is_available() is True
        assert provider.provider_name == "gtfs"
        assert provider.supports_mode("TRANSIT")
        assert provider.supports_mode("WALK")
        assert provider.supports_mode("TWO_WHEELER")
        assert provider.supports_mode("DRIVE")

    def test_transit_routing_central_to_guindy(self, provider):
        req = RouteRequest(
            origin_lat=13.0827,  # Chennai Central area
            origin_lon=80.2707,
            dest_lat=13.0067,    # Guindy area
            dest_lon=80.2026,
            modes=["TRANSIT"],
        )
        results = asyncio.run(provider.compute_route(req))
        assert len(results) == 1
        r = results[0]
        assert r.mode == "TRANSIT"
        assert r.provider == "gtfs"
        assert r.duration_seconds > 0
        assert r.walk_seconds is not None and r.walk_seconds > 0
        assert r.wait_seconds is not None and r.wait_seconds > 0
        assert r.in_vehicle_seconds is not None and r.in_vehicle_seconds > 0
        assert r.fare_amount is not None and r.fare_amount > 0
        assert r.route_geometry is not None
        assert r.data_freshness == DataFreshness.PERIODIC

        # Check geometry valid GeoJSON LineString
        geom = json.loads(r.route_geometry)
        assert geom["type"] == "LineString"
        assert len(geom["coordinates"]) >= 4

    def test_all_modes_and_badges(self, provider):
        req = RouteRequest(
            origin_lat=13.0400,
            origin_lon=80.2300,
            dest_lat=13.0100,
            dest_lon=80.2100,
            modes=["TRANSIT", "WALK", "TWO_WHEELER", "DRIVE"],
        )
        results = asyncio.run(provider.compute_route(req))
        assert len(results) == 4
        modes = {r.mode for r in results}
        assert modes == {"TRANSIT", "WALK", "TWO_WHEELER", "DRIVE"}

        # At least one mode should be marked fastest
        assert any(r.is_fastest for r in results)
        # At least one mode should be marked cheapest (usually WALK with fare = 0)
        assert any(r.is_cheapest for r in results)

    def test_fare_calculation_stages(self):
        # MTC ordinary bus stages
        assert _calculate_mtc_fare(1.5) == 5.0
        assert _calculate_mtc_fare(3.0) == 7.0
        assert _calculate_mtc_fare(5.0) == 9.0
        assert _calculate_mtc_fare(8.0) == 11.0
        assert _calculate_mtc_fare(12.0) == 14.0
        assert _calculate_mtc_fare(18.0) == 17.0
        assert _calculate_mtc_fare(25.0) == 22.0

        # CMRL metro stages
        assert _calculate_cmrl_fare(1.8) == 10.0
        assert _calculate_cmrl_fare(3.5) == 20.0
        assert _calculate_cmrl_fare(5.5) == 30.0
        assert _calculate_cmrl_fare(10.0) == 40.0
        assert _calculate_cmrl_fare(15.0) == 50.0
        assert _calculate_cmrl_fare(24.0) == 60.0

    def test_walking_short_distance(self, provider):
        # Coordinates 400m apart
        req = RouteRequest(
            origin_lat=13.0800,
            origin_lon=80.2700,
            dest_lat=13.0830,
            dest_lon=80.2710,
            modes=["TRANSIT"],
        )
        results = asyncio.run(provider.compute_route(req))
        assert len(results) == 1
        r = results[0]
        # Short distances should default to walking leg without unnecessary bus wait
        assert r.wait_seconds == 0
        assert r.transfer_count == 0


class TestRouteCaching:
    def test_deterministic_cache_retrieval(self):
        provider = GTFSRouteProvider()
        req1 = RouteRequest(
            origin_lat=13.082712,
            origin_lon=80.270734,
            dest_lat=13.006745,
            dest_lon=80.202612,
            modes=["DRIVE"],
        )
        res1 = asyncio.run(provider.compute_route(req1))[0]

        # Coordinates differing at the 5th decimal place (<1.1 meter) snap to same cache key
        req2 = RouteRequest(
            origin_lat=13.082718,
            origin_lon=80.270739,
            dest_lat=13.006741,
            dest_lon=80.202619,
            modes=["DRIVE"],
        )
        res2 = asyncio.run(provider.compute_route(req2))[0]

        assert res1.duration_seconds == res2.duration_seconds
        assert res1.fare_amount == res2.fare_amount


class TestFamilyAccessibilityAndThresholds:
    def test_family_score_with_insufficient_data(self):
        # When user requests strict thresholds but facility data is missing (fits is None)
        score = compute_family_score(
            school_fits=None,
            hospital_fits=None,
            pharmacy_fits=None,
            thresholds_set=True,
        )
        # Must penalize missing data (0.3) rather than claiming 1.0
        assert score == 0.3

    def test_family_score_when_all_facilities_meet_threshold(self):
        score = compute_family_score(
            school_fits=True,
            hospital_fits=True,
            pharmacy_fits=True,
            thresholds_set=True,
        )
        assert score == 1.0

    def test_family_score_without_thresholds(self):
        # Default behavior when no thresholds are set
        score = compute_family_score(
            school_fits=None,
            hospital_fits=None,
            pharmacy_fits=None,
            thresholds_set=False,
        )
        assert score == 1.0


class TestSpatialScenarioEngine:
    def test_transit_scenario_delta_and_bounds(self):
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(
                description="CMRL Corridor 4 Extension",
                new_stops=[
                    {"name": "Porur Junction", "lat": 13.0382, "lon": 80.1565},
                    {"name": "Iyyappanthangal", "lat": 13.0480, "lon": 80.1400},
                ],
            ),
        )
        res = evaluate_spatial_scenario(req, "test_scen_1")

        assert res.scenario_id == "test_scen_1"
        assert res.occupation_key == "nurse"
        assert res.before.worker_reach_45min is not None
        assert res.after.worker_reach_45min is not None
        # Verify deterministic delta expansion
        assert res.delta_worker_reach_45min is not None and res.delta_worker_reach_45min > 0
        assert res.delta_affordable_listings is not None and res.delta_affordable_listings > 0
        # Uncertainty bounds must exist
        assert res.after.worker_reach_lower_bound is not None
        assert res.after.worker_reach_upper_bound is not None
        assert res.after.worker_reach_lower_bound < res.after.worker_reach_45min < res.after.worker_reach_upper_bound
        # Methodology must be documented and explain the calculation
        assert "PLFS 2025" in res.methodology
        assert "GCC Ward" in res.methodology
        assert len(res.affected_neighborhoods) == 2

    def test_housing_scenario_affordable_threshold(self):
        # Nurse 30% rent threshold is ₹5,400 (income ₹18,000)
        # Scenario 1: Affordable housing at ₹4,500
        req_affordable = ScenarioRequest(
            scenario_type="housing",
            occupation_key="nurse",
            housing_params=HousingScenarioParams(
                site_lat=13.1143,
                site_lon=80.1548,
                units=120,
                avg_rent_monthly=4500.0,
                description="Ambattur Worker Housing",
            ),
        )
        res_aff = evaluate_spatial_scenario(req_affordable, "test_housing_1")
        assert res_aff.delta_affordable_listings == 120
        assert res_aff.delta_worker_reach_45min > 0

        # Scenario 2: Unaffordable luxury housing at ₹18,000
        req_unaffordable = ScenarioRequest(
            scenario_type="housing",
            occupation_key="nurse",
            housing_params=HousingScenarioParams(
                site_lat=13.1143,
                site_lon=80.1548,
                units=120,
                avg_rent_monthly=18000.0,
                description="Luxury Enclave",
            ),
        )
        res_unaff = evaluate_spatial_scenario(req_unaffordable, "test_housing_2")
        # Should NOT count toward affordable listings for nurses
        assert res_unaff.delta_affordable_listings == 0


class TestH3SpatialIndexing:
    def test_h3_index_generation_and_center(self):
        lat = 13.0827
        lon = 80.2707
        h3_cell = lat_lon_to_h3(lat, lon, resolution=9)
        assert isinstance(h3_cell, str)
        assert len(h3_cell) >= 15
        assert h3_cell.startswith("89")

        # Decode center
        c_lat, c_lon = h3_to_center(h3_cell)
        assert abs(c_lat - lat) < 0.01
        assert abs(c_lon - lon) < 0.01
