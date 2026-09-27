"""
RIVO Backend — Unit Tests for Spatial Scenario Engine (City Planner)
====================================================================
Tests the 12 mathematical and logical rules required for the RIVO City
urban intelligence scenario engine:
  1. Increasing commute threshold cannot decrease reachable workers.
  2. Reducing commute time cannot increase commute burden.
  3. Increasing transport cost cannot increase money saved.
  4. Current and proposed values must use the same worker population.
  5. Worker gain: proposed_reachable_workers - current_reachable_workers.
  6. Time saved: current_commute - proposed_commute.
  7. Monthly time saved: time_saved_per_trip * 2 * workdays / 60.
  8. Annual time saved: monthly * 12.
  9. Monthly money saved: current_transport_cost - proposed_transport_cost.
  10. Annual money saved: monthly * 12.
  11. Housing affordability must use selected income percentile.
  12. Switching from Transit Expansion to Housing Supply must change calculation pipeline.
"""
from __future__ import annotations

import pytest
from app.schemas.misc import (
    HousingScenarioParams,
    ScenarioRequest,
    TransitScenarioParams,
)
from app.services.algorithms.scenario_engine import evaluate_spatial_scenario


class TestScenarioPlannerLogic:

    def test_1_increasing_commute_threshold_monotonic(self):
        """1. Increasing commute threshold cannot decrease reachable workers."""
        req_30 = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=30,
        )
        req_45 = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
        )
        req_60 = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=60,
        )

        res_30 = evaluate_spatial_scenario(req_30, "test-30")
        res_45 = evaluate_spatial_scenario(req_45, "test-45")
        res_60 = evaluate_spatial_scenario(req_60, "test-60")

        assert res_30.proposed.reachable_workers <= res_45.proposed.reachable_workers
        assert res_45.proposed.reachable_workers <= res_60.proposed.reachable_workers
        assert res_30.current.reachable_workers <= res_45.current.reachable_workers

    def test_2_reducing_commute_time_reduces_or_maintains_burden(self):
        """2. Reducing commute time cannot increase commute burden."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-burden")
        assert res.proposed.median_commute_minutes < res.current.median_commute_minutes
        assert res.proposed.transport_burden_pct <= res.current.transport_burden_pct

    def test_3_transport_cost_and_savings_consistency(self):
        """3. Increasing transport cost cannot increase money saved."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-cost")
        # Proposed cost is lower, money saved must be positive
        assert res.proposed.monthly_transport_cost < res.current.monthly_transport_cost
        assert res.change.monthly_transport_savings > 0
        assert res.change.monthly_transport_savings == (
            res.current.monthly_transport_cost - res.proposed.monthly_transport_cost
        )

    def test_4_same_worker_population_and_income_base(self):
        """4. Current and proposed values must use the same worker population & income baseline."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            income_band="median",
            commute_threshold_minutes=45,
        )
        res = evaluate_spatial_scenario(req, "test-pop")
        assert res.current.monthly_income == res.proposed.monthly_income
        assert res.occupation_key == "nurse"

    def test_5_worker_gain_formula(self):
        """5. Worker gain: proposed_reachable_workers - current_reachable_workers."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-gain")
        expected_gain = res.proposed.reachable_workers - res.current.reachable_workers
        assert res.change.workers_reached == expected_gain
        assert res.delta_worker_reach_45min == expected_gain

    def test_6_time_saved_formula(self):
        """6. Time saved: current_commute - proposed_commute."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-time")
        expected_time_saved = round(
            res.current.median_commute_minutes - res.proposed.median_commute_minutes, 1
        )
        assert res.change.commute_minutes_saved_per_trip == expected_time_saved
        assert res.worker_impact.time_saved_per_trip_minutes == expected_time_saved

    def test_7_monthly_time_saved_formula(self):
        """7. Monthly time saved: time_saved_per_trip * 2 * workdays / 60."""
        workdays = 26
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            work_days_per_month=workdays,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-monthly-time")
        time_per_trip = res.worker_impact.time_saved_per_trip_minutes
        expected_monthly_hours = round((time_per_trip * 2 * workdays) / 60.0, 2)
        assert res.worker_impact.monthly_time_saved_hours == expected_monthly_hours

    def test_8_annual_time_saved_formula(self):
        """8. Annual time saved: monthly * 12."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            work_days_per_month=26,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-annual-time")
        expected_annual_hours = round(res.worker_impact.monthly_time_saved_hours * 12.0, 2)
        assert res.worker_impact.annual_time_saved_hours == expected_annual_hours

    def test_9_monthly_money_saved_formula(self):
        """9. Monthly money saved: current_transport_cost - proposed_transport_cost."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-monthly-money")
        expected_monthly_money = (
            res.current.monthly_transport_cost - res.proposed.monthly_transport_cost
        )
        assert res.change.monthly_transport_savings == expected_monthly_money
        assert res.worker_impact.monthly_money_saved == expected_monthly_money

    def test_10_annual_money_saved_formula(self):
        """10. Annual money saved: monthly * 12."""
        req = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            commute_threshold_minutes=45,
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        res = evaluate_spatial_scenario(req, "test-annual-money")
        expected_annual_money = res.worker_impact.monthly_money_saved * 12.0
        assert res.change.annual_transport_savings == expected_annual_money
        assert res.worker_impact.annual_money_saved == expected_annual_money

    def test_11_housing_affordability_uses_income_percentile(self):
        """11. Housing affordability must use selected income percentile."""
        req_p25 = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            income_band="p25",
        )
        req_p75 = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            income_band="p75",
        )
        res_p25 = evaluate_spatial_scenario(req_p25, "test-p25")
        res_p75 = evaluate_spatial_scenario(req_p75, "test-p75")

        assert res_p25.current.monthly_income < res_p75.current.monthly_income
        # Lower income with same rent has higher housing burden
        assert res_p25.current.housing_burden_pct > res_p75.current.housing_burden_pct

    def test_12_switching_transit_to_housing_changes_pipeline(self):
        """12. Switching from Transit Expansion to Housing Supply must change the calculation pipeline."""
        req_transit = ScenarioRequest(
            scenario_type="transit",
            occupation_key="nurse",
            transit_params=TransitScenarioParams(corridor_id="cmrl_c4"),
        )
        req_housing = ScenarioRequest(
            scenario_type="housing",
            occupation_key="nurse",
            housing_params=HousingScenarioParams(
                site_locality="ambattur",
                units=120,
                avg_rent_monthly=14000.0,
            ),
        )

        res_transit = evaluate_spatial_scenario(req_transit, "test-transit")
        res_housing = evaluate_spatial_scenario(req_housing, "test-housing")

        assert res_transit.scenario_type == "transit"
        assert res_housing.scenario_type == "housing"
        # Housing scenario directly adds affordable units
        assert res_housing.change.affordable_listings_added == 120
        assert "housing supply" in res_housing.scenario_name.lower() or "workforce housing" in res_housing.scenario_name.lower()
