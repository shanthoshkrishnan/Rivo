#!/usr/bin/env python3
"""
RIVO Backend — Rent Model Training & Rebuild Script
===================================================
Usage:
    python -m backend.scripts.train_rent_model
    # or from backend/:
    python scripts/train_rent_model.py

Workflow:
  1. Audits current database and in-memory rental observations
  2. Evaluates deterministic eligibility safeguards
  3. If eligible: prepares dataset, trains baseline, trains LightGBM, evaluates
  4. If ineligible: blocks training and reports "Insufficient real rental observations for ML training."
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.logging import configure_logging, logger
from app.models.rental import RentalObservation
from app.schemas.ml import ModelEligibilityThresholds
from app.services.ml.dataset import prepare_training_dataset
from app.services.ml.eligibility import evaluate_model_eligibility
from app.services.ml.rent_model import rent_ml_engine
from app.services.providers.rental_rivo_direct import rivo_direct_provider

configure_logging()


def main() -> int:
    print("=" * 60)
    print("RIVO RENT INTELLIGENCE — MODEL REBUILD PIPELINE")
    print("=" * 60)

    # 1. Collect all available empirical observations
    direct_obs = rivo_direct_provider.get_all_observations()

    # In production with PostgreSQL/SQLite, also query RentalObservation records
    all_observations = list(direct_obs)

    print(f"[*] Total empirical observations found: {len(all_observations)}")

    # 2. Check model eligibility safeguards
    thresholds = ModelEligibilityThresholds()
    result = evaluate_model_eligibility(all_observations, thresholds=thresholds)

    print(f"[*] Eligibility Status: {result.status}")
    print(f"[*] Real observations: {result.metrics.get('real_observations', 0)} / {thresholds.min_real_observations}")
    print(f"[*] Unique properties: {result.metrics.get('unique_properties', 0)} / {thresholds.min_unique_properties}")
    print(f"[*] Unique localities: {result.metrics.get('unique_localities', 0)} / {thresholds.min_localities}")
    print(f"[*] BHK classes:       {result.metrics.get('unique_bhks', 0)} / {thresholds.min_bhk_classes}")
    print(f"[*] Data sources:      {result.metrics.get('source_count', 0)} / {thresholds.min_source_count}")

    if not result.is_eligible:
        print("\n" + "!" * 60)
        print("SAFEGUARD BLOCKED: Insufficient real rental observations for ML training.")
        print("!" * 60)
        print("Reasons:")
        for r in result.reasons:
            print(f"  - {r}")
        print("\nModel pipeline remains safe and uncorrupted by synthetic data.")
        return 0

    # 3. Prepare dataset
    records, audit = prepare_training_dataset(all_observations, exclude_demo=True)
    print(f"\n[*] Cleaned training records: {len(records)}")

    # 4. Train & evaluate
    report = rent_ml_engine.train_and_evaluate(
        observations=all_observations,
        eligible_records=records,
        thresholds=thresholds,
    )

    print("\n[+] Training Complete:")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
