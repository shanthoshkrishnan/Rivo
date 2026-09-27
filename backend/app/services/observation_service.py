"""
RIVO Backend — Observation Service
====================================
Phase 10/11: Real Rental Observation Acquisition & Market Readiness

Central service for:
  - Persisting observations in-memory (in-process store; upgradeable to DB)
  - Eligibility evaluation per observation
  - Data quality reporting with gate progress
  - Bulk import processing
  - Real-data market summary (never mixes demo data)
  - Observation workflow (validate → quality → dedup → approve → publish)
"""
from __future__ import annotations

import csv
import io
import json
import statistics
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.ml import ModelEligibilityResult
from app.schemas.observation import (
    AdminCollectObservationRequest,
    AdminCollectObservationResponse,
    AdminDataQualityReport,
    BulkImportResult,
    BulkObservationRow,
    ObservationHistoryResponse,
    ObservationRecord,
)


# ─────────────────────────────────────────────────────────────────────────────
# Model eligibility thresholds (mirrors eligibility.py)
# ─────────────────────────────────────────────────────────────────────────────
_MIN_REAL_OBSERVATIONS = 50
_MIN_UNIQUE_PROPERTIES = 30
_MIN_LOCALITIES = 5
_MIN_BHK_CLASSES = 3
_MIN_SOURCE_COUNT = 2
_MIN_TEMPORAL_SPAN_DAYS = 7
_MAX_SYNTHETIC_RATIO = 0.10


def _compute_eligibility(obs_eligible: List[dict]) -> Tuple[bool, str]:
    """Quick eligibility check on a list of eligible observation dicts."""
    if len(obs_eligible) < _MIN_REAL_OBSERVATIONS:
        return False, "NOT_READY_INSUFFICIENT_DATA"

    # Property count: count unique listing_ids (multiple obs of same = 1 property)
    props = {o["listing_id"] for o in obs_eligible}
    if len(props) < _MIN_UNIQUE_PROPERTIES:
        return False, "NOT_READY_INSUFFICIENT_DATA"

    localities = {o["locality"].lower().strip() for o in obs_eligible}
    if len(localities) < _MIN_LOCALITIES:
        return False, "NOT_READY_INSUFFICIENT_DATA"

    bhk_classes = {o["bhk"] for o in obs_eligible}
    if len(bhk_classes) < _MIN_BHK_CLASSES:
        return False, "NOT_READY_INSUFFICIENT_DATA"

    # Source diversity: count genuinely independent source channels
    sources = {o["source"] for o in obs_eligible}
    if len(sources) < _MIN_SOURCE_COUNT:
        return False, "NOT_READY_INSUFFICIENT_DATA"

    dates = sorted(o["observed_at"] for o in obs_eligible)
    if dates:
        span = (dates[-1] - dates[0]).days
        if span < _MIN_TEMPORAL_SPAN_DAYS:
            return False, "NOT_READY_INSUFFICIENT_DATA"

    return True, "READY"


def _gate_progress(eligible_obs: List[dict]) -> Dict[str, Any]:
    """
    Returns per-gate progress for the data quality dashboard.
    Shows X / threshold for each gate, whether it passes, and the blocking reason.
    """
    n = len(eligible_obs)
    props = {o["listing_id"] for o in eligible_obs}
    localities = {o["locality"].lower().strip() for o in eligible_obs}
    bhk_classes = {o["bhk"] for o in eligible_obs}
    sources = {o["source"] for o in eligible_obs}
    dates = sorted(o["observed_at"] for o in eligible_obs)
    span = (dates[-1] - dates[0]).days if len(dates) >= 2 else 0

    total = len(eligible_obs)
    all_obs_count = total  # eligible already excludes synth/demo
    synth_ratio = 0.0  # by definition eligible_obs contains no synth/demo

    return {
        "real_observations": {
            "current": n,
            "required": _MIN_REAL_OBSERVATIONS,
            "pass": n >= _MIN_REAL_OBSERVATIONS,
        },
        "unique_properties": {
            "current": len(props),
            "required": _MIN_UNIQUE_PROPERTIES,
            "pass": len(props) >= _MIN_UNIQUE_PROPERTIES,
        },
        "localities": {
            "current": len(localities),
            "required": _MIN_LOCALITIES,
            "pass": len(localities) >= _MIN_LOCALITIES,
        },
        "bhk_classes": {
            "current": len(bhk_classes),
            "required": _MIN_BHK_CLASSES,
            "pass": len(bhk_classes) >= _MIN_BHK_CLASSES,
        },
        "source_diversity": {
            "current": len(sources),
            "required": _MIN_SOURCE_COUNT,
            "pass": len(sources) >= _MIN_SOURCE_COUNT,
        },
        "temporal_span_days": {
            "current": span,
            "required": _MIN_TEMPORAL_SPAN_DAYS,
            "pass": span >= _MIN_TEMPORAL_SPAN_DAYS,
        },
        "synthetic_ratio": {
            "current": 0.0,  # eligible_obs are all real by construction
            "max_allowed": _MAX_SYNTHETIC_RATIO,
            "pass": True,
        },
    }


class ObservationService:
    """
    In-process observation store for Phase 10.

    The _store is a list of flat dicts, each representing one observation.
    Keys:
      id, listing_id, observed_at, rent_monthly, availability_status,
      locality, bhk, area_sqft, furnishing, property_type,
      latitude, longitude, source, changed_fields,
      is_synthetic, is_demo, is_periodic, is_live, eligible_for_model
    """

    def __init__(self) -> None:
        self._store: List[dict] = []

    # ── Core write ────────────────────────────────────────────────────────────

    def record(
        self,
        listing_id: str,
        rent_monthly: float,
        availability_status: str,
        locality: str,
        bhk: int,
        source: str,
        observed_at: Optional[datetime] = None,
        area_sqft: Optional[float] = None,
        furnishing: Optional[str] = None,
        property_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        changed_fields: Optional[List[str]] = None,
        is_synthetic: bool = False,
        is_demo: bool = False,
        is_periodic: bool = False,
        is_live: bool = False,
    ) -> dict:
        """
        Store one rental observation.
        NEVER set eligible_for_model=True for synthetic or demo records.
        """
        eligible = (
            not is_synthetic
            and not is_demo
            and rent_monthly > 0
            and len(locality.strip()) >= 2
            and bhk >= 0
        )
        entry = {
            "id": str(uuid.uuid4()),
            "listing_id": listing_id,
            "observed_at": observed_at or datetime.now(timezone.utc),
            "rent_monthly": rent_monthly,
            "availability_status": availability_status,
            "locality": locality,
            "bhk": bhk,
            "area_sqft": area_sqft,
            "furnishing": furnishing,
            "property_type": property_type,
            "latitude": latitude,
            "longitude": longitude,
            "source": source,
            "changed_fields": changed_fields or ["initial_observation"],
            "is_synthetic": is_synthetic,
            "is_demo": is_demo,
            "is_periodic": is_periodic,
            "is_live": is_live,
            "eligible_for_model": eligible,
        }
        self._store.append(entry)
        return entry

    # ── History ───────────────────────────────────────────────────────────────

    def get_history(self, listing_id: str) -> ObservationHistoryResponse:
        """Return all observations for a given listing_id, sorted oldest-first."""
        records = sorted(
            [o for o in self._store if o["listing_id"] == listing_id],
            key=lambda o: o["observed_at"],
        )
        eligible_count = sum(1 for o in records if o["eligible_for_model"])
        first_dt = records[0]["observed_at"] if records else None
        last_dt = records[-1]["observed_at"] if records else None

        return ObservationHistoryResponse(
            listing_id=listing_id,
            total_observations=len(records),
            first_observed_at=first_dt,
            last_observed_at=last_dt,
            eligible_for_model_count=eligible_count,
            observations=[
                ObservationRecord(
                    listing_id=o["listing_id"],
                    observed_at=o["observed_at"],
                    rent_monthly=o["rent_monthly"],
                    availability_status=o["availability_status"],
                    locality=o["locality"],
                    bhk=o["bhk"],
                    area_sqft=o.get("area_sqft"),
                    furnishing=o.get("furnishing"),
                    source=o["source"],
                    changed_fields=o.get("changed_fields", []),
                    is_synthetic=o.get("is_synthetic", False),
                    is_demo=o.get("is_demo", False),
                    eligible_for_model=o.get("eligible_for_model", False),
                )
                for o in records
            ],
        )

    # ── Admin collect ─────────────────────────────────────────────────────────

    def admin_collect(self, req: AdminCollectObservationRequest) -> AdminCollectObservationResponse:
        """
        Add a single manually verified observation from a field agent or admin.
        Enforces is_synthetic=False, is_demo=False.
        """
        if req.is_synthetic or req.is_demo:
            return AdminCollectObservationResponse(
                accepted=False,
                listing_id=req.listing_id,
                observation_id="",
                eligible_for_model=False,
                total_eligible_observations=self._eligible_count(),
                model_eligibility_status="NOT_READY_INSUFFICIENT_DATA",
                message="Admin-collected observations MUST NOT be synthetic or demo.",
            )

        entry = self.record(
            listing_id=req.listing_id,
            rent_monthly=req.rent_monthly,
            availability_status=req.availability_status,
            locality=req.locality,
            bhk=req.bhk,
            source=req.source,
            observed_at=req.observed_at,
            area_sqft=req.area_sqft,
            furnishing=req.furnishing,
            property_type=req.property_type,
            latitude=req.latitude,
            longitude=req.longitude,
            is_synthetic=False,
            is_demo=False,
            is_live=True,
        )

        eligible_obs = [o for o in self._store if o["eligible_for_model"]]
        _, status = _compute_eligibility(eligible_obs)

        logger.info(
            "[OBSERVATION] Admin observation recorded",
            listing_id=req.listing_id,
            source=req.source,
            eligible=entry["eligible_for_model"],
            total_eligible=len(eligible_obs),
        )

        return AdminCollectObservationResponse(
            accepted=True,
            listing_id=req.listing_id,
            observation_id=entry["id"],
            eligible_for_model=entry["eligible_for_model"],
            total_eligible_observations=len(eligible_obs),
            model_eligibility_status=status,
            message=(
                f"Observation accepted. "
                f"{_MIN_REAL_OBSERVATIONS - len(eligible_obs)} more eligible observations needed for model training."
                if len(eligible_obs) < _MIN_REAL_OBSERVATIONS
                else "Model eligibility threshold reached!"
            ),
        )

    # ── Bulk import ───────────────────────────────────────────────────────────

    def bulk_import(self, rows: List[BulkObservationRow]) -> BulkImportResult:
        """
        Import a list of validated observation rows.
        Returns a full summary of accepted/rejected records.
        """
        accepted = 0
        rejected_synthetic = 0
        rejected_demo = 0
        rejected_val = 0
        eligible = 0
        sources: set[str] = set()
        localities: set[str] = set()
        errors: List[str] = []

        for i, row in enumerate(rows):
            if row.is_synthetic:
                rejected_synthetic += 1
                errors.append(f"Row {i+1} (listing_id={row.listing_id!r}): Rejected — is_synthetic=True")
                continue
            if row.is_demo:
                rejected_demo += 1
                errors.append(f"Row {i+1} (listing_id={row.listing_id!r}): Rejected — is_demo=True")
                continue

            try:
                entry = self.record(
                    listing_id=row.listing_id,
                    rent_monthly=row.rent_monthly,
                    availability_status=row.availability_status,
                    locality=row.locality,
                    bhk=row.bhk,
                    source=row.source,
                    observed_at=row.observed_at,
                    area_sqft=row.area_sqft,
                    furnishing=row.furnishing,
                    property_type=row.property_type,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    is_synthetic=False,
                    is_demo=False,
                    is_periodic=row.is_periodic,
                    is_live=row.is_live,
                )
                accepted += 1
                if entry["eligible_for_model"]:
                    eligible += 1
                sources.add(row.source)
                localities.add(row.locality)
            except Exception as exc:
                rejected_val += 1
                errors.append(f"Row {i+1} (listing_id={row.listing_id!r}): {exc}")

        logger.info(
            "[BULK IMPORT] Completed",
            total=len(rows),
            accepted=accepted,
            rejected_synthetic=rejected_synthetic,
            rejected_demo=rejected_demo,
            rejected_val=rejected_val,
            eligible=eligible,
        )

        return BulkImportResult(
            total_rows=len(rows),
            accepted=accepted,
            rejected_synthetic=rejected_synthetic,
            rejected_demo=rejected_demo,
            rejected_validation_error=rejected_val,
            eligible_for_model=eligible,
            sources=sorted(sources),
            localities=sorted(localities),
            errors=errors,
        )

    # ── Data quality report ───────────────────────────────────────────────────

    def data_quality_report(self) -> AdminDataQualityReport:
        """
        Returns data quality metrics with per-gate progress.
        real_observations ≠ eligible_for_model:
          real_obs = not synthetic AND not demo (may still fail other gates)
          eligible  = real AND passes per-record validation
        Property count = unique listing_ids (multiple obs of same property = 1 property).
        """
        all_obs = self._store
        real_obs = [o for o in all_obs if not o.get("is_synthetic") and not o.get("is_demo")]
        eligible_obs = [o for o in all_obs if o.get("eligible_for_model")]
        demo_obs = [o for o in all_obs if o.get("is_demo")]
        synth_obs = [o for o in all_obs if o.get("is_synthetic")]

        # Unique properties = unique listing_ids in eligible set
        unique_props = {o["listing_id"] for o in eligible_obs}
        unique_locs = sorted({o["locality"].lower().strip() for o in eligible_obs})
        unique_srcs = sorted({o["source"] for o in eligible_obs})

        dates = sorted(o["observed_at"] for o in eligible_obs)
        span_days = (dates[-1] - dates[0]).days if len(dates) >= 2 else None

        is_ready, status = _compute_eligibility(eligible_obs)
        needed = max(0, _MIN_REAL_OBSERVATIONS - len(eligible_obs))
        gate_progress = _gate_progress(eligible_obs)

        return AdminDataQualityReport(
            total_observations=len(all_obs),
            real_observations=len(real_obs),
            demo_observations=len(demo_obs),
            synthetic_observations=len(synth_obs),
            eligible_for_model=len(eligible_obs),
            unique_properties=len(unique_props),
            unique_localities=unique_locs,
            unique_sources=unique_srcs,
            temporal_span_days=float(span_days) if span_days is not None else None,
            model_ready=is_ready,
            model_eligibility_status=status,
            observations_needed=needed,
            gate_progress=gate_progress,
        )

    # ── Real-data market summary ───────────────────────────────────────────────

    def real_market_summary(self) -> Dict[str, Any]:
        """
        Returns empirical market statistics computed ONLY from eligible real observations.
        NEVER includes demo or synthetic data.
        Returns insufficient_data=True when fewer than 5 real observations exist.
        """
        eligible = [o for o in self._store if o.get("eligible_for_model")]
        if len(eligible) < 5:
            return {
                "observation_count": len(eligible),
                "property_count": 0,
                "locality_count": 0,
                "median": None,
                "p25": None,
                "p75": None,
                "by_bhk": {},
                "by_locality": {},
                "source_count": 0,
                "data_as_of": datetime.now(timezone.utc).isoformat(),
                "confidence": "INSUFFICIENT_DATA",
                "insufficient_data": True,
                "note": "Market statistics unavailable — fewer than 5 real observations.",
            }

        rents = [o["rent_monthly"] for o in eligible if o.get("rent_monthly", 0) > 0]
        rents_sorted = sorted(rents)
        n = len(rents_sorted)

        med = round(statistics.median(rents_sorted), 2)
        p25 = round(rents_sorted[int(n * 0.25)], 2)
        p75 = round(rents_sorted[int(n * 0.75)], 2)

        by_bhk: Dict[int, List[float]] = {}
        for o in eligible:
            if o.get("bhk") and o.get("rent_monthly"):
                by_bhk.setdefault(o["bhk"], []).append(o["rent_monthly"])

        by_loc: Dict[str, List[float]] = {}
        for o in eligible:
            loc = o.get("locality", "").lower().strip()
            if loc and o.get("rent_monthly"):
                by_loc.setdefault(loc, []).append(o["rent_monthly"])

        return {
            "observation_count": n,
            "property_count": len({o["listing_id"] for o in eligible}),
            "locality_count": len({o["locality"].lower().strip() for o in eligible}),
            "median": med,
            "p25": p25,
            "p75": p75,
            "by_bhk": {bhk: round(statistics.median(vals), 2) for bhk, vals in by_bhk.items()},
            "by_locality": {loc: round(statistics.median(vals), 2) for loc, vals in by_loc.items()},
            "source_count": len({o["source"] for o in eligible}),
            "data_as_of": datetime.now(timezone.utc).isoformat(),
            "confidence": "MEDIUM" if n >= 10 else "LOW",
            "insufficient_data": False,
        }

    # ── Observation workflow ───────────────────────────────────────────────────

    def validate_observation(self, obs: dict) -> Tuple[str, List[str]]:
        """
        Phase 11 Task 26 — Observation workflow validation.
        Returns (status, reasons) where status is one of:
          VALID | QUESTIONABLE | REJECTED

        REJECTED:  synthetic, demo, missing source, impossible rent, out-of-bounds coords
        QUESTIONABLE: real but weak location precision (geocode_confidence=LOW)
        VALID:     passes all hard checks
        """
        reasons: List[str] = []

        # Hard rejections
        if obs.get("is_synthetic"):
            return "REJECTED", ["is_synthetic=True — synthetic observations are never accepted"]
        if obs.get("is_demo"):
            return "REJECTED", ["is_demo=True — demo observations are never accepted"]
        if not obs.get("source"):
            reasons.append("REJECTED: missing source")
            return "REJECTED", reasons
        if not obs.get("observed_at"):
            reasons.append("REJECTED: missing observed_at")
            return "REJECTED", reasons

        rent = obs.get("rent_monthly", 0)
        if not rent or rent <= 0:
            reasons.append("REJECTED: rent_monthly must be > 0")
            return "REJECTED", reasons
        if rent > 1_000_000:
            reasons.append(f"REJECTED: rent_monthly={rent} exceeds maximum (₹10,00,000)")
            return "REJECTED", reasons
        if rent < 2000:
            reasons.append(f"REJECTED: rent_monthly={rent} below minimum reasonable threshold (₹2,000)")
            return "REJECTED", reasons

        lat, lon = obs.get("latitude"), obs.get("longitude")
        if lat is not None and lon is not None:
            from app.schemas.rental import CHENNAI_LAT_MIN, CHENNAI_LAT_MAX, CHENNAI_LON_MIN, CHENNAI_LON_MAX
            if not (CHENNAI_LAT_MIN <= lat <= CHENNAI_LAT_MAX):
                reasons.append(f"REJECTED: latitude {lat} outside Chennai bounds")
                return "REJECTED", reasons
            if not (CHENNAI_LON_MIN <= lon <= CHENNAI_LON_MAX):
                reasons.append(f"REJECTED: longitude {lon} outside Chennai bounds")
                return "REJECTED", reasons

        bhk = obs.get("bhk")
        if bhk is None or bhk < 0 or bhk > 10:
            reasons.append(f"REJECTED: bhk={bhk} is out of range [0, 10]")
            return "REJECTED", reasons

        # Soft warnings → QUESTIONABLE
        geocode_confidence = obs.get("geocode_confidence", "")
        if isinstance(geocode_confidence, str):
            geocode_confidence = geocode_confidence.upper()
        if geocode_confidence == "LOW" or (lat is None or lon is None):
            reasons.append("QUESTIONABLE: geocode_confidence=LOW or coordinates absent — location precision is weak")
            return "QUESTIONABLE", reasons

        return "VALID", ["All checks passed"]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _eligible_count(self) -> int:
        return sum(1 for o in self._store if o.get("eligible_for_model"))

    def get_all(self) -> List[dict]:
        return list(self._store)

    # ── Phase 12: Collection progress ─────────────────────────────────────────

    def collection_progress(self) -> Dict[str, Any]:
        """
        Phase 12 Task 18 — Operational collection progress.
        Returns per-gate progress + breakdown by locality, BHK, and source.
        Never mixes demo or synthetic data.
        Used by:  GET /api/v1/rentals/admin/collection-progress
        """
        eligible = [o for o in self._store if o.get("eligible_for_model")]
        real = [o for o in self._store if not o.get("is_synthetic") and not o.get("is_demo")]

        # Gate progress (same as data_quality_report)
        gate_progress = _gate_progress(eligible)

        is_ready, status = _compute_eligibility(eligible)
        blocking: List[str] = []
        for gate_name, gate in gate_progress.items():
            if not gate.get("pass", True):
                cur = gate.get("current", 0)
                req = gate.get("required", gate.get("max_allowed", "?"))
                blocking.append(f"{gate_name}: {cur} / {req}")

        # Per-locality breakdown
        by_locality: Dict[str, Dict[str, Any]] = {}
        for o in eligible:
            loc = o.get("locality", "unknown").lower().strip()
            entry = by_locality.setdefault(loc, {"observations": 0, "properties": set(), "bhk_classes": set()})
            entry["observations"] += 1
            entry["properties"].add(o["listing_id"])
            if o.get("bhk"):
                entry["bhk_classes"].add(o["bhk"])
        by_locality_out = {
            loc: {
                "observations": v["observations"],
                "unique_properties": len(v["properties"]),
                "bhk_classes": sorted(v["bhk_classes"]),
            }
            for loc, v in by_locality.items()
        }

        # Per-BHK breakdown
        by_bhk: Dict[int, Dict[str, Any]] = {}
        for o in eligible:
            bhk = o.get("bhk")
            if bhk is None:
                continue
            entry = by_bhk.setdefault(bhk, {"observations": 0, "properties": set(), "localities": set()})
            entry["observations"] += 1
            entry["properties"].add(o["listing_id"])
            entry["localities"].add(o.get("locality", "").lower().strip())
        by_bhk_out = {
            bhk: {
                "observations": v["observations"],
                "unique_properties": len(v["properties"]),
                "localities": sorted(v["localities"]),
            }
            for bhk, v in by_bhk.items()
        }

        # Per-source breakdown
        by_source: Dict[str, int] = {}
        for o in eligible:
            src = o.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        dates = sorted(o["observed_at"] for o in eligible)
        span = (dates[-1] - dates[0]).days if len(dates) >= 2 else 0
        first_obs = dates[0].isoformat() if dates else None
        last_obs = dates[-1].isoformat() if dates else None

        return {
            "real_observations": len(eligible),
            "unique_properties": len({o["listing_id"] for o in eligible}),
            "localities": sorted({o.get("locality", "").lower().strip() for o in eligible}),
            "bhk_classes": sorted({o.get("bhk") for o in eligible if o.get("bhk") is not None}),
            "source_count": len({o["source"] for o in eligible}),
            "temporal_span_days": span,
            "first_observed_at": first_obs,
            "last_observed_at": last_obs,
            "model_ready": is_ready,
            "model_eligibility_status": status,
            "blocking_reasons": blocking,
            "gate_progress": gate_progress,
            "by_locality": by_locality_out,
            "by_bhk": by_bhk_out,
            "by_source": by_source,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    def quality_warnings(self, obs: dict) -> List[str]:
        """
        Phase 12 Task 9 — Return operational quality warnings for a candidate observation.
        These are advisory — the observation is NOT rejected.
        Checks for common collection issues that reduce data quality.
        """
        warnings: List[str] = []

        lat, lon = obs.get("latitude"), obs.get("longitude")
        if lat is None or lon is None:
            warnings.append("Exact coordinates missing — only locality-level precision available.")

        gc = (obs.get("geocode_confidence") or "").upper()
        if gc == "LOW":
            warnings.append("Geocode confidence is LOW — location precision is weak.")

        if not obs.get("source"):
            warnings.append("Source not recorded — provenance will be lost.")

        avail = obs.get("availability_status", "")
        if avail in ("UNKNOWN", "RECENTLY_SEEN"):
            warnings.append(
                f"Availability is '{avail}' — current status has not been confirmed with owner/agent."
            )

        verification = obs.get("verification_status", "")
        if verification == "UNVERIFIED" or not verification:
            warnings.append("Observation is UNVERIFIED — source has not been independently checked.")

        listing_id = obs.get("listing_id", "")
        if not listing_id:
            warnings.append("listing_id is empty — may create duplicate property entries.")
        else:
            # Duplicate property check
            existing_ids = {o["listing_id"] for o in self._store}
            if listing_id in existing_ids:
                warnings.append(
                    f"listing_id '{listing_id}' already exists — this will create a new observation "
                    "for an existing property (which is correct for price updates)."
                )

        return warnings


# Global singleton — shared across the process
observation_service = ObservationService()
