"""
RIVO Backend — H3 & Spatial Utilities
=======================================
Helper functions for:
  - Converting lat/lon to H3 index
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

import h3

from app.core.config import get_settings

settings = get_settings()


def lat_lon_to_h3(lat: float, lon: float, resolution: Optional[int] = None) -> str:
    """
    Convert latitude / longitude to H3 cell index at the configured resolution.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        resolution: H3 resolution (1–15). Defaults to settings.H3_RESOLUTION (9).

    Returns:
        H3 cell index string (e.g. "8928308280fffff")
    """
    res = resolution or settings.H3_RESOLUTION
    # h3-py 4.x API: latlng_to_cell (was geo_to_h3 in 3.x)
    return h3.latlng_to_cell(lat, lon, res)


def h3_to_center(h3_index: str) -> Tuple[float, float]:
    """Return the (lat, lon) of the H3 cell centre."""
    # h3-py 4.x API: cell_to_latlng (was h3_to_geo in 3.x)
    return h3.cell_to_latlng(h3_index)


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
