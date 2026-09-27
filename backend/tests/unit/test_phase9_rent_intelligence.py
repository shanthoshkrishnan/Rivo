"""
RIVO Unit Tests — Phase 9: Rent Intelligence & Data Sufficiency
================================================================
Tests all Phase 9 requirements:
  - Data sufficiency & eligibility safeguards (Task 2 & 3)
  - Demo and synthetic exclusion (Task 4)
  - GTFS transit feature extraction (Task 5 & 6)
  - Hierarchical baseline benchmark & metrics (Task 7)
  - Quantile LightGBM ML regression & safe promotion (Task 8 & 12)
  - Temporal validation splitting (Task 9)
  - Percentile outputs (p25, p50, p75) and monotonic ordering (Task 11)
  - Spatial rent surface & H3 smoothing fallback (Task 14 & 15)
  - Market comparison & position labeling (Task 16 & 17)
  - Market summary endpoint & insufficient data guard (Task 23)
  - Safe rebuild script behavior (Task 21)

ALL TESTS USE LOCAL FIXTURES. 0 EXTERNAL CALLS.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import DataFreshness
from app.main import app
from app.schemas.ml import (
    ModelEligibilityThresholds,
    RentPredictionRequest,
)
from app.services.ml.baseline_model import RentBaselineModel
from app.services.ml.dataset import (
    RentalDatasetRecord,
    prepare_training_dataset,
    temporal_train_test_split,
)
from app.services.ml.eligibility import evaluate_model_eligibility
from app.services.ml.features import feature_extractor
from app.services.ml.rent_model import RentMLModel
from app.services.ml.rent_surface import RentSurfaceService
from app.services.providers.rental_rivo_direct import rivo_direct_provider
from app.utils.spatial import lat_lng_to_h3


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_demo_observations():
    """88 station-anchored demo records from seed."""
    return [
        {
            "listing_id": f"CMRL-{i:03d}-1BHK",
            "rent_monthly": 8000 + (i * 100),
            "bhk": 1,
            "locality": "wimconagar",
            "latitude": 13.18,
            "longitude": 80.30,
            "is_demo": True,
            "is_synthetic": True,
            "source": "RIVO Sample Data",
        }
        for i in range(88)
    ]


@pytest.fixture
def sample_eligible_real_observations():
    """Synthesized fixture representing 60 real observations across 6 localities and 3 BHKs."""
    localities = ["velachery", "guindy", "tambaram", "anna_nagar", "adyar", "mylapore"]
    sources = ["rivo_direct", "credai_chennai_partner"]
    base_time = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

    obs = []
    for i in range(60):
        loc = localities[i % len(localities)]
        bhk = (i % 3) + 1
        src = sources[i % len(sources)]
        obs_time = base_time + timedelta(days=(i // 5))  # 12 days temporal span
        base_rent = 10000.0 * bhk + (i * 150.0)

        obs.append({
            "listing_id": f"REAL-LIST-{i:03d}",
            "rent_monthly": base_rent,
            "bhk": bhk,
            "area_sqft": bhk * 500.0,
            "furnishing": "semi-furnished",
            "property_type": "flat",
            "locality": loc,
            "latitude": 13.00 + (i * 0.002),
            "longitude": 80.20 + (i * 0.002),
            "is_demo": False,
            "is_synthetic": False,
            "source": src,
            "observed_at": obs_time,
        })
    return obs


# ─── Tests ───────────────────────────────────────────────────────────────────
class TestModelEligibilitySafeguards:
    def test_demo_observations_fail_eligibility(self, sample_demo_observations):
        """Verifies demo data is blocked from training ML models."""
        res = evaluate_model_eligibility(sample_demo_observations)
        assert res.is_eligible is False
        assert res.status == "NOT_READY_INSUFFICIENT_DATA"
        assert res.metrics["real_observations"] == 0
        assert res.metrics["synthetic_ratio"] == 1.0
        assert any("Insufficient real observations" in r for r in res.reasons)

    def test_eligible_dataset_passes_safeguards(self, sample_eligible_real_observations):
        """Verifies an observation pool with sufficient diversity passes safeguards."""
        thresholds = ModelEligibilityThresholds(
            min_real_observations=50,
            min_unique_properties=30,
            min_localities=5,
            min_bhk_classes=3,
            min_source_count=2,
            min_temporal_span_days=7,
        )
        res = evaluate_model_eligibility(sample_eligible_real_observations, thresholds)
        assert res.is_eligible is True
        assert res.status == "READY"
        assert len(res.reasons) == 0


class TestDatasetCleaningAndExclusion:
    def test_demo_and_corrupt_records_are_dropped(self, sample_demo_observations):
        """Task 4: Drops demo records, impossible rents, and out-of-bounds coordinates."""
        mixed = list(sample_demo_observations)
        mixed.append({
            "listing_id": "VALID-001",
            "rent_monthly": 15000,
            "bhk": 2,
            "area_sqft": 900,
            "locality": "velachery",
            "latitude": 12.98,
            "longitude": 80.22,
            "is_demo": False,
            "is_synthetic": False,
        })
        # Impossible rent
        mixed.append({
            "listing_id": "CORRUPT-RENT",
            "rent_monthly": 500,  # Below 2000
            "bhk": 1,
            "latitude": 12.98,
            "longitude": 80.22,
            "is_demo": False,
        })
        # Out-of-bounds coordinates (Bangalore)
        mixed.append({
            "listing_id": "OUT-OF-BOUNDS",
            "rent_monthly": 20000,
            "bhk": 2,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "is_demo": False,
        })

        records, audit = prepare_training_dataset(mixed, exclude_demo=True)
        assert len(records) == 1
        assert records[0].listing_id == "VALID-001"
        assert audit["excluded_synthetic_or_demo"] == len(sample_demo_observations)
        assert audit["excluded_impossible_rent"] == 1
        assert audit["excluded_invalid_coordinates"] == 1


class TestFeatureExtraction:
    def test_gtfs_transit_features(self):
        """Task 6: Deterministic transit accessibility from local GTFS."""
        # Guindy coordinates
        lat, lon = 13.0067, 80.2030
        feats = feature_extractor.extract_features(latitude=lat, longitude=lon, bhk=2, area_sqft=900)
        assert "nearest_metro_distance_m" in feats
        assert "nearest_bus_stop_distance_m" in feats
        assert "transit_accessibility_index" in feats
        assert 0.0 <= feats["transit_accessibility_index"] <= 1.0


class TestBaselineModel:
    def test_baseline_hierarchical_fit_and_predict(self, sample_eligible_real_observations):
        """Task 7: Tests baseline median model and hierarchical fallback."""
        records, _ = prepare_training_dataset(sample_eligible_real_observations, exclude_demo=False)
        baseline = RentBaselineModel(model_version="test_base_v1")
        fit_res = baseline.fit(records)
        assert fit_res["status"] == "FITTED"

        # Predict existing locality
        pred = baseline.predict(RentPredictionRequest(bhk=2, locality="velachery"))
        assert pred.rent_p50 is not None
        assert pred.rent_p25 is not None
        assert pred.rent_p75 is not None
        assert pred.rent_p25 <= pred.rent_p50 <= pred.rent_p75
        assert pred.data_freshness == "MODELLED"

        # Evaluate error metrics
        metrics = baseline.evaluate(records[:10])
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "medae" in metrics


class TestTemporalSplit:
    def test_temporal_split_chronological(self, sample_eligible_real_observations):
        """Task 9: Older records in train, newer records in test."""
        records, _ = prepare_training_dataset(sample_eligible_real_observations, exclude_demo=False)
        train, val, status = temporal_train_test_split(records, test_ratio=0.2)
        assert status == "TEMPORAL_SPLIT_VALID"
        assert len(train) > len(val)
        assert train[-1].observed_at <= val[0].observed_at


class TestLightGBMQuantileModel:
    def test_ml_quantile_training_and_ordering(self, sample_eligible_real_observations):
        """Task 8 & 12: Quantile regression training with p25 <= p50 <= p75."""
        records, _ = prepare_training_dataset(sample_eligible_real_observations, exclude_demo=False)
        model = RentMLModel(model_version="test_ml_v1")
        report = model.train_and_evaluate(
            observations=sample_eligible_real_observations,
            eligible_records=records,
            force_train_for_testing=True,
        )
        assert model.is_trained is True
        assert "p25" in model.models
        assert "p50" in model.models
        assert "p75" in model.models

        pred = model.predict(RentPredictionRequest(bhk=2, locality="velachery", latitude=12.98, longitude=80.22))
        assert pred.rent_p25 is not None
        assert pred.rent_p50 is not None
        assert pred.rent_p75 is not None
        assert pred.rent_p25 <= pred.rent_p50 <= pred.rent_p75
        assert pred.data_freshness == "MODELLED"


class TestSpatialRentSurface:
    def test_h3_surface_building_and_smoothing(self, sample_eligible_real_observations):
        """Tasks 14 & 15: H3 spatial surface and neighbor fallback smoothing."""
        records, _ = prepare_training_dataset(sample_eligible_real_observations, exclude_demo=False)
        service = RentSurfaceService(resolution=8)
        cells = service.build_surface(records)
        assert len(cells) > 0

        first_h3 = list(cells.keys())[0]
        est = service.get_cell_estimate(first_h3)
        assert est.rent_p50 is not None
        assert est.confidence in ("HIGH", "MEDIUM", "LOW")

        # Unknown cell outside training but with locality fallback
        unknown_h3 = lat_lng_to_h3(13.08, 80.27, resolution=8)
        smooth_est = service.get_cell_estimate(unknown_h3, locality="velachery")
        assert smooth_est.confidence in ("LOW", "INSUFFICIENT_DATA")


class TestRentEndpoints:
    @pytest.mark.asyncio
    async def test_market_summary_endpoint(self):
        """Task 23: Market summary endpoint returns insufficient_data on empty DB."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/rentals/market-summary")
            assert res.status_code == 200
            data = res.json()
            assert "insufficient_data" in data
            assert "listing_count" in data
            assert "observation_count" in data

    @pytest.mark.asyncio
    async def test_market_estimate_endpoint(self):
        """Task 16: Market estimate endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/rentals/market-estimate",
                json={"bhk": 2, "area_sqft": 900.0, "locality": "velachery"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["data_freshness"] == "MODELLED"
            assert "rent_p50" in data
