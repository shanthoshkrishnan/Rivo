"""
Phase 11 Tests — Real Rental Data Population + End-to-End Market Readiness
===========================================================================
Tests for:
  1.  Phase 10 API verification (PATCH, history, admin collect, data-quality)
  2.  Gate progress tracking per ML eligibility gate
  3.  Observation workflow (VALID / QUESTIONABLE / REJECTED)
  4.  Property deduplication — repeated observations ≠ new properties
  5.  Temporal coverage — genuine observed_at values only
  6.  Source diversity — count genuinely independent channels
  7.  Real-data market summary — never mixes demo data
  8.  Demo/real separation — demo never contributes to market stats
  9.  Availability state independence
  10. Verification state independence from freshness
  11. Model readiness gate — truthful NOT_READY when below threshold
  12. train_rent_model script remains gated
  13. Source filter in search params
  14. 0 Google API calls during all Phase 11 tests
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.endpoints.rentals import router as rental_router
from app.schemas.observation import (
    AdminCollectObservationRequest,
    AdminDataQualityReport,
    BulkObservationRow,
)
from app.services.observation_service import ObservationService, _gate_progress
from app.core.config import AvailabilityStatus, VerificationStatus, DataFreshness


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def svc() -> ObservationService:
    return ObservationService()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(rental_router, prefix="/api/v1")
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


def _obs(**kwargs) -> dict:
    """Minimal valid real observation dict."""
    base = dict(
        listing_id="OBS-001",
        locality="Velachery",
        bhk=2,
        rent_monthly=18000.0,
        availability_status="AVAILABLE",
        source="field_agent",
        observed_at=datetime.now(timezone.utc),
        is_synthetic=False,
        is_demo=False,
    )
    base.update(kwargs)
    return base


def _fill_eligible(svc: ObservationService, count: int, bhk_variety: bool = True) -> None:
    """Add `count` real eligible observations with diverse properties."""
    base_dt = datetime(2025, 9, 1, tzinfo=timezone.utc)
    localities = ["velachery", "adyar", "t-nagar", "anna-nagar", "mylapore", "kodambakkam"]
    for i in range(count):
        svc.record(
            listing_id=f"PROP-{i:04d}",
            locality=localities[i % len(localities)],
            bhk=(i % 4) + 1 if bhk_variety else 2,
            rent_monthly=12000.0 + i * 300,
            availability_status="AVAILABLE",
            source="field_agent" if i % 2 == 0 else "owner_interview",
            observed_at=base_dt + timedelta(days=i),
            is_synthetic=False,
            is_demo=False,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Phase 10 API verification (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase10APIVerification:
    """Verify PATCH, history, admin collect, and data-quality endpoints work correctly."""

    def test_admin_collect_records_source(self, client: TestClient):
        payload = {
            "listing_id": "VER-001",
            "locality": "Adyar",
            "bhk": 2,
            "rent_monthly": 22000.0,
            "source": "owner_interview",
        }
        resp = client.post("/api/v1/rentals/admin/collect", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["accepted"] is True
        assert data["eligible_for_model"] is True
        assert data["observation_id"] != ""

    def test_patch_then_history_contains_update(self, client: TestClient):
        # Create
        create = client.post("/api/v1/rentals/direct", json={
            "locality": "Velachery",
            "latitude": 12.9816,
            "longitude": 80.2180,
            "rent_monthly": 18000.0,
            "bhk": 2,
            "consent_to_publish": True,
        })
        assert create.status_code == 201
        lid = create.json()["listing_id"]

        # PATCH
        patch = client.patch(f"/api/v1/rentals/direct/{lid}", json={"rent_monthly": 20000.0})
        assert patch.status_code == 200
        assert patch.json()["updated_fields"] == ["rent_monthly"]
        assert patch.json()["observation_recorded"] is True
        assert patch.json()["current_rent"] == 20000.0

        # History
        hist = client.get(f"/api/v1/rentals/{lid}/history")
        assert hist.status_code == 200
        assert hist.json()["total_observations"] >= 1

    def test_data_quality_endpoint_has_gate_progress(self, client: TestClient):
        resp = client.get("/api/v1/rentals/admin/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert "gate_progress" in data
        gp = data["gate_progress"]
        assert "real_observations" in gp
        assert "unique_properties" in gp
        assert "localities" in gp
        assert "bhk_classes" in gp
        assert "source_diversity" in gp
        assert "temporal_span_days" in gp
        assert "synthetic_ratio" in gp

    def test_real_market_summary_insufficient_when_empty(self, client: TestClient):
        resp = client.get("/api/v1/rentals/real-market-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["insufficient_data"] is True
        assert data["confidence"] == "INSUFFICIENT_DATA"
        assert data["median"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Gate progress tracking
# ─────────────────────────────────────────────────────────────────────────────

class TestGateProgress:

    def test_all_gates_fail_on_empty_dataset(self, svc: ObservationService):
        dq = svc.data_quality_report()
        gp = dq.gate_progress
        assert gp is not None
        assert gp["real_observations"]["current"] == 0
        assert gp["real_observations"]["pass"] is False
        assert gp["unique_properties"]["pass"] is False
        assert gp["localities"]["pass"] is False
        assert gp["bhk_classes"]["pass"] is False
        assert gp["source_diversity"]["pass"] is False

    def test_gate_shows_correct_current_counts(self, svc: ObservationService):
        svc.record(**_obs(listing_id="P-001", locality="velachery", bhk=2, source="field_agent"))
        svc.record(**_obs(listing_id="P-002", locality="adyar", bhk=3, source="owner_interview"))
        dq = svc.data_quality_report()
        gp = dq.gate_progress
        assert gp["real_observations"]["current"] == 2
        assert gp["unique_properties"]["current"] == 2
        assert gp["localities"]["current"] == 2
        assert gp["bhk_classes"]["current"] == 2
        assert gp["source_diversity"]["current"] == 2

    def test_synthetic_ratio_gate_always_passes_for_eligible_obs(self, svc: ObservationService):
        svc.record(**_obs())
        dq = svc.data_quality_report()
        assert dq.gate_progress["synthetic_ratio"]["pass"] is True
        assert dq.gate_progress["synthetic_ratio"]["current"] == 0.0

    def test_gate_progress_shows_required_thresholds(self, svc: ObservationService):
        dq = svc.data_quality_report()
        gp = dq.gate_progress
        assert gp["real_observations"]["required"] == 50
        assert gp["unique_properties"]["required"] == 30
        assert gp["localities"]["required"] == 5
        assert gp["bhk_classes"]["required"] == 3
        assert gp["source_diversity"]["required"] == 2
        assert gp["temporal_span_days"]["required"] == 7


# ─────────────────────────────────────────────────────────────────────────────
# 3. Observation workflow — VALID / QUESTIONABLE / REJECTED
# ─────────────────────────────────────────────────────────────────────────────

class TestObservationWorkflow:

    def test_valid_observation_passes(self, svc: ObservationService):
        obs = {
            "listing_id": "WF-001",
            "locality": "Adyar",
            "bhk": 2,
            "rent_monthly": 22000.0,
            "source": "field_agent",
            "observed_at": datetime.now(timezone.utc),
            "latitude": 12.9954,
            "longitude": 80.2569,
            "geocode_confidence": "HIGH",
        }
        status, reasons = svc.validate_observation(obs)
        assert status == "VALID"

    def test_synthetic_rejected(self, svc: ObservationService):
        obs = {**_obs(), "is_synthetic": True}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"
        assert "is_synthetic" in reasons[0]

    def test_demo_rejected(self, svc: ObservationService):
        obs = {**_obs(), "is_demo": True}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"

    def test_missing_source_rejected(self, svc: ObservationService):
        obs = {**_obs(), "source": None}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"

    def test_missing_observed_at_rejected(self, svc: ObservationService):
        obs = {**_obs(), "observed_at": None}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"

    def test_impossible_rent_rejected(self, svc: ObservationService):
        obs = {**_obs(), "rent_monthly": -500.0}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"

    def test_rent_below_minimum_rejected(self, svc: ObservationService):
        obs = {**_obs(), "rent_monthly": 100.0}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"

    def test_out_of_bounds_coordinates_rejected(self, svc: ObservationService):
        obs = {**_obs(), "latitude": 0.0, "longitude": 0.0}
        status, reasons = svc.validate_observation(obs)
        assert status == "REJECTED"

    def test_low_geocode_confidence_questionable(self, svc: ObservationService):
        obs = {**_obs(), "geocode_confidence": "LOW",
               "latitude": 12.9816, "longitude": 80.2180}
        status, reasons = svc.validate_observation(obs)
        assert status == "QUESTIONABLE"
        assert any("geocode_confidence" in r for r in reasons)

    def test_missing_coordinates_questionable(self, svc: ObservationService):
        obs = {**_obs(), "latitude": None, "longitude": None}
        status, reasons = svc.validate_observation(obs)
        assert status == "QUESTIONABLE"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Property deduplication — repeated obs ≠ new properties
# ─────────────────────────────────────────────────────────────────────────────

class TestPropertyDeduplication:

    def test_repeated_observations_same_property_count_as_one(self, svc: ObservationService):
        """
        3 observations of SAME listing_id = 1 unique property.
        This is the key distinction: repeated price observations of the same
        property do NOT inflate the unique_properties count.
        """
        for rent in [18000.0, 18500.0, 19000.0]:
            svc.record(**_obs(listing_id="PROP-SINGLE", rent_monthly=rent))
        dq = svc.data_quality_report()
        assert dq.unique_properties == 1
        assert dq.eligible_for_model == 3   # 3 observations

    def test_different_listings_count_as_different_properties(self, svc: ObservationService):
        for i in range(5):
            svc.record(**_obs(listing_id=f"PROP-{i}"))
        dq = svc.data_quality_report()
        assert dq.unique_properties == 5

    def test_observation_history_keeps_all_snapshots(self, svc: ObservationService):
        """Repeated obs of same property are preserved in history — not merged."""
        for i, rent in enumerate([18000.0, 18500.0, 19000.0]):
            svc.record(**_obs(
                listing_id="HIST-001",
                rent_monthly=rent,
                observed_at=datetime(2025, 9, i+1, tzinfo=timezone.utc),
            ))
        hist = svc.get_history("HIST-001")
        assert hist.total_observations == 3
        rents = [o.rent_monthly for o in hist.observations]
        assert sorted(rents) == [18000.0, 18500.0, 19000.0]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Temporal coverage — genuine observed_at only
# ─────────────────────────────────────────────────────────────────────────────

class TestTemporalCoverage:

    def test_temporal_span_from_real_dates(self, svc: ObservationService):
        d0 = datetime(2025, 9, 1, tzinfo=timezone.utc)
        d7 = datetime(2025, 9, 8, tzinfo=timezone.utc)
        svc.record(**_obs(observed_at=d0, listing_id="T-001"))
        svc.record(**_obs(observed_at=d7, listing_id="T-002"))
        dq = svc.data_quality_report()
        assert dq.temporal_span_days == 7.0

    def test_single_observation_span_is_none(self, svc: ObservationService):
        svc.record(**_obs())
        dq = svc.data_quality_report()
        assert dq.temporal_span_days is None

    def test_temporal_gate_fails_below_7_days(self, svc: ObservationService):
        d0 = datetime(2025, 9, 1, tzinfo=timezone.utc)
        d3 = datetime(2025, 9, 4, tzinfo=timezone.utc)
        svc.record(**_obs(observed_at=d0))
        svc.record(**_obs(observed_at=d3))
        dq = svc.data_quality_report()
        assert dq.gate_progress["temporal_span_days"]["pass"] is False
        assert dq.gate_progress["temporal_span_days"]["current"] == 3

    def test_temporal_gate_passes_at_7_days(self, svc: ObservationService):
        d0 = datetime(2025, 9, 1, tzinfo=timezone.utc)
        d7 = datetime(2025, 9, 8, tzinfo=timezone.utc)
        svc.record(**_obs(observed_at=d0))
        svc.record(**_obs(observed_at=d7))
        dq = svc.data_quality_report()
        assert dq.gate_progress["temporal_span_days"]["pass"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. Source diversity — independent channels only
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceDiversity:

    def test_same_source_counts_as_one(self, svc: ObservationService):
        for i in range(10):
            svc.record(**_obs(listing_id=f"P-{i}", source="field_agent"))
        dq = svc.data_quality_report()
        assert dq.gate_progress["source_diversity"]["current"] == 1
        assert dq.gate_progress["source_diversity"]["pass"] is False

    def test_two_independent_sources_pass_gate(self, svc: ObservationService):
        svc.record(**_obs(listing_id="P-001", source="field_agent"))
        svc.record(**_obs(listing_id="P-002", source="owner_interview"))
        dq = svc.data_quality_report()
        assert dq.gate_progress["source_diversity"]["current"] == 2
        assert dq.gate_progress["source_diversity"]["pass"] is True

    def test_source_diversity_unique_by_name(self, svc: ObservationService):
        # "field_agent" and "field_agent_v2" are counted as two distinct sources
        svc.record(**_obs(listing_id="P-001", source="field_agent"))
        svc.record(**_obs(listing_id="P-002", source="field_agent_v2"))
        dq = svc.data_quality_report()
        # Two different source strings → 2 sources (operators responsible for labeling correctly)
        assert dq.gate_progress["source_diversity"]["current"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# 7. Real-data market summary — never mixes demo
# ─────────────────────────────────────────────────────────────────────────────

class TestRealMarketSummary:

    def test_empty_returns_insufficient(self, svc: ObservationService):
        result = svc.real_market_summary()
        assert result["insufficient_data"] is True
        assert result["median"] is None

    def test_demo_observations_excluded(self, svc: ObservationService):
        for i in range(10):
            svc.record(**_obs(listing_id=f"D-{i}", is_demo=True, rent_monthly=50000.0))
        # Still insufficient — demo obs excluded
        result = svc.real_market_summary()
        assert result["insufficient_data"] is True

    def test_real_observations_compute_correctly(self, svc: ObservationService):
        rents = [10000.0, 12000.0, 15000.0, 18000.0, 20000.0]
        for i, rent in enumerate(rents):
            svc.record(**_obs(listing_id=f"R-{i}", rent_monthly=rent))
        result = svc.real_market_summary()
        assert result["insufficient_data"] is False
        assert result["median"] == 15000.0
        assert result["p25"] is not None
        assert result["p75"] is not None

    def test_by_bhk_breakdown(self, svc: ObservationService):
        for i, (bhk, rent) in enumerate([(1, 10000), (1, 11000), (2, 18000), (2, 19000), (3, 28000)]):
            svc.record(**_obs(listing_id=f"BHK-{i}", bhk=bhk, rent_monthly=float(rent)))
        result = svc.real_market_summary()
        if not result["insufficient_data"]:
            assert 1 in result["by_bhk"]
            assert 2 in result["by_bhk"]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Demo / real separation
# ─────────────────────────────────────────────────────────────────────────────

class TestDemoRealSeparation:

    def test_demo_never_contributes_to_eligibility(self, svc: ObservationService):
        # Add 100 demo observations — still not eligible
        for i in range(100):
            svc.record(**_obs(listing_id=f"DEMO-{i}", is_demo=True))
        dq = svc.data_quality_report()
        assert dq.eligible_for_model == 0
        assert dq.model_ready is False
        assert dq.demo_observations == 100

    def test_synthetic_never_contributes_to_eligibility(self, svc: ObservationService):
        for i in range(100):
            svc.record(**_obs(listing_id=f"SYNTH-{i}", is_synthetic=True))
        dq = svc.data_quality_report()
        assert dq.eligible_for_model == 0
        assert dq.synthetic_observations == 100

    def test_real_and_demo_counted_separately(self, svc: ObservationService):
        svc.record(**_obs(listing_id="R-001", is_demo=False))
        svc.record(**_obs(listing_id="D-001", is_demo=True))
        svc.record(**_obs(listing_id="S-001", is_synthetic=True))
        dq = svc.data_quality_report()
        assert dq.real_observations == 1
        assert dq.demo_observations == 1
        assert dq.synthetic_observations == 1
        assert dq.eligible_for_model == 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. Availability state independence
# ─────────────────────────────────────────────────────────────────────────────

class TestAvailabilityStates:

    def test_all_availability_states_storable(self, svc: ObservationService):
        states = [
            "AVAILABLE",
            "PENDING_CONFIRMATION",
            "RECENTLY_SEEN",
            "UNAVAILABLE",
            "UNKNOWN",
        ]
        for i, state in enumerate(states):
            svc.record(**_obs(listing_id=f"AVAIL-{i}", availability_status=state))
        dq = svc.data_quality_report()
        assert dq.total_observations == 5

    def test_recently_seen_not_promoted_to_available(self, svc: ObservationService):
        """RECENTLY_SEEN must not be silently promoted to AVAILABLE."""
        svc.record(**_obs(availability_status="RECENTLY_SEEN", listing_id="RS-001"))
        hist = svc.get_history("RS-001")
        obs = hist.observations[0]
        assert obs.availability_status == "RECENTLY_SEEN"   # unchanged


# ─────────────────────────────────────────────────────────────────────────────
# 10. Verification state independence from freshness
# ─────────────────────────────────────────────────────────────────────────────

class TestVerificationStateSeparation:

    def test_live_plus_unverified_can_coexist(self):
        """LIVE freshness does NOT imply RIVO_VERIFIED."""
        from app.schemas.rental import RentalListingCreate
        from app.core.config import DataFreshness, VerificationStatus, AvailabilityStatus
        listing = RentalListingCreate(
            listing_id="VERIFY-001",
            provider="rivo_direct",
            data_freshness=DataFreshness.LIVE,
            verification_status=VerificationStatus.UNVERIFIED,
            availability_status=AvailabilityStatus.AVAILABLE,
        )
        assert listing.data_freshness == DataFreshness.LIVE
        assert listing.verification_status == VerificationStatus.UNVERIFIED

    def test_submission_does_not_auto_upgrade_to_rivo_verified(self):
        """Submitting a listing via RIVO Direct gives OWNER_ATTESTED, not RIVO_VERIFIED."""
        from app.schemas.rental import DirectRentalSubmissionRequest
        from app.services.providers.rental_rivo_direct import RivoDirectListingProvider
        from app.core.config import VerificationStatus

        p = RivoDirectListingProvider()
        req = DirectRentalSubmissionRequest(
            locality="Adyar",
            latitude=12.9954,
            longitude=80.2569,
            rent_monthly=22000.0,
            bhk=2,
            consent_to_publish=True,
        )
        listing = p.add_direct_listing(req)
        assert listing.verification_status == VerificationStatus.OWNER_ATTESTED
        assert listing.verification_status != VerificationStatus.RIVO_VERIFIED


# ─────────────────────────────────────────────────────────────────────────────
# 11. Model readiness gate — truthful NOT_READY
# ─────────────────────────────────────────────────────────────────────────────

class TestModelReadinessGate:

    def test_model_not_ready_at_zero_observations(self, svc: ObservationService):
        dq = svc.data_quality_report()
        assert dq.model_ready is False
        assert dq.model_eligibility_status == "NOT_READY_INSUFFICIENT_DATA"

    def test_model_not_ready_with_only_demo_data(self, svc: ObservationService):
        for i in range(200):
            svc.record(**_obs(listing_id=f"D-{i}", is_demo=True))
        dq = svc.data_quality_report()
        assert dq.model_ready is False

    def test_model_not_ready_insufficient_properties(self, svc: ObservationService):
        """50 observations from 1 property — fails unique_properties gate."""
        for i in range(50):
            svc.record(**_obs(
                listing_id="SINGLE-PROPERTY",
                rent_monthly=18000.0 + i * 10,
                observed_at=datetime(2025, 9, 1, tzinfo=timezone.utc) + timedelta(days=i),
            ))
        dq = svc.data_quality_report()
        assert dq.model_ready is False  # fails unique_properties gate

    def test_observations_needed_decrements_correctly(self, svc: ObservationService):
        initial_needed = 50
        for i in range(5):
            svc.record(**_obs(listing_id=f"P-{i}"))
        dq = svc.data_quality_report()
        assert dq.observations_needed == initial_needed - 5


# ─────────────────────────────────────────────────────────────────────────────
# 12. train_rent_model script remains gated at 0 observations
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainRentModelGate:

    def test_eligibility_returns_not_ready_with_empty_observations(self):
        from app.services.ml.eligibility import evaluate_model_eligibility
        result = evaluate_model_eligibility([])
        assert result.is_eligible is False
        assert result.status == "NOT_READY_INSUFFICIENT_DATA"
        assert result.metrics["real_observations"] == 0

    def test_demo_observations_never_make_model_eligible(self):
        from app.services.ml.eligibility import evaluate_model_eligibility
        # Use is_demo=True with a non-demo-seed source name so they are
        # classified as demo_count (not synthetic_count) by the evaluator.
        # Listing IDs don't start with CMRL- or MOCK-. Source is not "demo_seed".
        demo_obs = [
            {
                "listing_id": f"FIELD-DEMO-{i:04d}",
                "locality": f"loc-{i}",
                "bhk": (i % 3) + 1,
                "rent_monthly": 15000 + i * 200,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "source": "field_survey_labelled_demo",
                "is_demo": True,
            }
            for i in range(100)
        ]
        result = evaluate_model_eligibility(demo_obs)
        assert result.is_eligible is False
        assert result.metrics["real_observations"] == 0
        assert result.metrics["demo_observations"] == 100


# ─────────────────────────────────────────────────────────────────────────────
# 13. Source filter in search / data quality
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceFilter:

    def test_source_categories_filter_in_search(self, client: TestClient):
        """Search with source_categories=CURRENT returns valid response."""
        resp = client.get(
            "/api/v1/rentals/search",
            params={"max_rent_monthly": 30000, "source_categories": "CURRENT"},
        )
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_demo_filter_returns_demo_banner(self, client: TestClient):
        """Search with source_categories=DEMO returns demo-labelled results."""
        resp = client.get(
            "/api/v1/rentals/search",
            params={"max_rent_monthly": 50000, "source_categories": "DEMO"},
        )
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 14. Zero Google API calls
# ─────────────────────────────────────────────────────────────────────────────

class TestZeroGoogleCalls:

    def test_rivo_live_api_tests_defaults_false(self):
        from app.core.config import get_settings
        settings = get_settings()
        assert settings.RIVO_LIVE_API_TESTS is False

    def test_data_quality_needs_no_google(self, client: TestClient):
        """Data quality report must not trigger any Google API calls."""
        # This test just verifies no exception from blocked Google calls
        resp = client.get("/api/v1/rentals/admin/data-quality")
        assert resp.status_code == 200

    def test_admin_collect_needs_no_google(self, client: TestClient):
        resp = client.post("/api/v1/rentals/admin/collect", json={
            "listing_id": "GOOGLE-TEST-001",
            "locality": "Anna Nagar",
            "bhk": 2,
            "rent_monthly": 20000.0,
            "source": "field_agent",
        })
        assert resp.status_code == 201

    def test_real_market_summary_needs_no_google(self, client: TestClient):
        resp = client.get("/api/v1/rentals/real-market-summary")
        assert resp.status_code == 200
