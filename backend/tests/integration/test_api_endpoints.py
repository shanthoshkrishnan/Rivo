"""
RIVO Backend — Integration Tests: Mock Provider Endpoints
===========================================================
Tests the full API endpoints using httpx AsyncClient with the
mock providers (no DB, no Redis, no external APIs required).

These tests verify that the API contract is correct and that
the mock provider returns consistent data.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


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


class TestHealthEndpoint:
    @pytest.mark.anyio
    async def test_health_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "rental_provider" in data


class TestRentalsEndpoint:
    @pytest.mark.anyio
    async def test_search_requires_max_rent(self, client: AsyncClient):
        resp = await client.get("/api/v1/rentals/search")
        assert resp.status_code == 422   # missing required param

    @pytest.mark.anyio
    async def test_search_returns_listings(self, client: AsyncClient):
        resp = await client.get("/api/v1/rentals/search?max_rent_monthly=15000")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total" in data
        assert "data_freshness" in data
        # All returned listings should be within budget
        for listing in data["results"]:
            if listing["rent_monthly"] is not None:
                assert listing["rent_monthly"] <= 15000

    @pytest.mark.anyio
    async def test_search_bhk_filter(self, client: AsyncClient):
        resp = await client.get("/api/v1/rentals/search?max_rent_monthly=20000&bhk=2")
        assert resp.status_code == 200
        data = resp.json()
        for listing in data["results"]:
            assert listing["bhk"] == 2

    @pytest.mark.anyio
    async def test_get_listing_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/rentals/NONEXISTENT-999")
        assert resp.status_code == 404


class TestRoutesEndpoint:
    @pytest.mark.anyio
    async def test_compare_routes(self, client: AsyncClient):
        payload = {
            "origin_lat": 12.9751,
            "origin_lon": 80.2202,
            "dest_lat": 13.0669,
            "dest_lon": 80.2425,
            "modes": ["TRANSIT", "DRIVE", "WALK"],
        }
        resp = await client.post("/api/v1/routes/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "routes" in data
        assert len(data["routes"]) > 0
        # At least one mode should be marked fastest
        fastest = [r for r in data["routes"] if r.get("is_fastest")]
        assert len(fastest) >= 1

    @pytest.mark.anyio
    async def test_route_includes_freshness(self, client: AsyncClient):
        payload = {
            "origin_lat": 12.9751,
            "origin_lon": 80.2202,
            "dest_lat": 13.0669,
            "dest_lon": 80.2425,
        }
        resp = await client.post("/api/v1/routes/compare", json=payload)
        data = resp.json()
        for route in data["routes"]:
            assert "data_freshness" in route


class TestWorkersEndpoint:
    @pytest.mark.anyio
    async def test_list_occupations(self, client: AsyncClient):
        resp = await client.get("/api/v1/workers/occupations")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4
        keys = [o["occupation_key"] for o in data]
        assert "nurse" in keys

    @pytest.mark.anyio
    async def test_get_nurse_income(self, client: AsyncClient):
        resp = await client.get("/api/v1/workers/income/nurse")
        assert resp.status_code == 200
        data = resp.json()
        assert "income_median" in data
        assert data["income_median"] is not None
        assert "data_freshness" in data
        assert "source_name" in data

    @pytest.mark.anyio
    async def test_unknown_occupation_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/workers/income/unknown_occupation_xyz")
        assert resp.status_code == 404


class TestDataSourcesEndpoint:
    @pytest.mark.anyio
    async def test_list_sources(self, client: AsyncClient):
        resp = await client.get("/api/v1/data/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5
        # All sources should have attribution
        source_names = [s["source_name"] for s in data]
        assert "RIVO Sample Data" in source_names
        assert "OpenStreetMap" in source_names


class TestScenariosEndpoint:
    @pytest.mark.anyio
    async def test_transit_scenario(self, client: AsyncClient):
        payload = {
            "scenario_type": "transit",
            "occupation_key": "nurse",
            "transit_params": {
                "new_stops": [
                    {"name": "Velachery Extended", "lat": 12.975, "lon": 80.220}
                ],
                "new_routes": [],
                "description": "Test transit scenario",
            },
            "commute_threshold_minutes": 45,
        }
        resp = await client.post("/api/v1/scenarios/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "before" in data
        assert "after" in data
        assert data["data_freshness"] == "ESTIMATED"
        # After should have more worker reach with a new stop
        if data["after"]["worker_reach_45min"] and data["before"]["worker_reach_45min"]:
            assert data["after"]["worker_reach_45min"] >= data["before"]["worker_reach_45min"]
