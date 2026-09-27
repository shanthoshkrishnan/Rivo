"""
RIVO Backend — H3 & Spatial Utilities
=======================================
Helper functions for:
  - Converting lat/lon to H3 index (with pure-Python fallback if C-extension is restricted)
  - Adding H3 index to a listing/facility dict
  - Haversine distance calculation
  - GeoJSON geometry helpers

H3 resolution 9: ~174 m hex diameter — good for city-level aggregation.
Resolution is configurable via settings.H3_RESOLUTION.

Reference: https://h3geo.org/docs/
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

try:
    import h3
    _H3_AVAILABLE = True
except (ImportError, OSError):
    _H3_AVAILABLE = False

from app.core.config import get_settings

settings = get_settings()


def lat_lon_to_h3(lat: float, lon: float, resolution: Optional[int] = None) -> str:
    """
    Convert latitude / longitude to H3 cell index at the configured resolution.
    Falls back gracefully to a deterministic 15-char hex spatial cell if h3 C-extension
    is blocked by host OS security policies.
    """
    res = resolution or settings.H3_RESOLUTION
    if _H3_AVAILABLE:
        try:
            return h3.latlng_to_cell(lat, lon, res)
        except Exception:
            pass

    # Deterministic resolution-aware spatial cell representation (15 hex chars)
    # Scale factor based on resolution (approx 174m cell size at res 9)
    step = 0.0015 * (1.5 ** (9 - res))
    q_lat = int(math.floor(lat / step))
    q_lon = int(math.floor(lon / step))
    return f"8{res:x}{(q_lat & 0xfffff):05x}{(q_lon & 0xfffff):05x}f"


lat_lng_to_h3 = lat_lon_to_h3


def h3_to_center(h3_index: str) -> Tuple[float, float]:
    """Return the (lat, lon) of the H3 cell centre."""
    if _H3_AVAILABLE:
        try:
            return h3.cell_to_latlng(h3_index)
        except Exception:
            pass
    # Decode fallback spatial index
    try:
        if len(h3_index) >= 13 and h3_index.startswith("8"):
            res = int(h3_index[1], 16)
            q_lat = int(h3_index[2:7], 16)
            q_lon = int(h3_index[7:12], 16)
            # handle signed 20-bit wrap
            if q_lat > 0x7ffff:
                q_lat -= 0x100000
            if q_lon > 0x7ffff:
                q_lon -= 0x100000
            step = 0.0015 * (1.5 ** (9 - res))
            return (q_lat + 0.5) * step, (q_lon + 0.5) * step
    except Exception:
        pass
    return (13.0827, 80.2707)  # Chennai center default


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance in kilometres between two WGS-84 points.
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    return haversine_km(lat1, lon1, lat2, lon2) * 1000


def point_to_geojson(lat: float, lon: float) -> dict:
    """Return a GeoJSON Point dict for a lat/lon pair."""
    return {"type": "Point", "coordinates": [lon, lat]}


def add_h3_index(
    record: dict,
    lat_key: str = "latitude",
    lon_key: str = "longitude",
    h3_key: str = "h3_index",
    resolution: Optional[int] = None,
) -> dict:
    """
    Add an H3 index field to a dict in place.
    Returns the dict for chaining.
    """
    lat = record.get(lat_key)
    lon = record.get(lon_key)
    if lat is not None and lon is not None:
        record[h3_key] = lat_lon_to_h3(float(lat), float(lon), resolution)
    else:
        record[h3_key] = None
    return record
