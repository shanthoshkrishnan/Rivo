"""
RIVO Backend — Rental Normalization & Deduplication Algorithms
================================================================
Implements ALGORITHMS.md §1 (normalization) and §2 (deduplication).

§1 Normalization
----------------
Normalise INR, sqft, BHK, furnishing, property_type from raw scraped/
provider values to canonical forms.  Raw values are always preserved.

§2 Deduplication
----------------
Uses:
  - provider listing ID (exact match → same listing)
  - URL hash (same URL → same listing)
  - address similarity (fuzzy match)
  - coordinate proximity (within 50 m)
  - same rent + BHK + area + furnishing

Rule: Do NOT use personal phone numbers or image fingerprints
unless legally permitted.

Output: cluster_id assigned to each listing group; one listing in
each cluster is marked is_canonical=True (the most recent / highest
confidence one).
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Tuple

from app.core.logging import logger


# ─────────────────────────────────────────────────────────────────────────────
# §1 Normalization helpers
# ─────────────────────────────────────────────────────────────────────────────

# Canonical furnishing values
_FURNISHING_MAP: Dict[str, str] = {
    "unfurnished": "unfurnished",
    "un-furnished": "unfurnished",
    "bare": "unfurnished",
    "semi furnished": "semi-furnished",
    "semi-furnished": "semi-furnished",
    "semifurnished": "semi-furnished",
    "partially furnished": "semi-furnished",
    "partially-furnished": "semi-furnished",
    "fully furnished": "fully-furnished",
    "fully-furnished": "fully-furnished",
    "fullyfurnished": "fully-furnished",
    "furnished": "fully-furnished",
}

# Canonical property type values
_PROPERTY_TYPE_MAP: Dict[str, str] = {
    "flat": "flat",
    "apartment": "flat",
    "appt": "flat",
    "house": "house",
    "independent house": "house",
    "independent floor": "house",
    "villa": "house",
    "bungalow": "house",
    "studio": "studio",
    "studio apartment": "studio",
    "pg": "pg",
    "paying guest": "pg",
    "room": "room",
    "single room": "room",
}


def normalize_furnishing(raw: Optional[str]) -> Optional[str]:
    """
    Return canonical furnishing label or None if unrecognised.
    Preserves raw value separately.
    """
    if not raw:
        return None
    return _FURNISHING_MAP.get(raw.lower().strip())


def normalize_property_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return _PROPERTY_TYPE_MAP.get(raw.lower().strip())


def normalize_bhk(raw: Optional[str | int]) -> Optional[int]:
    """
    Extract integer BHK from strings like "2 BHK", "3bhk", "Studio" → 0.
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    s = str(raw).lower().strip()
    if "studio" in s:
        return 0
    m = re.search(r"(\d+)", s)
    if m:
        return int(m.group(1))
    return None


def normalize_area_sqft(raw: Optional[str | float]) -> Optional[float]:
    """Extract numeric sqft area from strings like '850 sqft', '850'."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r"[\d,]+\.?\d*", str(raw).replace(",", ""))
    if m:
        return float(m.group().replace(",", ""))
    return None


def normalize_rent(raw: Optional[str | float]) -> Optional[float]:
    """
    Parse INR rent from strings like "₹12,000", "12000/month", "12K".
    Returns float in INR or None.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).lower().replace("₹", "").replace(",", "").strip()
    # Handle "12k" or "12.5k"
    m = re.search(r"(\d+\.?\d*)\s*k", s)
    if m:
        return float(m.group(1)) * 1000
    m = re.search(r"(\d+\.?\d*)", s)
    if m:
        return float(m.group(1))
    return None


def normalize_locality(raw: Optional[str]) -> Optional[str]:
    """Lowercase, strip, collapse spaces."""
    if not raw:
        return None
    return re.sub(r"\s+", "_", raw.lower().strip())


# ─────────────────────────────────────────────────────────────────────────────
# §2 Deduplication
# ─────────────────────────────────────────────────────────────────────────────

def make_url_hash(url: Optional[str]) -> Optional[str]:
    """SHA-256 hex of the URL, truncated to 16 chars."""
    if not url:
        return None
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres."""
    import math
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _address_similarity(a: str, b: str) -> float:
    """
    Simple token-overlap similarity (Jaccard) for address strings.
    Returns 0.0–1.0.
    """
    tokens_a = set(re.findall(r"\w+", a.lower()))
    tokens_b = set(re.findall(r"\w+", b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def deduplicate_listings(
    listings: List[dict],
    coord_threshold_m: float = 50.0,
    address_sim_threshold: float = 0.7,
) -> List[dict]:
    """
    Assign duplicate_cluster_id and is_canonical to each listing dict.

    Algorithm:
      1. Group by (provider, listing_id) → exact match
      2. Group by url_hash
      3. Group by coordinate proximity + same bhk + same rent band
         (within 10% of each other)

    Returns modified list (in-place mutation for efficiency).

    Rule: Do NOT use phone numbers or image fingerprints.
    """
    import uuid

    # Track which cluster each listing belongs to: index → cluster_id
    cluster_map: Dict[int, str] = {}

    def get_or_create_cluster(i: int) -> str:
        if i not in cluster_map:
            cluster_map[i] = str(uuid.uuid4())[:8]
        return cluster_map[i]

    def merge_clusters(i: int, j: int) -> None:
        ci, cj = get_or_create_cluster(i), get_or_create_cluster(j)
        if ci == cj:
            return
        # Merge j's cluster into i's
        for k, v in cluster_map.items():
            if v == cj:
                cluster_map[k] = ci

    n = len(listings)
    for i in range(n):
        a = listings[i]
        for j in range(i + 1, n):
            b = listings[j]
            # Rule 1: same provider + listing_id
            if (
                a.get("provider") == b.get("provider")
                and a.get("listing_id") == b.get("listing_id")
            ):
                merge_clusters(i, j)
                continue
            # Rule 2: same url_hash
            if (
                a.get("url_hash")
                and a.get("url_hash") == b.get("url_hash")
            ):
                merge_clusters(i, j)
                continue
            # Rule 3: coordinate proximity + same bhk + similar rent
            lat_a, lon_a = a.get("latitude"), a.get("longitude")
            lat_b, lon_b = b.get("latitude"), b.get("longitude")
            if all(v is not None for v in (lat_a, lon_a, lat_b, lon_b)):
                dist = _haversine_m(lat_a, lon_a, lat_b, lon_b)  # type: ignore
                if dist <= coord_threshold_m:
                    if a.get("bhk") == b.get("bhk"):
                        rent_a = a.get("rent_monthly") or 0
                        rent_b = b.get("rent_monthly") or 0
                        if rent_a > 0 and rent_b > 0:
                            ratio = max(rent_a, rent_b) / min(rent_a, rent_b)
                            if ratio <= 1.1:
                                merge_clusters(i, j)
                                continue

    # Assign clusters
    canonical_per_cluster: Dict[str, int] = {}
    for i, listing in enumerate(listings):
        cid = get_or_create_cluster(i)
        listing["duplicate_cluster_id"] = cid
        listing["is_canonical"] = False
        if cid not in canonical_per_cluster:
            canonical_per_cluster[cid] = i

    # Mark canonical (first seen / most recent)
    for cluster_i in canonical_per_cluster.values():
        listings[cluster_i]["is_canonical"] = True

    logger.debug(
        "Deduplication complete",
        total=n,
        clusters=len(canonical_per_cluster),
    )
    return listings
