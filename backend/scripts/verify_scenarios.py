import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.schemas.recommendation import RecommendationRequest, FamilyContext
from app.services.providers.rental_mock import MockRentalProvider
from app.services.providers.route_mock import MockRouteProvider
from app.services.recommendation_service import RecommendationService

async def main():
    rental = MockRentalProvider()
    route = MockRouteProvider()
    service = RecommendationService(rental_provider=rental, route_provider=route)

    scenarios = [
        ("Tidel Park (INR 10k-16k, 2 BHK, <=45 min)", {
            "workplace_lat": 12.9893, "workplace_lon": 80.2483, "workplace_label": "TIDEL Park",
            "min_rent_monthly": 10000, "max_rent_monthly": 16000, "bhk": 2, "max_commute_minutes": 45,
            "search_radius_km": 25.0
        }),
        ("Tidel Park (INR 15k-25k, 2 BHK, <=30 min)", {
            "workplace_lat": 12.9893, "workplace_lon": 80.2483, "workplace_label": "TIDEL Park",
            "min_rent_monthly": 15000, "max_rent_monthly": 25000, "bhk": 2, "max_commute_minutes": 30,
            "search_radius_km": 25.0
        }),
        ("Chennai Central (INR 20k-40k, 3 BHK, family)", {
            "workplace_lat": 13.0827, "workplace_lon": 80.2707, "workplace_label": "Chennai Central",
            "min_rent_monthly": 20000, "max_rent_monthly": 40000, "bhk": 3, "max_commute_minutes": 60,
            "search_radius_km": 30.0,
            "family": {"adults": 2, "children": 1, "child_age_bands": ["6-12"]}
        }),
        ("Ambattur (INR 8k-12k, 1 BHK)", {
            "workplace_lat": 13.1143, "workplace_lon": 80.1548, "workplace_label": "Ambattur Estate",
            "min_rent_monthly": 8000, "max_rent_monthly": 12000, "bhk": 1, "max_commute_minutes": 60,
            "search_radius_km": 30.0
        }),
        ("Guindy (INR 30k-60k, 4 BHK)", {
            "workplace_lat": 13.0067, "workplace_lon": 80.2025, "workplace_label": "Guindy SIDCO",
            "min_rent_monthly": 30000, "max_rent_monthly": 60000, "bhk": 4, "max_commute_minutes": 60,
            "search_radius_km": 35.0
        }),
    ]

    print("==================================================")
    print("DEMO SEARCH SCENARIO VERIFICATION")
    print("==================================================")

    scenario_results = {}
    for name, params in scenarios:
        family_ctx = None
        if "family" in params:
            f = params.pop("family")
            family_ctx = FamilyContext(**f)

        req = RecommendationRequest(**params, family=family_ctx, page=1, page_size=15)
        resp = await service.search(req)

        ids = [r.listing_id for r in resp.results]
        unique_ids = set(ids)
        assert len(ids) == len(unique_ids), f"DUPLICATE DETECTED in scenario '{name}'! {ids}"

        # Consecutive check
        for i in range(len(ids) - 1):
            assert ids[i] != ids[i+1], f"CONSECUTIVE DUPLICATE in '{name}' at index {i}"

        scenario_results[name] = unique_ids
        print(f"\n[Scenario: {name}]")
        print(f"  Matched: {resp.total} homes | Returned: {len(resp.results)}")
        print(f"  Unique listing IDs: {len(unique_ids)} | Duplicate IDs: 0")
        for r in resp.results[:3]:
            print(f"    - {r.listing_id}: INR {int(r.rent_monthly or 0):,} | {r.bhk} BHK | {r.locality} | Commute: ~{int(r.best_route.duration_minutes if r.best_route else 0)}m | Score: {r.score_total:.2f}")

    print("\n==================================================")
    print("ALL SCENARIOS PASSED WITH ZERO DUPLICATES")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
