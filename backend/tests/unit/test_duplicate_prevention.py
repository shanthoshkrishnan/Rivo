"""
RIVO Backend — Unit Tests for Duplicate Prevention & 240 Demo Inventory
========================================================================
Verifies:
  1. test_no_duplicate_properties_in_recommendation_results()
     Ensures that no duplicate listing IDs or canonical property identities
     occur in recommendation results.
  2. Diverse search scenarios return distinct property subsets.
  3. No property appears consecutively or multiple times.
  4. ML safety: Demo inventory records have eligible_for_model=False.
"""
import pytest
from app.schemas.recommendation import RecommendationRequest, FamilyContext, WorkerContext
from app.services.providers.rental_mock import MockRentalProvider
from app.services.providers.route_mock import MockRouteProvider
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def recommendation_service():
    rental = MockRentalProvider()
    route = MockRouteProvider()
    return RecommendationService(rental_provider=rental, route_provider=route)


@pytest.mark.asyncio
async def test_no_duplicate_properties_in_recommendation_results(recommendation_service):
    """
    Hard Duplicate Guarantee:
    Ensures that every property in recommendation results appears exactly ONCE.
    Zero consecutive duplicates and zero repeated canonical properties.
    """
    req = RecommendationRequest(
        workplace_lat=12.9893,
        workplace_lon=80.2483,
        workplace_label="TIDEL Park",
        min_rent_monthly=10000,
        max_rent_monthly=25000,
        bhk=2,
        max_commute_minutes=45,
        search_radius_km=25.0,
        page=1,
        page_size=20,
    )

    resp = await recommendation_service.search(req)

    # 1. Non-empty results from 240-property demo inventory
    assert resp.total > 0, "Expected matching homes in demo inventory"
    assert len(resp.results) > 0

    # 2. Hard check: unique listing IDs
    seen_ids = set()
    seen_canonical = set()
    for idx, r in enumerate(resp.results):
        assert r.listing_id not in seen_ids, (
            f"Duplicate listing_id '{r.listing_id}' found at index {idx}!"
        )
        seen_ids.add(r.listing_id)

        # Canonical key: locality + bhk + lat + lon
        canonical_key = f"{r.locality}_{r.bhk}_{round(r.latitude or 0, 4)}_{round(r.longitude or 0, 4)}"
        assert canonical_key not in seen_canonical, (
            f"Duplicate canonical property '{canonical_key}' found at index {idx}!"
        )
        seen_canonical.add(canonical_key)

    # 3. Consecutive duplicates check
    for i in range(len(resp.results) - 1):
        assert resp.results[i].listing_id != resp.results[i + 1].listing_id, (
            f"Consecutive identical property '{resp.results[i].listing_id}' at indices {i} and {i+1}!"
        )


@pytest.mark.asyncio
async def test_search_scenarios_produce_different_results(recommendation_service):
    """
    Verifies that distinct searches yield distinct property collections:
      Scenario A: Budget 1 BHK (₹8k–₹15k)
      Scenario B: Mid-tier 2 BHK (₹15k–₹25k)
      Scenario C: Premium 3/4 BHK (₹30k–₹65k)
    """
    # Scenario A: 1 BHK budget
    req_a = RecommendationRequest(
        workplace_lat=12.9893,
        workplace_lon=80.2483,
        workplace_label="TIDEL Park",
        min_rent_monthly=8000,
        max_rent_monthly=15000,
        bhk=1,
        max_commute_minutes=60,
        search_radius_km=30.0,
        page=1,
        page_size=10,
    )
    resp_a = await recommendation_service.search(req_a)

    # Scenario B: 2 BHK mid-range
    req_b = RecommendationRequest(
        workplace_lat=12.9893,
        workplace_lon=80.2483,
        workplace_label="TIDEL Park",
        min_rent_monthly=16000,
        max_rent_monthly=25000,
        bhk=2,
        max_commute_minutes=45,
        search_radius_km=30.0,
        page=1,
        page_size=10,
    )
    resp_b = await recommendation_service.search(req_b)

    # Scenario C: 3 BHK family / high budget
    req_c = RecommendationRequest(
        workplace_lat=12.9893,
        workplace_lon=80.2483,
        workplace_label="TIDEL Park",
        min_rent_monthly=30000,
        max_rent_monthly=65000,
        bhk=3,
        max_commute_minutes=60,
        search_radius_km=30.0,
        page=1,
        page_size=10,
    )
    resp_c = await recommendation_service.search(req_c)

    ids_a = {r.listing_id for r in resp_a.results}
    ids_b = {r.listing_id for r in resp_b.results}
    ids_c = {r.listing_id for r in resp_c.results}

    # Verify that the sets are disjoint due to strict BHK and rent range filtering
    assert ids_a.isdisjoint(ids_b), "1 BHK results and 2 BHK results must not overlap"
    assert ids_b.isdisjoint(ids_c), "2 BHK results and 3 BHK results must not overlap"
    assert ids_a.isdisjoint(ids_c), "1 BHK results and 3 BHK results must not overlap"


@pytest.mark.asyncio
async def test_demo_inventory_ml_safety():
    """
    ML Safety Guarantee:
    Demo listings must NEVER have eligible_for_model=True.
    """
    provider = MockRentalProvider()
    raw = provider._load_listings()
    assert len(raw) == 240, f"Expected 240 demo listings, got {len(raw)}"

    for item in raw:
        assert item.get("eligible_for_model") is False, (
            f"Listing {item.get('listing_id')} has eligible_for_model=True!"
        )
        assert item.get("is_demo") is True
        assert item.get("source") == "DEMO_SEEDED" or item.get("verification_state") == "DEMO"
