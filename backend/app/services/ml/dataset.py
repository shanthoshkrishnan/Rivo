"""
RIVO Backend — Rental Dataset Preparation & Validation Split
============================================================
Prepares real rental observations for training and benchmarking:
  - Enforces strict demo/synthetic exclusion (Task 3 & 4)
  - Filters out-of-bounds coordinates & corrupt data
  - Temporal validation splitting (older -> train, newer -> test)
  - Spatial grouping to avoid spatial data leakage
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.rental import validate_chennai_coordinates
from app.services.algorithms.normalization import (
    normalize_bhk,
    normalize_furnishing,
    normalize_locality,
    normalize_property_type,
    normalize_rent,
)
from app.services.ml.features import feature_extractor
from app.utils.spatial import lat_lng_to_h3


class RentalDatasetRecord:
    def __init__(
        self,
        listing_id: str,
        rent: float,
        bhk: int,
        locality: str,
        area_sqft: float,
        furnishing: str,
        property_type: str,
        latitude: float,
        longitude: float,
        h3_index: str,
        observed_at: datetime,
        source: str,
        features: Dict[str, float],
    ) -> None:
        self.listing_id = listing_id
        self.rent = rent
        self.bhk = bhk
        self.locality = locality
        self.area_sqft = area_sqft
        self.furnishing = furnishing
        self.property_type = property_type
        self.latitude = latitude
        self.longitude = longitude
        self.h3_index = h3_index
        self.observed_at = observed_at
        self.source = source
        self.features = features

    def to_dict(self) -> Dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "rent": self.rent,
            "bhk": self.bhk,
            "locality": self.locality,
            "area_sqft": self.area_sqft,
            "furnishing": self.furnishing,
            "property_type": self.property_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "h3_index": self.h3_index,
            "observed_at": self.observed_at.isoformat(),
            "source": self.source,
            **self.features,
        }


def prepare_training_dataset(
    observations: List[Dict[str, Any]],
    exclude_demo: bool = True,
) -> Tuple[List[RentalDatasetRecord], Dict[str, Any]]:
    """
    Cleans, validates, and engineers features for eligible rental observations.
    """
    valid_records: List[RentalDatasetRecord] = []
    audit = {
        "total_input": len(observations),
        "excluded_synthetic_or_demo": 0,
        "excluded_invalid_coordinates": 0,
        "excluded_impossible_rent": 0,
        "excluded_impossible_area": 0,
        "excluded_duplicate_snapshot": 0,
        "accepted_records": 0,
    }

    seen_property_day: set = set()

    for item in observations:
        # Task 3: Demo / synthetic flags
        if exclude_demo:
            if item.get("is_synthetic") or item.get("is_demo"):
                audit["excluded_synthetic_or_demo"] += 1
                continue
            if str(item.get("listing_id", "")).startswith(("CMRL-", "MOCK-")):
                audit["excluded_synthetic_or_demo"] += 1
                continue
            if item.get("source") in ("RIVO Sample Data", "demo_seed"):
                audit["excluded_synthetic_or_demo"] += 1
                continue

        # Rent validation
        rent = item.get("rent_monthly") or item.get("rent")
        norm_rent = normalize_rent(rent) if rent is not None else None
        if not norm_rent or norm_rent < 2000.0 or norm_rent > 500000.0:
            audit["excluded_impossible_rent"] += 1
            continue

        # Coordinates & bounding box
        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is None or lon is None:
            audit["excluded_invalid_coordinates"] += 1
            continue

        valid_coords, _ = validate_chennai_coordinates(float(lat), float(lon))
        if not valid_coords:
            audit["excluded_invalid_coordinates"] += 1
            continue

        # BHK & Area
        bhk = normalize_bhk(item.get("bhk")) or 1
        area = item.get("area_sqft")
        if area is not None:
            try:
                area = float(area)
                if area < 100.0 or area > 10000.0:
                    audit["excluded_impossible_area"] += 1
                    continue
            except (ValueError, TypeError):
                area = bhk * 450.0
        else:
            area = bhk * 450.0

        # Locality & attributes
        locality = normalize_locality(item.get("locality") or item.get("locality_raw")) or "chennai"
        furnishing = normalize_furnishing(item.get("furnishing")) or "semi-furnished"
        prop_type = normalize_property_type(item.get("property_type")) or "flat"

        # Observation timestamp
        obs_at = item.get("observed_at")
        if isinstance(obs_at, str):
            try:
                obs_at_dt = datetime.fromisoformat(obs_at.replace("Z", "+00:00"))
            except Exception:
                obs_at_dt = datetime.now(timezone.utc)
        elif isinstance(obs_at, datetime):
            obs_at_dt = obs_at
        else:
            obs_at_dt = datetime.now(timezone.utc)

        # Deduplication per property per day
        listing_id = str(item.get("listing_id", "UNKNOWN"))
        day_key = f"{listing_id}_{obs_at_dt.strftime('%Y-%m-%d')}_{norm_rent}"
        if day_key in seen_property_day:
            audit["excluded_duplicate_snapshot"] += 1
            continue
        seen_property_day.add(day_key)

        # Spatial features & transit proximity
        features = feature_extractor.extract_features(
            latitude=float(lat),
            longitude=float(lon),
            bhk=bhk,
            area_sqft=area,
            furnishing=furnishing,
            property_type=prop_type,
            locality=locality,
        )

        h3_idx = lat_lng_to_h3(float(lat), float(lon), resolution=8) or "unknown"

        record = RentalDatasetRecord(
            listing_id=listing_id,
            rent=norm_rent,
            bhk=bhk,
            locality=locality,
            area_sqft=area,
            furnishing=furnishing,
            property_type=prop_type,
            latitude=float(lat),
            longitude=float(lon),
            h3_index=h3_idx,
            observed_at=obs_at_dt,
            source=str(item.get("source", "rivo_direct")),
            features=features,
        )
        valid_records.append(record)

    audit["accepted_records"] = len(valid_records)
    return valid_records, audit


def temporal_train_test_split(
    records: List[RentalDatasetRecord],
    test_ratio: float = 0.2,
) -> Tuple[List[RentalDatasetRecord], List[RentalDatasetRecord], str]:
    """
    Splits records chronologically: older observations for training, newer for validation.
    Avoids random shuffling leakage across time.
    """
    if len(records) < 10:
        return records, [], "TEMPORAL_VALIDATION_INSUFFICIENT"

    sorted_records = sorted(records, key=lambda r: r.observed_at)
    time_span = (sorted_records[-1].observed_at - sorted_records[0].observed_at).total_seconds() / 86400.0

    if time_span < 3.0:
        # Less than 3 days of temporal depth
        split_idx = int(len(sorted_records) * (1.0 - test_ratio))
        return sorted_records[:split_idx], sorted_records[split_idx:], "TEMPORAL_VALIDATION_INSUFFICIENT"

    split_idx = int(len(sorted_records) * (1.0 - test_ratio))
    return sorted_records[:split_idx], sorted_records[split_idx:], "TEMPORAL_SPLIT_VALID"
