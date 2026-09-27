#!/usr/bin/env python
"""
RIVO — Deterministic Demo Workflow: Nurse at RGGGH (Tasks 18 & 19)
=================================================================
Runs the COMPLETE RIVO Home pipeline for the PS-11-S3 showcase persona:
  - Worker: Nurse (Healthcare worker)
  - Workplace: Rajiv Gandhi Government General Hospital (Park Town, Chennai)
  - Household: 2 adults, 2 children
  - Requirements: 2 BHK, School <= 15m, Hospital <= 20m, Pharmacy <= 10m
  - Mode: TRANSIT
  - Rent budget: ₹16,000 / month (based on PLFS 2025 healthcare worker income)

Outputs the structured explainability card and door-to-door transit plan.

Usage:
  python -m scripts.demo_nurse_workflow
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.schemas.recommendation import (
    FamilyContext,
    RecommendationRequest,
    WorkerContext,
)
from app.services.providers.registry import (
    get_places_provider,
    get_rental_provider,
    get_route_provider,
)
from app.services.recommendation_service import RecommendationService

# Coordinates
# Workplace: Rajiv Gandhi Government General Hospital, Park Town, Chennai
RGGGH_LAT = 13.0786
RGGGH_LON = 80.2785


async def run_nurse_demo() -> int:
    print("=" * 65)
    print("  RIVO — REAL CHENNAI HOME FINDER DEMO")
    print("  Persona: Nurse @ Rajiv Gandhi Govt General Hospital")
    print("  Problem Statement: PS-11-S3 (Housing + Mobility Affordability)")
    print("=" * 65)

    # 1. Setup Providers
    rental_prov = get_rental_provider()
    route_prov = get_route_provider()
    places_prov = get_places_provider()

    print(f"\nActive Providers:")
    print(f"  Rental Provider:   {rental_prov.provider_name}")
    print(f"  Route Provider:    {route_prov.provider_name} (Google enabled: {route_prov.supports_mode('TRANSIT')})")
    print(f"  Places Provider:   {places_prov.provider_name} (Google enabled: {places_prov.is_available()})")

    # 2. Build Recommendation Request
    req = RecommendationRequest(
        max_rent_monthly=16000.0,
        bhk=2,
        workplace_lat=RGGGH_LAT,
        workplace_lon=RGGGH_LON,
        workplace_label="Rajiv Gandhi Govt General Hospital, Park Town",
        max_commute_minutes=60,
        preferred_modes=["TRANSIT"],
        worker=WorkerContext(
            occupation_key="nurse",
            household_income_monthly=35000.0,
        ),
        family=FamilyContext(
            adults=2,
            children=2,
            child_age_bands=["6-12", "13-18"],
            school_max_minutes=15,
            hospital_max_minutes=20,
            pharmacy_max_minutes=10,
            require_within_threshold=False,
        ),
        search_radius_km=25.0,
        work_days_per_month=22,
        page=1,
        page_size=5,
    )

    print("\nRunning recommendation pipeline...")
    service = RecommendationService(
        rental_provider=rental_prov,
        route_provider=route_prov,
        places_provider=places_prov,
        db=None,
    )

    response = await service.search(req)

    print(f"Search complete: {response.total} matching candidate homes found.")
    if not response.results:
        print("No candidates found within criteria.")
        return 1

    top = response.results[0]

    # Task 19 Formatted Output
    print("\n" + "=" * 65)
    print("  TOP RECOMMENDATION — WHY THIS HOME PASSED (Task 19)")
    print("=" * 65)

    afford = top.affordability
    best_route = top.best_route
    commute_min = round(best_route.duration_seconds / 60, 1) if (best_route and best_route.duration_seconds) else "N/A"

    print(f"\n{top.locality.upper() if top.locality else 'CHENNAI RESIDENCE'}")
    print(f"₹{top.rent_monthly:,.0f} / month")
    print(f"{top.bhk} BHK | {top.area_sqft:,.0f} sqft | {top.furnishing.title() if top.furnishing else 'Unfurnished'}")
    print(f"Coordinates: ({top.latitude:.4f}, {top.longitude:.4f})")

    if afford:
        print(f"\nFinancial Feasibility:")
        print(f"  Housing burden:       {afford.housing_burden_pct * 100:.1f}% of income")
        print(f"  Commute time:         {commute_min} min one-way")
        print(f"  Monthly transport:    ₹{afford.monthly_transport_cost:,.0f}")
        print(f"  Cash burden (total):  {afford.cash_burden_pct * 100:.1f}%")
        print(f"  Monthly time tax:     {afford.monthly_commute_hours:.1f} hours")

    print(f"\nFamily Accessibility (Walking):")
    if top.school_access:
        s_sym = "PASS" if top.school_access.meets_threshold else "WARN"
        print(f"  [{s_sym}] School:   {top.school_access.nearest_minutes:.1f} min ({top.school_access.nearest_name}) — limit: 15 min")
    if top.hospital_access:
        h_sym = "PASS" if top.hospital_access.meets_threshold else "WARN"
        print(f"  [{h_sym}] Hospital: {top.hospital_access.nearest_minutes:.1f} min ({top.hospital_access.nearest_name}) — limit: 20 min")
    if top.pharmacy_access:
        p_sym = "PASS" if top.pharmacy_access.meets_threshold else "WARN"
        print(f"  [{p_sym}] Pharmacy: {top.pharmacy_access.nearest_minutes:.1f} min ({top.pharmacy_access.nearest_name}) — limit: 10 min")

    if best_route:
        print(f"\nTransit Details:")
        print(f"  Mode:            {best_route.mode}")
        print(f"  Transfers:       {best_route.transfer_count}")
        print(f"  Estimated Fare:  ₹{best_route.fare_amount or 20:.0f}")
        if best_route.steps:
            print(f"\n  Itinerary Steps:")
            for idx, s in enumerate(best_route.steps[:6], 1):
                dur_m = round(s.duration_seconds / 60, 1) if s.duration_seconds else 0
                step_desc = s.instruction or s.type
                if s.transit:
                    step_desc = f"{s.transit.line} ({s.transit.agency}) from {s.transit.departure_stop} to {s.transit.arrival_stop}"
                print(f"    {idx}. [{s.type}] {step_desc} ({dur_m} min)")

    print(f"\nData Provenance & Trust (Task 13 & 14):")
    print(f"  Rental Source:   {top.provider} ({top.data_freshness.value})")
    print(f"  Route Source:    {best_route.source_label if best_route else 'None'} ({best_route.data_freshness.value if best_route else 'N/A'})")
    print(f"  Confidence:      {top.explainability.confidence.value if top.explainability else 'MEDIUM'}")
    if "data_quality_score" in top.score_components:
        print(f"  Data Quality:    {top.score_components['data_quality_score']} / 1.00")
    print(f"  Overall Score:   {top.score_total:.3f} / 1.00")

    if top.explainability and top.explainability.positive_reasons:
        print(f"\nPositive Reasons:")
        for r in top.explainability.positive_reasons:
            print(f"  + {r}")

    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_nurse_demo()))
