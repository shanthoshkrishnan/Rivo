"""
RIVO Backend — Unit Tests: Affordability Algorithms
======================================================
Tests all pure functions in app/services/algorithms/affordability.py.

These tests have no external dependencies — no DB, no Redis, no HTTP.
They verify the mathematical correctness of affordability, scoring,
hard-constraint, and explainability logic.
"""
from __future__ import annotations

import pytest

from app.core.config import ConfidenceLevel
from app.services.algorithms.affordability import (
    AffordabilityResult,
    check_hard_constraints,
    compute_affordability,
    compute_commute_score,
    compute_confidence_level,
    compute_family_score,
    compute_housing_score,
    compute_monthly_transit_cost,
    compute_total_score,
    compute_transport_score,
    facility_fit,
    generate_why_text,
)


# ─────────────────────────────────────────────────────────────────────────────
# §5 Household affordability
# ─────────────────────────────────────────────────────────────────────────────
class TestAffordability:
    def test_housing_burden_calculation(self):
        result = compute_affordability(
            rent_monthly=12000,
            maintenance_monthly=800,
            transport_cost_monthly=1600,
            household_income_monthly=24000,
        )
        assert result.housing_burden == pytest.approx(12000 / 24000, rel=1e-3)
        assert result.transport_burden == pytest.approx(1600 / 24000, rel=1e-3)
        assert result.cash_burden == pytest.approx((12000 + 800 + 1600) / 24000, rel=1e-3)
        assert result.monthly_total_cost == 14400

    def test_no_income_gives_no_burden(self):
        result = compute_affordability(
            rent_monthly=12000,
            maintenance_monthly=800,
            transport_cost_monthly=1600,
            household_income_monthly=None,
        )
        assert result.housing_burden is None
        assert result.monthly_total_cost == 14400

    def test_time_tax(self):
        result = compute_affordability(
            rent_monthly=12000,
            maintenance_monthly=800,
            transport_cost_monthly=1600,
            household_income_monthly=24000,
            one_way_commute_minutes=38,
            work_days=22,
        )
        # monthly_commute_hours = 38 × 2 × 22 / 60
        expected = round(38 * 2 * 22 / 60, 2)
        assert result.monthly_commute_hours == pytest.approx(expected, rel=1e-3)


# ─────────────────────────────────────────────────────────────────────────────
# §9 Monthly transit cost
# ─────────────────────────────────────────────────────────────────────────────
class TestTransitCost:
    def test_basic_monthly_cost(self):
        # one-way ₹40, 22 days
        cost = compute_monthly_transit_cost(40.0, work_days=22)
        assert cost == 40.0 * 2 * 22

    def test_default_work_days(self):
        cost = compute_monthly_transit_cost(40.0)
        assert cost > 0


# ─────────────────────────────────────────────────────────────────────────────
# §11 Facility fit
# ─────────────────────────────────────────────────────────────────────────────
class TestFacilityFit:
    def test_within_threshold(self):
        assert facility_fit(10.0, 15) is True

    def test_at_threshold(self):
        assert facility_fit(15.0, 15) is True

    def test_exceeds_threshold(self):
        assert facility_fit(16.0, 15) is False

    def test_unknown_travel_time(self):
        assert facility_fit(None, 15) is None

    def test_no_threshold(self):
        assert facility_fit(10.0, None) is None


# ─────────────────────────────────────────────────────────────────────────────
# §16 Hard constraints
# ─────────────────────────────────────────────────────────────────────────────
class TestHardConstraints:
    def _base_kwargs(self, **overrides) -> dict:
        kwargs = dict(
            rent_monthly=12000,
            max_rent_monthly=15000,
            bhk=2,
            required_bhk=2,
            property_type="flat",
            required_property_type="flat",
            is_available=True,
            commute_minutes=38,
            max_commute_minutes=60,
        )
        kwargs.update(overrides)
        return kwargs

    def test_all_pass(self):
        result = check_hard_constraints(**self._base_kwargs())
        assert result.passes is True
        assert result.failures == []

    def test_rent_exceeds_budget(self):
        result = check_hard_constraints(**self._base_kwargs(rent_monthly=20000))
        assert result.passes is False
        assert any("rent" in f for f in result.failures)

    def test_wrong_bhk(self):
        result = check_hard_constraints(**self._base_kwargs(bhk=1))
        assert result.passes is False
        assert any("bhk" in f for f in result.failures)

    def test_not_available(self):
        result = check_hard_constraints(**self._base_kwargs(is_available=False))
        assert result.passes is False
        assert any("available" in f for f in result.failures)

    def test_commute_too_long(self):
        result = check_hard_constraints(**self._base_kwargs(commute_minutes=90))
        assert result.passes is False
        assert any("commute" in f for f in result.failures)

    def test_no_required_bhk(self):
        result = check_hard_constraints(**self._base_kwargs(required_bhk=None))
        assert result.passes is True


# ─────────────────────────────────────────────────────────────────────────────
# §15 Scoring
# ─────────────────────────────────────────────────────────────────────────────
class TestScoring:
    def test_housing_score_at_budget(self):
        score = compute_housing_score(15000, 15000)
        assert score == 0.0

    def test_housing_score_below_budget(self):
        score = compute_housing_score(7500, 15000)
        assert score > 0.0
        assert score <= 1.0

    def test_commute_score_zero_commute(self):
        assert compute_commute_score(0, 60) == 1.0

    def test_commute_score_at_max(self):
        assert compute_commute_score(60, 60) == 0.0

    def test_total_score_range(self):
        score = compute_total_score(
            housing_score=0.8,
            commute_score=0.7,
            transport_score=0.6,
            family_score=1.0,
            work_access_score=0.5,
            confidence_score=0.8,
        )
        assert 0.0 <= score <= 1.0

    def test_family_score_all_pass(self):
        assert compute_family_score(True, True, True) == 1.0

    def test_family_score_one_fail(self):
        assert compute_family_score(True, False, True) == pytest.approx(2 / 3, rel=1e-3)

    def test_family_score_no_thresholds(self):
        assert compute_family_score(None, None, None) == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# §18 Confidence
# ─────────────────────────────────────────────────────────────────────────────
class TestConfidence:
    def test_high_confidence(self):
        level = compute_confidence_level(
            listing_count=10,
            source_diversity=3,
            has_geocode=True,
            has_route=True,
            has_facility_data=True,
        )
        assert level == ConfidenceLevel.HIGH

    def test_low_confidence(self):
        level = compute_confidence_level(
            listing_count=0,
            source_diversity=1,
            has_geocode=False,
            has_route=False,
            has_facility_data=False,
        )
        assert level == ConfidenceLevel.LOW


# ─────────────────────────────────────────────────────────────────────────────
# Explainability
# ─────────────────────────────────────────────────────────────────────────────
class TestExplainability:
    def test_all_positive(self):
        pos, neg = generate_why_text(
            passes_rent=True,
            passes_commute=True,
            passes_bhk=True,
            school_fits=True,
            hospital_fits=True,
            pharmacy_fits=True,
            preferred_mode_matched=True,
            hard_failures=[],
        )
        assert "within_budget" in pos
        assert "commute_within_limit" in pos
        assert len(neg) == 0

    def test_rent_over_budget_in_negatives(self):
        pos, neg = generate_why_text(
            passes_rent=False,
            passes_commute=True,
            passes_bhk=True,
            school_fits=None,
            hospital_fits=None,
            pharmacy_fits=None,
            preferred_mode_matched=False,
            hard_failures=["rent_exceeds_budget"],
        )
        assert "rent_over_budget" in neg
