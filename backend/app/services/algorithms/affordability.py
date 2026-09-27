"""
RIVO Backend — Affordability & Scoring Algorithms
===================================================
Pure functions implementing all algorithms from ALGORITHMS.md.
No database access, no external calls — only math.

Sections implemented:
  5.  Household affordability (housing_burden, transport_burden, cash_burden)
  6.  Time tax (monthly commute hours)
  7.  Optional value of time
  8.  Route comparison → badge assignment (in providers)
  9.  Transport cost (monthly)
  10. Car / two-wheeler fuel cost
  11. Facility access fit
  14. WorkerReach (30/45/60 min bands)
  15. Recommendation score (weighted components)
  16. Hard constraints
  18. Confidence level

All money in INR.  All times in seconds unless noted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.config import ConfidenceLevel, get_settings

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# §5 Household affordability
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class AffordabilityResult:
    housing_burden: Optional[float] = None      # rent / income
    transport_burden: Optional[float] = None    # transport_cost / income
    cash_burden: Optional[float] = None         # (rent + maint + transport) / income
    monthly_total_cost: Optional[float] = None
    monthly_commute_hours: Optional[float] = None
    monetized_time: Optional[float] = None


def compute_affordability(
    rent_monthly: Optional[float],
    maintenance_monthly: Optional[float],
    transport_cost_monthly: Optional[float],
    household_income_monthly: Optional[float],
    one_way_commute_minutes: Optional[float] = None,
    work_days: Optional[int] = None,
    hourly_value_of_time: Optional[float] = None,
) -> AffordabilityResult:
    """
    Implements ALGORITHMS.md §5, §6, §7.

    housing_burden    = rent / income
    transport_burden  = transport_cost / income
    cash_burden       = (rent + maintenance + transport) / income
    monthly_commute_h = one_way_min × 2 × work_days / 60

    NOTE: Do NOT make monetized_time the primary affordability criterion.
    """
    _work_days = work_days or settings.DEFAULT_WORK_DAYS_PER_MONTH
    result = AffordabilityResult()

    rent = rent_monthly or 0.0
    maintenance = maintenance_monthly or 0.0
    transport = transport_cost_monthly or 0.0
    income = household_income_monthly

    result.monthly_total_cost = rent + maintenance + transport

    if income and income > 0:
        result.housing_burden = round(rent / income, 4)
        result.transport_burden = round(transport / income, 4)
        result.cash_burden = round((rent + maintenance + transport) / income, 4)

    if one_way_commute_minutes is not None:
        result.monthly_commute_hours = round(
            one_way_commute_minutes * 2 * _work_days / 60, 2
        )
        if hourly_value_of_time is not None:
            result.monetized_time = round(
                hourly_value_of_time * result.monthly_commute_hours, 2
            )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# §9 & §10 Transport cost
# ─────────────────────────────────────────────────────────────────────────────
def compute_monthly_transit_cost(
    one_way_fare: float,
    work_days: Optional[int] = None,
) -> float:
    """
    §9: monthly_cost = (outbound_fare + return_fare) × work_days
    """
    _work_days = work_days or settings.DEFAULT_WORK_DAYS_PER_MONTH
    return round(one_way_fare * 2 * _work_days, 2)


def compute_fuel_cost_one_way(
    distance_km: float,
    fuel_price_inr: float,
    efficiency_kmpl: float,
) -> float:
    """
    §10: fuel_cost = (distance_km / efficiency_kmpl) × fuel_price
    """
    if efficiency_kmpl <= 0:
        raise ValueError("efficiency_kmpl must be positive")
    return round((distance_km / efficiency_kmpl) * fuel_price_inr, 2)


def compute_monthly_fuel_cost(
    distance_km: float,
    fuel_price_inr: float,
    efficiency_kmpl: float,
    work_days: Optional[int] = None,
) -> float:
    """Round-trip fuel cost × work_days per month."""
    _work_days = work_days or settings.DEFAULT_WORK_DAYS_PER_MONTH
    one_way = compute_fuel_cost_one_way(distance_km, fuel_price_inr, efficiency_kmpl)
    return round(one_way * 2 * _work_days, 2)


# ─────────────────────────────────────────────────────────────────────────────
# §11 Facility access fit
# ─────────────────────────────────────────────────────────────────────────────
def facility_fit(
    travel_time_minutes: Optional[float],
    threshold_minutes: Optional[int],
) -> Optional[bool]:
    """
    §11: facility_fit = 1 if travel_time <= threshold else 0
    Returns None if travel_time is unknown (data unavailable).
    """
    if travel_time_minutes is None or threshold_minutes is None:
        return None
    return travel_time_minutes <= threshold_minutes


# ─────────────────────────────────────────────────────────────────────────────
# §16 Hard constraints
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class HardConstraintResult:
    passes: bool
    failures: List[str] = field(default_factory=list)


def check_hard_constraints(
    rent_monthly: Optional[float],
    max_rent_monthly: float,
    bhk: Optional[int],
    required_bhk: Optional[int],
    property_type: Optional[str],
    required_property_type: Optional[str],
    is_available: bool,
    commute_minutes: Optional[float],
    max_commute_minutes: Optional[int],
    min_rent_monthly: Optional[float] = None,
) -> HardConstraintResult:
    """
    §16: Reject listings that violate hard constraints.
    Hard constraints are binary pass/fail — they are never "soft preferences".

    Filtering order per AGENTS.md:
      1. availability
      2. property type
      3. BHK
      4. hard rent budget
      5. commute max
    """
    failures: List[str] = []

    if not is_available:
        failures.append("listing_not_available")
    if required_property_type and property_type != required_property_type.lower():
        failures.append(f"property_type_mismatch (got {property_type}, need {required_property_type})")
    if required_bhk is not None and bhk != required_bhk:
        failures.append(f"bhk_mismatch (got {bhk}, need {required_bhk})")
    if rent_monthly is not None:
        if min_rent_monthly is not None and rent_monthly < min_rent_monthly:
            failures.append(f"rent_below_minimum ({rent_monthly:.0f} < {min_rent_monthly:.0f})")
        if rent_monthly > max_rent_monthly:
            failures.append(f"rent_exceeds_budget ({rent_monthly:.0f} > {max_rent_monthly:.0f})")
    if (
        commute_minutes is not None
        and max_commute_minutes is not None
        and commute_minutes > max_commute_minutes
    ):
        failures.append(
            f"commute_too_long ({commute_minutes:.0f} min > {max_commute_minutes} min)"
        )

    return HardConstraintResult(passes=len(failures) == 0, failures=failures)


# ─────────────────────────────────────────────────────────────────────────────
# §15 Recommendation score
# ─────────────────────────────────────────────────────────────────────────────

# Default weights from ALGORITHMS.md §15
# These are tunable defaults, NOT scientific universal weights.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "housing": 0.30,
    "commute": 0.25,
    "transport": 0.15,
    "family": 0.15,
    "work_access": 0.10,
    "confidence": 0.05,
}


def compute_housing_score(
    rent_monthly: float,
    max_rent_monthly: float,
    cash_burden: Optional[float] = None,
) -> float:
    """
    Higher score = rent is further below budget and burden is lower.
    0.0 = at or above budget  1.0 = rent is 0 (theoretical max)
    """
    if rent_monthly >= max_rent_monthly:
        return 0.0
    base = 1.0 - (rent_monthly / max_rent_monthly)
    # Penalise high cash burden
    if cash_burden is not None:
        burden_penalty = min(cash_burden, 1.0) * 0.3
        base = max(0.0, base - burden_penalty)
    return round(min(1.0, base), 4)


def compute_commute_score(
    commute_minutes: Optional[float],
    max_commute_minutes: int,
) -> float:
    """
    1.0 if commute is 0, 0.0 if at or above max.
    Linear between 0 and max.
    """
    if commute_minutes is None:
        return 0.5   # unknown → neutral score
    if commute_minutes >= max_commute_minutes:
        return 0.0
    return round(1.0 - (commute_minutes / max_commute_minutes), 4)


def compute_transport_score(
    monthly_transport_cost: Optional[float],
    household_income_monthly: Optional[float],
) -> float:
    """
    Score based on transport burden (transport_cost / income).
    0% burden → 1.0   50%+ burden → 0.0
    """
    if monthly_transport_cost is None:
        return 0.5
    if household_income_monthly is None or household_income_monthly <= 0:
        return 0.5
    burden = monthly_transport_cost / household_income_monthly
    return round(max(0.0, 1.0 - burden * 2), 4)


def compute_family_score(
    school_fits: Optional[bool],
    hospital_fits: Optional[bool],
    pharmacy_fits: Optional[bool],
    thresholds_set: bool = False,
) -> float:
    """
    Average binary fit across required facilities.
    If thresholds were requested by the user but facility data was missing for all,
    returns 0.3 (insufficient data penalty) rather than a false 1.0 pass.
    If no thresholds were requested, returns 1.0.
    """
    votes = []
    for fit in (school_fits, hospital_fits, pharmacy_fits):
        if fit is not None:
            votes.append(1.0 if fit else 0.0)
    if not votes:
        return 0.3 if thresholds_set else 1.0
    return round(sum(votes) / len(votes), 4)


def compute_confidence_score(confidence: Optional[str]) -> float:
    """Map HIGH/MEDIUM/LOW/None to 1.0/0.6/0.2/0.4."""
    mapping = {
        ConfidenceLevel.HIGH: 1.0,
        ConfidenceLevel.MEDIUM: 0.6,
        ConfidenceLevel.LOW: 0.2,
    }
    if confidence is None:
        return 0.4
    return mapping.get(confidence, 0.4)  # type: ignore


def compute_total_score(
    housing_score: float,
    commute_score: float,
    transport_score: float,
    family_score: float,
    work_access_score: float = 0.5,
    confidence_score: float = 0.5,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    §15 weighted aggregate score.
    work_access_score defaults to 0.5 (neutral) when not computable.
    """
    w = weights or DEFAULT_WEIGHTS
    total = (
        housing_score    * w.get("housing", 0.30)
        + commute_score  * w.get("commute", 0.25)
        + transport_score * w.get("transport", 0.15)
        + family_score   * w.get("family", 0.15)
        + work_access_score * w.get("work_access", 0.10)
        + confidence_score  * w.get("confidence", 0.05)
    )
    return round(min(1.0, max(0.0, total)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# §18 Confidence
# ─────────────────────────────────────────────────────────────────────────────
def compute_confidence_level(
    listing_count: int,
    source_diversity: int,
    has_geocode: bool,
    has_route: bool,
    has_facility_data: bool,
) -> ConfidenceLevel:
    """
    §18: Confidence uses listing count, source diversity, geocode quality,
    route-provider availability, facility completeness.
    Returns HIGH / MEDIUM / LOW — not an arbitrary percentage.
    """
    score = 0
    if listing_count >= 5:
        score += 2
    elif listing_count >= 2:
        score += 1
    if source_diversity >= 2:
        score += 1
    if has_geocode:
        score += 1
    if has_route:
        score += 1
    if has_facility_data:
        score += 1

    if score >= 5:
        return ConfidenceLevel.HIGH
    if score >= 3:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


# ─────────────────────────────────────────────────────────────────────────────
# Explainability text generator (no LLM — from data only)
# ─────────────────────────────────────────────────────────────────────────────
def generate_why_text(
    passes_rent: bool,
    passes_commute: bool,
    passes_bhk: bool,
    school_fits: Optional[bool],
    hospital_fits: Optional[bool],
    pharmacy_fits: Optional[bool],
    preferred_mode_matched: bool,
    hard_failures: List[str],
) -> tuple[List[str], List[str]]:
    """
    Generate human-readable positive/negative reasons from data.
    UI displays these under "Why this home?".
    """
    positive: List[str] = []
    negative: List[str] = []

    if passes_rent:
        positive.append("within_budget")
    if passes_commute:
        positive.append("commute_within_limit")
    if passes_bhk:
        positive.append("correct_bhk")
    if school_fits is True:
        positive.append("school_within_target")
    if hospital_fits is True:
        positive.append("hospital_within_target")
    if pharmacy_fits is True:
        positive.append("pharmacy_within_target")
    if preferred_mode_matched:
        positive.append("transit_match")

    if not passes_rent:
        negative.append("rent_over_budget")
    if not passes_commute:
        negative.append("commute_too_long")
    if school_fits is False:
        negative.append("school_far")
    if hospital_fits is False:
        negative.append("hospital_far")
    if pharmacy_fits is False:
        negative.append("pharmacy_far")
    for f in hard_failures:
        if f not in negative:
            negative.append(f)

    return positive, negative
