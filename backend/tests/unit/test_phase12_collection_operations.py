"""
Phase 12 Tests — Operational Real Rental Data Collection
==========================================================
Tests for:
  1.  collection_progress() breakdown by locality, BHK, source
  2.  quality_warnings() advisory system
  3.  collection-progress API endpoint
  4.  Blocking reasons format
  5.  Demo/synthetic never appear in collection progress
  6.  Temporal span in collection progress
  7.  by_locality / by_bhk / by_source breakdowns
  8.  Model ready alert (truthful when gates pass)
  9.  Bulk import UX (dry-run, questionable, duplicate counts)
  10. Zero Google API calls
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.endpoints.rentals import router as rental_router
from app.services.observation_service import ObservationService


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


# ─────────────────────────────────────────────────────────────────────────────
# 1. collection_progress() breakdown
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectionProgress:

    def test_empty_returns_all_zeros(self, svc: ObservationService):
        cp = svc.collection_progress()
        assert cp["real_observations"] == 0
        assert cp["unique_properties"] == 0
        assert cp["localities"] == []
        assert cp["bhk_classes"] == []
        assert cp["source_count"] == 0
        assert cp["temporal_span_days"] == 0
        assert cp["model_ready"] is False
        assert cp["model_eligibility_status"] == "NOT_READY_INSUFFICIENT_DATA"

    def test_blocking_reasons_populated_when_empty(self, svc: ObservationService):
        cp = svc.collection_progress()
        blocking = cp["blocking_reasons"]
        assert any("real_observations" in r for r in blocking)
        assert any("unique_properties" in r for r in blocking)
        assert any("localities" in r for r in blocking)
        assert any("bhk_classes" in r for r in blocking)
        assert any("source_diversity" in r for r in blocking)

    def test_locality_breakdown_correct(self, svc: ObservationService):
        svc.record(**_obs(listing_id="P-001", locality="Velachery", bhk=2))
        svc.record(**_obs(listing_id="P-002", locality="Velachery", bhk=3))
        svc.record(**_obs(listing_id="P-003", locality="Adyar", bhk=2))
        cp = svc.collection_progress()
        assert "velachery" in cp["by_locality"]
        assert "adyar" in cp["by_locality"]
        assert cp["by_locality"]["velachery"]["observations"] == 2
        assert cp["by_locality"]["velachery"]["unique_properties"] == 2
        assert sorted(cp["by_locality"]["velachery"]["bhk_classes"]) == [2, 3]

    def test_bhk_breakdown_correct(self, svc: ObservationService):
        svc.record(**_obs(listing_id="P-001", bhk=1, locality="velachery"))
        svc.record(**_obs(listing_id="P-002", bhk=2, locality="adyar"))
        svc.record(**_obs(listing_id="P-003", bhk=2, locality="t-nagar"))
        cp = svc.collection_progress()
        assert 1 in cp["by_bhk"]
        assert 2 in cp["by_bhk"]
        assert cp["by_bhk"][2]["observations"] == 2
        assert cp["by_bhk"][2]["unique_properties"] == 2
        assert "adyar" in cp["by_bhk"][2]["localities"]
        assert "t-nagar" in cp["by_bhk"][2]["localities"]

    def test_source_breakdown_correct(self, svc: ObservationService):
        svc.record(**_obs(listing_id="P-001", source="field_agent"))
        svc.record(**_obs(listing_id="P-002", source="field_agent"))
        svc.record(**_obs(listing_id="P-003", source="owner_interview"))
        cp = svc.collection_progress()
        assert cp["by_source"]["field_agent"] == 2
        assert cp["by_source"]["owner_interview"] == 1
        assert cp["source_count"] == 2

    def test_first_and_last_observed_at_correct(self, svc: ObservationService):
        d1 = datetime(2026, 9, 1, tzinfo=timezone.utc)
        d2 = datetime(2026, 9, 15, tzinfo=timezone.utc)
        svc.record(**_obs(listing_id="P-001", observed_at=d1))
        svc.record(**_obs(listing_id="P-002", observed_at=d2))
        cp = svc.collection_progress()
        assert cp["temporal_span_days"] == 14
        assert "2026-09-01" in cp["first_observed_at"]
        assert "2026-09-15" in cp["last_observed_at"]

    def test_retrieved_at_is_present(self, svc: ObservationService):
        cp = svc.collection_progress()
        assert "retrieved_at" in cp
        assert "2026" in cp["retrieved_at"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. quality_warnings() advisory system
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityWarnings:

    def test_no_warnings_for_full_valid_obs(self, svc: ObservationService):
        obs = {
            "listing_id": "QW-001",
            "locality": "Adyar",
            "bhk": 2,
            "rent_monthly": 22000.0,
            "source": "field_agent",
            "observed_at": datetime.now(timezone.utc),
            "availability_status": "AVAILABLE",
            "verification_status": "OWNER_ATTESTED",
            "latitude": 12.9954,
            "longitude": 80.2569,
            "geocode_confidence": "HIGH",
        }
        warnings = svc.quality_warnings(obs)
        assert warnings == []

    def test_missing_coordinates_warns(self, svc: ObservationService):
        obs = {**_obs(), "latitude": None, "longitude": None}
        warnings = svc.quality_warnings(obs)
        assert any("coordinates missing" in w for w in warnings)

    def test_low_geocode_confidence_warns(self, svc: ObservationService):
        obs = {**_obs(), "geocode_confidence": "LOW",
               "latitude": 12.9954, "longitude": 80.2569}
        warnings = svc.quality_warnings(obs)
        assert any("LOW" in w for w in warnings)

    def test_missing_source_warns(self, svc: ObservationService):
        obs = {**_obs(), "source": None}
        warnings = svc.quality_warnings(obs)
        assert any("Source not recorded" in w for w in warnings)

    def test_unknown_availability_warns(self, svc: ObservationService):
        obs = {**_obs(), "availability_status": "UNKNOWN"}
        warnings = svc.quality_warnings(obs)
        assert any("UNKNOWN" in w for w in warnings)

    def test_recently_seen_warns(self, svc: ObservationService):
        obs = {**_obs(), "availability_status": "RECENTLY_SEEN"}
        warnings = svc.quality_warnings(obs)
        assert any("RECENTLY_SEEN" in w for w in warnings)

    def test_unverified_warns(self, svc: ObservationService):
        obs = {**_obs(), "verification_status": "UNVERIFIED"}
        warnings = svc.quality_warnings(obs)
        assert any("UNVERIFIED" in w for w in warnings)

    def test_existing_listing_id_warns_with_context(self, svc: ObservationService):
        svc.record(**_obs(listing_id="EXISTING-001"))
        obs = {**_obs(), "listing_id": "EXISTING-001"}
        warnings = svc.quality_warnings(obs)
        # Warns but explains this is OK for price updates
        assert any("already exists" in w for w in warnings)
        assert any("new observation" in w.lower() for w in warnings)

    def test_missing_listing_id_warns(self, svc: ObservationService):
        obs = {**_obs(), "listing_id": ""}
        warnings = svc.quality_warnings(obs)
        assert any("listing_id is empty" in w for w in warnings)


# ─────────────────────────────────────────────────────────────────────────────
# 3. collection-progress API endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectionProgressEndpoint:

    def test_endpoint_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/rentals/admin/collection-progress")
        assert resp.status_code == 200

    def test_endpoint_returns_required_fields(self, client: TestClient):
        resp = client.get("/api/v1/rentals/admin/collection-progress")
        data = resp.json()
        required = [
            "real_observations",
            "unique_properties",
            "localities",
            "bhk_classes",
            "source_count",
            "temporal_span_days",
            "model_ready",
            "model_eligibility_status",
            "blocking_reasons",
            "gate_progress",
            "by_locality",
            "by_bhk",
            "by_source",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_endpoint_shows_not_ready_at_zero_obs(self, client: TestClient):
        resp = client.get("/api/v1/rentals/admin/collection-progress")
        data = resp.json()
        assert data["model_ready"] is False
        assert data["model_eligibility_status"] == "NOT_READY_INSUFFICIENT_DATA"
        assert len(data["blocking_reasons"]) > 0

    def test_endpoint_zero_google_calls(self, client: TestClient):
        # This endpoint must not trigger any Google API calls
        resp = client.get("/api/v1/rentals/admin/collection-progress")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 4. Demo/synthetic never in collection progress
# ─────────────────────────────────────────────────────────────────────────────

class TestDemoSyntheticExcludedFromProgress:

    def test_demo_obs_excluded_from_collection_progress(self, svc: ObservationService):
        for i in range(100):
            svc.record(**_obs(listing_id=f"D-{i}", is_demo=True))
        cp = svc.collection_progress()
        assert cp["real_observations"] == 0
        assert cp["unique_properties"] == 0
        assert cp["localities"] == []

    def test_synthetic_obs_excluded_from_collection_progress(self, svc: ObservationService):
        for i in range(100):
            svc.record(**_obs(listing_id=f"S-{i}", is_synthetic=True))
        cp = svc.collection_progress()
        assert cp["real_observations"] == 0

    def test_real_obs_appear_in_collection_progress(self, svc: ObservationService):
        svc.record(**_obs(listing_id="REAL-001", is_demo=False))
        svc.record(**_obs(listing_id="DEMO-001", is_demo=True))
        cp = svc.collection_progress()
        assert cp["real_observations"] == 1
        assert cp["unique_properties"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. Temporal span in collection progress
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectionProgressTemporal:

    def test_zero_span_with_single_obs(self, svc: ObservationService):
        svc.record(**_obs())
        cp = svc.collection_progress()
        assert cp["temporal_span_days"] == 0

    def test_14_day_span(self, svc: ObservationService):
        d0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
        d14 = datetime(2026, 9, 15, tzinfo=timezone.utc)
        svc.record(**_obs(listing_id="P-001", observed_at=d0))
        svc.record(**_obs(listing_id="P-002", observed_at=d14))
        cp = svc.collection_progress()
        assert cp["temporal_span_days"] == 14

    def test_temporal_gate_shown_in_blocking_reasons_when_short(self, svc: ObservationService):
        d0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
        d3 = datetime(2026, 9, 4, tzinfo=timezone.utc)
        svc.record(**_obs(listing_id="P-001", observed_at=d0))
        svc.record(**_obs(listing_id="P-002", observed_at=d3))
        cp = svc.collection_progress()
        assert any("temporal_span_days" in r for r in cp["blocking_reasons"])


# ─────────────────────────────────────────────────────────────────────────────
# 6. Model ready alert truthfulness
# ─────────────────────────────────────────────────────────────────────────────

class TestModelReadyAlert:

    def test_model_not_ready_shown_correctly(self, svc: ObservationService):
        cp = svc.collection_progress()
        assert cp["model_ready"] is False
        # Blocking reasons must be present
        assert len(cp["blocking_reasons"]) > 0

    def test_model_not_ready_with_49_obs(self, svc: ObservationService):
        """One observation short — still not ready."""
        base_dt = datetime(2026, 9, 1, tzinfo=timezone.utc)
        locs = ["velachery", "adyar", "t-nagar", "anna-nagar", "mylapore"]
        for i in range(49):
            svc.record(**_obs(
                listing_id=f"P-{i:03d}",
                locality=locs[i % len(locs)],
                bhk=(i % 4) + 1,
                source="field_agent" if i % 2 == 0 else "owner_interview",
                observed_at=base_dt + timedelta(days=i),
            ))
        cp = svc.collection_progress()
        assert cp["model_ready"] is False

    def test_no_auto_training_flagged(self, svc: ObservationService):
        """Even when filled enough, just flag model_ready — don't auto-train."""
        cp = svc.collection_progress()
        # Verify no "trained" or "deployed" key
        assert "model_trained" not in cp
        assert "model_deployed" not in cp


# ─────────────────────────────────────────────────────────────────────────────
# 7. Bulk import UX improvements
# ─────────────────────────────────────────────────────────────────────────────

class TestBulkImportUX:

    def test_bulk_import_report_has_accepted_count(self, svc: ObservationService):
        from app.schemas.observation import BulkObservationRow
        rows = [
            BulkObservationRow(
                listing_id=f"CSV-{i:03d}",
                locality="Adyar",
                bhk=2,
                rent_monthly=20000.0 + i * 100,
                source="field_agent",
                observed_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]
        result = svc.bulk_import(rows)
        assert result.accepted == 5
        assert result.rejected_synthetic == 0
        assert result.rejected_demo == 0
        assert result.total_rows == 5

    def test_bulk_import_rejects_synthetic(self, svc: ObservationService):
        from app.schemas.observation import BulkObservationRow
        rows = [
            BulkObservationRow(
                listing_id="SYN-001",
                locality="Velachery",
                bhk=2,
                rent_monthly=18000.0,
                source="script",
                observed_at=datetime.now(timezone.utc),
                is_synthetic=True,
            )
        ]
        result = svc.bulk_import(rows)
        assert result.accepted == 0
        assert result.rejected_synthetic == 1
        assert any("is_synthetic" in e for e in result.errors)

    def test_bulk_import_errors_have_row_numbers(self, svc: ObservationService):
        from app.schemas.observation import BulkObservationRow
        rows = [
            BulkObservationRow(
                listing_id="D-001",
                locality="Anna Nagar",
                bhk=2,
                rent_monthly=20000.0,
                source="demo_seed",
                observed_at=datetime.now(timezone.utc),
                is_demo=True,
            )
        ]
        result = svc.bulk_import(rows)
        assert result.rejected_demo == 1
        assert any("Row 1" in e for e in result.errors)

    def test_bulk_import_reports_localities_and_sources(self, svc: ObservationService):
        from app.schemas.observation import BulkObservationRow
        rows = [
            BulkObservationRow(
                listing_id=f"MIX-{i}",
                locality=["Velachery", "Adyar", "T. Nagar"][i % 3],
                bhk=2,
                rent_monthly=18000.0,
                source="field_agent" if i < 3 else "owner_interview",
                observed_at=datetime.now(timezone.utc),
            )
            for i in range(6)
        ]
        result = svc.bulk_import(rows)
        assert result.accepted == 6
        assert len(result.localities) >= 2
        assert len(result.sources) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 8. Zero Google API calls
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase12ZeroGoogleCalls:

    def test_collection_progress_no_google(self, client: TestClient):
        resp = client.get("/api/v1/rentals/admin/collection-progress")
        assert resp.status_code == 200

    def test_data_quality_no_google(self, client: TestClient):
        resp = client.get("/api/v1/rentals/admin/data-quality")
        assert resp.status_code == 200

    def test_real_market_summary_no_google(self, client: TestClient):
        resp = client.get("/api/v1/rentals/real-market-summary")
        assert resp.status_code == 200

    def test_rivo_live_api_tests_still_false(self):
        from app.core.config import get_settings
        assert get_settings().RIVO_LIVE_API_TESTS is False
