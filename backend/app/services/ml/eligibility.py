"""
RIVO Backend — Rental Data Sufficiency & Model Eligibility Gate
===============================================================
Enforces strict engineering safeguards:
RIVO NEVER trains an ML model on demo, synthetic, or statistically
insufficient real-world observations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.ml import ModelEligibilityResult, ModelEligibilityThresholds


def evaluate_model_eligibility(
    observations: List[Dict[str, Any]],
    thresholds: Optional[ModelEligibilityThresholds] = None,
) -> ModelEligibilityResult:
    """
    Deterministically evaluates whether the current observation pool is eligible
    for statistical ML model training.
    """
    t = thresholds or ModelEligibilityThresholds()

    total_count = len(observations)
    real_obs: List[Dict[str, Any]] = []
    synthetic_count = 0
    demo_count = 0

    for obs in observations:
        if obs.get("is_synthetic") or obs.get("source") in ("RIVO Sample Data", "demo_seed"):
            synthetic_count += 1
        elif obs.get("is_demo") or str(obs.get("listing_id", "")).startswith(("CMRL-", "MOCK-")):
            demo_count += 1
        else:
            real_obs.append(obs)

    real_count = len(real_obs)
    unique_properties = len({obs.get("listing_id") for obs in real_obs if obs.get("listing_id")})
    unique_localities = len({str(obs.get("locality")).lower().strip() for obs in real_obs if obs.get("locality")})
    unique_bhks = len({obs.get("bhk") for obs in real_obs if obs.get("bhk") is not None})
    sources = {obs.get("source") for obs in real_obs if obs.get("source")}
    source_count = len(sources)

    # Temporal span calculation
    observed_dates = []
    for obs in real_obs:
        dt = obs.get("observed_at")
        if isinstance(dt, datetime):
            observed_dates.append(dt)
        elif isinstance(dt, str):
            try:
                observed_dates.append(datetime.fromisoformat(dt.replace("Z", "+00:00")))
            except Exception:
                pass

    temporal_span_days = 0
    if len(observed_dates) >= 2:
        oldest = min(observed_dates)
        newest = max(observed_dates)
        temporal_span_days = max(0, (newest - oldest).days)

    synthetic_ratio = (synthetic_count + demo_count) / total_count if total_count > 0 else 0.0

    metrics = {
        "total_observations": total_count,
        "real_observations": real_count,
        "synthetic_observations": synthetic_count,
        "demo_observations": demo_count,
        "synthetic_ratio": round(synthetic_ratio, 3),
        "unique_properties": unique_properties,
        "unique_localities": unique_localities,
        "unique_bhks": unique_bhks,
        "source_count": source_count,
        "sources": list(sources),
        "temporal_span_days": temporal_span_days,
    }

    reasons: List[str] = []
    is_eligible = True

    # 1. Minimum real observations
    if real_count < t.min_real_observations:
        is_eligible = False
        reasons.append(
            f"Insufficient real observations: {real_count} available, minimum required is {t.min_real_observations}."
        )

    # 2. Minimum unique properties
    if unique_properties < t.min_unique_properties:
        is_eligible = False
        reasons.append(
            f"Too few unique properties: {unique_properties} available, minimum required is {t.min_unique_properties}."
        )

    # 3. Minimum unique localities
    if unique_localities < t.min_localities:
        is_eligible = False
        reasons.append(
            f"Too few localities represented: {unique_localities} available, minimum required is {t.min_localities}."
        )

    # 4. Minimum BHK classes
    if unique_bhks < t.min_bhk_classes:
        is_eligible = False
        reasons.append(
            f"Too few BHK classes: {unique_bhks} available, minimum required is {t.min_bhk_classes}."
        )

    # 5. Minimum source diversity
    if source_count < t.min_source_count:
        is_eligible = False
        reasons.append(
            f"Insufficient source diversity: {source_count} sources ({list(sources)}), minimum required is {t.min_source_count}."
        )

    # 6. Maximum synthetic ratio
    if synthetic_ratio > t.max_synthetic_ratio and real_count < t.min_real_observations:
        is_eligible = False
        reasons.append(
            f"Dataset dominated by synthetic/demo records: {round(synthetic_ratio * 100, 1)}% synthetic, maximum allowed is {round(t.max_synthetic_ratio * 100, 1)}%."
        )

    # 7. Minimum temporal variation
    if temporal_span_days < t.min_temporal_span_days and real_count >= t.min_real_observations:
        is_eligible = False
        reasons.append(
            f"Insufficient temporal variation: {temporal_span_days} days observed, minimum required is {t.min_temporal_span_days} days."
        )

    status = "READY" if is_eligible else "NOT_READY_INSUFFICIENT_DATA"

    return ModelEligibilityResult(
        is_eligible=is_eligible,
        status=status,
        reasons=reasons,
        metrics=metrics,
        thresholds=t.model_dump(),
        evaluated_at=datetime.now(timezone.utc),
    )
