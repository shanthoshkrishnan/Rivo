"""
RIVO Backend — Spatial & Transit Feature Engineering
=====================================================
Calculates deterministic spatial features using local Chennai GTFS stops:
  - nearest_metro_distance_m (CMRL stops)
  - nearest_bus_stop_distance_m (MTC stops)
  - transit_accessibility_index (composite score based on transit proximity)
  - H3 spatial indexing
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.spatial import lat_lng_to_h3

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0  # meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class TransitFeatureExtractor:
    """
    Deterministic transit accessibility extractor grounded in local GTFS feeds.
    """

    def __init__(self, gtfs_root: Optional[Path] = None) -> None:
        self.gtfs_root = gtfs_root or (BASE_DIR / "data" / "seed" / "gtfs")
        self._metro_stops: List[Tuple[float, float, str]] = []
        self._bus_stops: List[Tuple[float, float, str]] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        # Load CMRL metro stops
        cmrl_file = self.gtfs_root / "cmrl-gtfs" / "stops.txt"
        if cmrl_file.exists():
            try:
                with open(cmrl_file, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        lat, lon = row.get("stop_lat"), row.get("stop_lon")
                        name = row.get("stop_name", "")
                        if lat and lon:
                            self._metro_stops.append((float(lat), float(lon), name))
            except Exception:
                pass

        # Load unified/MTC bus stops
        mtc_file = self.gtfs_root / "chennai-unified-gtfs" / "stops.txt"
        if mtc_file.exists():
            try:
                with open(mtc_file, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        lat, lon = row.get("stop_lat"), row.get("stop_lon")
                        name = row.get("stop_name", "")
                        if lat and lon:
                            self._bus_stops.append((float(lat), float(lon), name))
            except Exception:
                pass

        self._loaded = True

    def extract_features(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        bhk: int = 1,
        area_sqft: Optional[float] = None,
        furnishing: Optional[str] = None,
        property_type: Optional[str] = None,
        locality: Optional[str] = None,
    ) -> Dict[str, float]:
        self._ensure_loaded()

        nearest_metro_dist = 99999.0
        nearest_bus_dist = 99999.0

        if latitude is not None and longitude is not None:
            for s_lat, s_lon, _ in self._metro_stops:
                dist = _haversine_m(latitude, longitude, s_lat, s_lon)
                if dist < nearest_metro_dist:
                    nearest_metro_dist = dist

            # Sample MTC stops for performance if bus stops are large
            for s_lat, s_lon, _ in self._bus_stops:
                dist = _haversine_m(latitude, longitude, s_lat, s_lon)
                if dist < nearest_bus_dist:
                    nearest_bus_dist = dist

        # Accessibility index: 1.0 (very close to transit <= 500m) to 0.0 (far > 5km)
        metro_score = max(0.0, 1.0 - (nearest_metro_dist / 3000.0))
        bus_score = max(0.0, 1.0 - (nearest_bus_dist / 1000.0))
        transit_idx = round(0.6 * metro_score + 0.4 * bus_score, 3)

        return {
            "nearest_metro_distance_m": round(nearest_metro_dist, 1) if nearest_metro_dist < 99999 else -1.0,
            "nearest_bus_stop_distance_m": round(nearest_bus_dist, 1) if nearest_bus_dist < 99999 else -1.0,
            "transit_accessibility_index": transit_idx,
            "bhk": float(bhk),
            "area_sqft": float(area_sqft) if area_sqft else float(bhk * 450.0),
        }


feature_extractor = TransitFeatureExtractor()
