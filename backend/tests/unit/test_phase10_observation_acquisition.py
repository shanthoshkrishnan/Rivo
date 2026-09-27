"""
Phase 10 Tests — Real Rental Observation Acquisition & Data Collection System
==============================================================================
Tests for:
  1. PATCH /api/v1/rentals/direct/{listing_id}  — listing update + observation
  2. GET  /api/v1/rentals/{listing_id}/history  — observation history
  3. ObservationService admin collect           — eligibility enforcement
  4. ObservationService bulk import             — accept/reject logic
  5. Admin data quality report                  — metrics correctness
  6. CLI importer schema validation             — BulkObservationRow parsing
  7. Synthetic/demo safeguards                  — NEVER eligible_for_model
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.api.v1.endpoints.rentals import router as rental_router
from app.schemas.observation import (
    AdminCollectObservationRequest,
    AdminDataQualityReport,
    BulkObservationRow,
    DirectListingUpdateRequest,
    ObservationHistoryResponse,
)
from app.services.observation_service import ObservationService


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def obs_service() -> ObservationService:
    """Fresh ObservationService instance per test."""
    return ObservationService()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(rental_router, prefix="/api/v1")
    return app


@pytest.fixture
def test_client():
    return TestClient(_make_app())


def _real_observation_kwargs(**overrides) -> dict:
    base = {
        "listing_id": "RIVO-DIR-TEST001",
        "locality": "Velachery",
        "bhk": 2,
        "rent_monthly": 18000.0,
        "availability_status": "AVAILABLE",
        "source": "owner_interview",
        "is_synthetic": False,
        "is_demo": False,
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# 1. ObservationService: record + eligibility
# ─────────────────────────────────────────────────────────────────────────────

class TestObservationServiceRecord:

    def test_real_observation_is_eligible(self, obs_service: ObservationService):
        entry = obs_service.record(**_real_observation_kwargs())
        assert entry["eligible_for_model"] is True
        assert entry["is_synthetic"] is False
        assert entry["is_demo"] is False

    def test_synthetic_observation_never_eligible(self, obs_service: ObservationService):
        entry = obs_service.record(**_real_observation_kwargs(is_synthetic=True))
        assert entry["eligible_for_model"] is False

    def test_demo_observation_never_eligible(self, obs_service: ObservationService):
        entry = obs_service.record(**_real_observation_kwargs(is_demo=True))
        assert entry["eligible_for_model"] is False

    def test_multiple_observations_accumulate(self, obs_service: ObservationService):
        for i in range(5):
            obs_service.record(**_real_observation_kwargs(listing_id=f"LID-{i}"))
        assert len(obs_service.get_all()) == 5

    def test_changed_fields_recorded(self, obs_service: ObservationService):
        entry = obs_service.record(
            **_real_observation_kwargs(changed_fields=["rent_monthly"])
        )
        assert "rent_monthly" in entry["changed_fields"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. ObservationService: history
# ─────────────────────────────────────────────────────────────────────────────

class TestObservationHistory:

    def test_history_empty_for_unknown_listing(self, obs_service: ObservationService):
        hist = obs_service.get_history("UNKNOWN-ID")
        assert hist.total_observations == 0
        assert hist.observations == []

    def test_history_returns_sorted_by_time(self, obs_service: ObservationService):
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for i in range(3):
            obs_service.record(
                **_real_observation_kwargs(
                    listing_id="LID-HISTORY",
                    rent_monthly=15000 + i * 500,
                    observed_at=base_time + timedelta(days=i),
                )
            )
        hist = obs_service.get_history("LID-HISTORY")
        assert hist.total_observations == 3
        rents = [o.rent_monthly for o in hist.observations]
        assert rents == sorted(rents)   # chronological → rent ascends with our test data

    def test_history_eligible_count(self, obs_service: ObservationService):
        obs_service.record(**_real_observation_kwargs(listing_id="LID-ELIG"))       # real
        obs_service.record(**_real_observation_kwargs(listing_id="LID-ELIG", is_demo=True))  # demo
        hist = obs_service.get_history("LID-ELIG")
        assert hist.eligible_for_model_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. ObservationService: admin collect
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminCollect:

    def test_valid_admin_collect_accepted(self, obs_service: ObservationService):
        req = AdminCollectObservationRequest(
            listing_id="ADMIN-001",
            locality="Adyar",
            bhk=2,
            rent_monthly=22000.0,
            source="field_agent",
        )
        resp = obs_service.admin_collect(req)
        assert resp.accepted is True
        assert resp.eligible_for_model is True
        assert resp.observation_id != ""

    def test_admin_collect_rejects_synthetic(self, obs_service: ObservationService):
        req = AdminCollectObservationRequest(
            listing_id="ADMIN-SYNTH",
            locality="Adyar",
            bhk=2,
            rent_monthly=22000.0,
            source="test",
            is_synthetic=True,
        )
        resp = obs_service.admin_collect(req)
        assert resp.accepted is False
        assert resp.eligible_for_model is False

    def test_admin_collect_rejects_demo(self, obs_service: ObservationService):
        req = AdminCollectObservationRequest(
            listing_id="ADMIN-DEMO",
            locality="Adyar",
            bhk=2,
            rent_monthly=22000.0,
            source="test",
            is_demo=True,
        )
        resp = obs_service.admin_collect(req)
        assert resp.accepted is False

    def test_admin_collect_progressive_eligibility_counter(self, obs_service: ObservationService):
        """Each accepted admin observation should increment the eligible counter."""
        for i in range(5):
            req = AdminCollectObservationRequest(
                listing_id=f"ADMIN-{i:03d}",
                locality=f"Locality-{i}",
                bhk=2,
                rent_monthly=15000 + i * 1000,
                source="field_agent",
            )
            resp = obs_service.admin_collect(req)
            assert resp.total_eligible_observations == i + 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. ObservationService: bulk import
# ─────────────────────────────────────────────────────────────────────────────

class TestBulkImport:

    def _make_rows(self, count: int, **overrides) -> List[BulkObservationRow]:
        base = datetime(2025, 3, 1, tzinfo=timezone.utc)
        return [
            BulkObservationRow(
                listing_id=f"BULK-{i:04d}",
                locality=f"Locality-{i % 6}",
                bhk=(i % 3) + 1,
                rent_monthly=12000.0 + i * 200,
                observed_at=base + timedelta(days=i),
                source="verified_portal",
                **overrides,
            )
            for i in range(count)
        ]

    def test_clean_rows_all_accepted(self, obs_service: ObservationService):
        rows = self._make_rows(10)
        result = obs_service.bulk_import(rows)
        assert result.accepted == 10
        assert result.rejected_synthetic == 0
        assert result.rejected_demo == 0
        assert result.eligible_for_model == 10

    def test_synthetic_rows_are_rejected(self, obs_service: ObservationService):
        rows = self._make_rows(5, is_synthetic=True)
        result = obs_service.bulk_import(rows)
        assert result.accepted == 0
        assert result.rejected_synthetic == 5
        assert result.eligible_for_model == 0

    def test_demo_rows_are_rejected(self, obs_service: ObservationService):
        rows = self._make_rows(3, is_demo=True)
        result = obs_service.bulk_import(rows)
        assert result.accepted == 0
        assert result.rejected_demo == 3

    def test_mixed_rows_correct_split(self, obs_service: ObservationService):
        real_rows = self._make_rows(5)
        demo_rows = self._make_rows(3, is_demo=True)
        synth_rows = self._make_rows(2, is_synthetic=True)
        result = obs_service.bulk_import(real_rows + demo_rows + synth_rows)
        assert result.accepted == 5
        assert result.rejected_demo == 3
        assert result.rejected_synthetic == 2

    def test_sources_and_localities_populated(self, obs_service: ObservationService):
        rows = self._make_rows(6)
        result = obs_service.bulk_import(rows)
        assert "verified_portal" in result.sources
        assert len(result.localities) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. Admin data quality report
# ─────────────────────────────────────────────────────────────────────────────

class TestDataQualityReport:

    def test_empty_store_returns_zeros(self, obs_service: ObservationService):
        dq = obs_service.data_quality_report()
        assert dq.total_observations == 0
        assert dq.eligible_for_model == 0
        assert dq.model_ready is False
        assert dq.model_eligibility_status == "NOT_READY_INSUFFICIENT_DATA"
        assert dq.observations_needed == 50  # min threshold

    def test_demo_and_synth_not_counted_as_real(self, obs_service: ObservationService):
        obs_service.record(**_real_observation_kwargs(is_demo=True))
        obs_service.record(**_real_observation_kwargs(is_synthetic=True))
        dq = obs_service.data_quality_report()
        assert dq.real_observations == 0
        assert dq.demo_observations == 1
        assert dq.synthetic_observations == 1
        assert dq.eligible_for_model == 0

    def test_real_observations_contribute_to_count(self, obs_service: ObservationService):
        for i in range(10):
            obs_service.record(**_real_observation_kwargs(listing_id=f"LID-{i}"))
        dq = obs_service.data_quality_report()
        assert dq.real_observations == 10
        assert dq.eligible_for_model == 10
        assert dq.observations_needed == 40   # 50 - 10

    def test_model_not_ready_below_threshold(self, obs_service: ObservationService):
        for i in range(20):
            obs_service.record(**_real_observation_kwargs(listing_id=f"LID-{i}"))
        dq = obs_service.data_quality_report()
        assert dq.model_ready is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. BulkObservationRow schema validation
# ─────────────────────────────────────────────────────────────────────────────

class TestBulkObservationRowSchema:

    def test_valid_row_parses(self):
        row = BulkObservationRow(
            listing_id="TEST-001",
            locality="Anna Nagar",
            bhk=2,
            rent_monthly=20000.0,
            observed_at=datetime.now(timezone.utc),
            source="owner_interview",
        )
        assert row.is_synthetic is False
        assert row.is_demo is False
        assert row.listing_id == "TEST-001"
        assert row.bhk == 2

    def test_iso_string_observed_at_parsed(self):
        row = BulkObservationRow(
            listing_id="TEST-002",
            locality="T. Nagar",
            bhk=1,
            rent_monthly=12000.0,
            observed_at="2025-06-15T10:00:00+05:30",
            source="portal",
        )
        assert isinstance(row.observed_at, datetime)

    def test_utc_z_suffix_parsed(self):
        row = BulkObservationRow(
            listing_id="TEST-003",
            locality="Kodambakkam",
            bhk=3,
            rent_monthly=30000.0,
            observed_at="2025-08-01T00:00:00Z",
            source="portal",
        )
        assert row.observed_at.tzinfo is not None

    def test_invalid_rent_raises(self):
        with pytest.raises(Exception):
            BulkObservationRow(
                listing_id="TEST-BAD",
                locality="Anna Nagar",
                bhk=2,
                rent_monthly=-500.0,   # invalid
                observed_at=datetime.now(timezone.utc),
                source="test",
            )

    def test_bhk_out_of_range_raises(self):
        with pytest.raises(Exception):
            BulkObservationRow(
                listing_id="TEST-BAD",
                locality="Anna Nagar",
                bhk=99,   # > 10
                rent_monthly=15000.0,
                observed_at=datetime.now(timezone.utc),
                source="test",
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. API endpoint integration tests (FastAPI TestClient)
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase10APIEndpoints:
    """
    Integration tests via TestClient using a fresh app.
    """

    def test_admin_collect_endpoint_accepts_valid_payload(self, test_client: TestClient):
        payload = {
            "listing_id": "API-COLLECT-001",
            "locality": "Velachery",
            "bhk": 2,
            "rent_monthly": 18000.0,
            "source": "field_agent",
        }
        response = test_client.post("/api/v1/rentals/admin/collect", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["accepted"] is True
        assert data["eligible_for_model"] is True

    def test_admin_collect_endpoint_rejects_synthetic(self, test_client: TestClient):
        payload = {
            "listing_id": "API-SYNTH-001",
            "locality": "Velachery",
            "bhk": 2,
            "rent_monthly": 18000.0,
            "source": "test",
            "is_synthetic": True,
        }
        response = test_client.post("/api/v1/rentals/admin/collect", json=payload)
        assert response.status_code == 422

    def test_data_quality_endpoint_returns_structure(self, test_client: TestClient):
        response = test_client.get("/api/v1/rentals/admin/data-quality")
        assert response.status_code == 200
        data = response.json()
        assert "total_observations" in data
        assert "eligible_for_model" in data
        assert "model_eligibility_status" in data
        assert "observations_needed" in data

    def test_history_endpoint_empty_for_unknown(self, test_client: TestClient):
        response = test_client.get("/api/v1/rentals/UNKNOWN-9999/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total_observations"] == 0
        assert data["observations"] == []

    def test_patch_direct_listing_not_found(self, test_client: TestClient):
        payload = {"rent_monthly": 20000.0}
        response = test_client.patch(
            "/api/v1/rentals/direct/DOESNT-EXIST-9999", json=payload
        )
        assert response.status_code == 404

    def test_patch_direct_listing_flow(self, test_client: TestClient):
        """
        Full flow:
        1. POST /direct to create listing
        2. PATCH /direct/{id} to update rent
        3. GET /{id}/history to confirm observation recorded
        """
        # Step 1: Create listing
        create_payload = {
            "locality": "Velachery",
            "latitude": 12.9816,
            "longitude": 80.2180,
            "rent_monthly": 18000.0,
            "bhk": 2,
            "consent_to_publish": True,
        }
        create_resp = test_client.post("/api/v1/rentals/direct", json=create_payload)
        assert create_resp.status_code == 201
        listing_id = create_resp.json()["listing_id"]

        # Step 2: Update rent via PATCH
        patch_resp = test_client.patch(
            f"/api/v1/rentals/direct/{listing_id}",
            json={"rent_monthly": 20000.0},
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["updated_fields"] == ["rent_monthly"]
        assert patch_data["observation_recorded"] is True
        assert patch_data["current_rent"] == 20000.0

        # Step 3: Verify history
        hist_resp = test_client.get(f"/api/v1/rentals/{listing_id}/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        # At least one observation from the PATCH
        assert hist_data["total_observations"] >= 1
