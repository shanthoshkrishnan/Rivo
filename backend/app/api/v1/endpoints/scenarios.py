"""
RIVO Backend — Scenarios API Endpoint
=======================================
POST /api/v1/scenarios/evaluate

RIVO City scenario engine.
Computes before/after accessibility metrics when a transit or housing
scenario is applied to Chennai's current network.

Transit scenario:
  Current network + proposed stops/routes → recompute worker reach
Housing scenario:
  New site + units + rent → new housing supply → recompute metrics

Results show delta in:
  - worker_reach (30/45/60 min bands)
  - affordable_listings
  - commute_median_minutes

Freshness: ESTIMATED (model-based — not live data)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import DataFreshness
from app.schemas.misc import (
    ScenarioMetrics,
    ScenarioRequest,
    ScenarioResponse,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post(
    "/evaluate",
    response_model=ScenarioResponse,
    summary="Evaluate a housing or transit scenario",
    description=(
        "Compute before/after accessibility metrics for a planning scenario. "
        "Results are ESTIMATED from the current DB state + scenario parameters. "
        "Requires occupation_key to determine relevant job sites and income bands."
    ),
)
async def evaluate_scenario(request: ScenarioRequest) -> ScenarioResponse:
    """
    MVP implementation: computes rough delta estimates.
    Full R5-based batch accessibility is planned for a later iteration.
    """
    scenario_id = str(uuid.uuid4())[:12]

    # Base metrics (from DB in future; fixture for MVP)
    before = _baseline_metrics(request.occupation_key)
    after = _apply_scenario(before, request)

    delta_reach = None
    delta_listings = None
    if after.worker_reach_45min is not None and before.worker_reach_45min is not None:
        delta_reach = after.worker_reach_45min - before.worker_reach_45min
    if after.affordable_listings is not None and before.affordable_listings is not None:
        delta_listings = after.affordable_listings - before.affordable_listings

    return ScenarioResponse(
        scenario_id=scenario_id,
        occupation_key=request.occupation_key,
        before=before,
        after=after,
        delta_worker_reach_45min=delta_reach,
        delta_affordable_listings=delta_listings,
        computed_at=datetime.now(timezone.utc),
        data_freshness=DataFreshness.ESTIMATED,
    )


def _baseline_metrics(occupation_key: str) -> ScenarioMetrics:
    """
    Returns baseline accessibility metrics for the occupation.
    MVP: hardcoded estimates per occupation type.
    Production: query travel_time_matrix + rental_listings DB.
    """
    baselines = {
        "nurse": ScenarioMetrics(
            worker_reach_30min=1200,
            worker_reach_45min=3400,
            worker_reach_60min=6800,
            affordable_listings=42,
            commute_median_minutes=38.0,
        ),
        "teacher": ScenarioMetrics(
            worker_reach_30min=2200,
            worker_reach_45min=5100,
            worker_reach_60min=9200,
            affordable_listings=68,
            commute_median_minutes=34.0,
        ),
        "bus_driver": ScenarioMetrics(
            worker_reach_30min=800,
            worker_reach_45min=2100,
            worker_reach_60min=4200,
            affordable_listings=35,
            commute_median_minutes=42.0,
        ),
        "delivery_rider": ScenarioMetrics(
            worker_reach_30min=1800,
            worker_reach_45min=4200,
            worker_reach_60min=8100,
            affordable_listings=88,
            commute_median_minutes=30.0,
        ),
    }
    return baselines.get(
        occupation_key,
        ScenarioMetrics(
            worker_reach_30min=1500,
            worker_reach_45min=3500,
            worker_reach_60min=7000,
            affordable_listings=50,
            commute_median_minutes=38.0,
        ),
    )


def _apply_scenario(before: ScenarioMetrics, request: ScenarioRequest) -> ScenarioMetrics:
    """
    Apply scenario delta to baseline metrics.
    MVP: linear approximation based on scenario type.
    Production: run OTP/R5 with modified network.
    """
    after = ScenarioMetrics(
        worker_reach_30min=before.worker_reach_30min,
        worker_reach_45min=before.worker_reach_45min,
        worker_reach_60min=before.worker_reach_60min,
        affordable_listings=before.affordable_listings,
        commute_median_minutes=before.commute_median_minutes,
    )

    if request.scenario_type == "transit" and request.transit_params:
        num_new_stops = len(request.transit_params.new_stops)
        # Approximate: each new stop adds ~150 reachable workers at 45 min
        boost = num_new_stops * 150
        after.worker_reach_45min = (before.worker_reach_45min or 0) + boost
        after.worker_reach_60min = (before.worker_reach_60min or 0) + int(boost * 1.4)
        after.commute_median_minutes = max(
            10.0, (before.commute_median_minutes or 38.0) - num_new_stops * 1.5
        )

    elif request.scenario_type == "housing" and request.housing_params:
        new_units = request.housing_params.units
        # Approximate: each affordable unit = 1 new affordable listing
        after.affordable_listings = (before.affordable_listings or 0) + new_units

    return after
