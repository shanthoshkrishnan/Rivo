"""
RIVO Backend — Unit Tests: Normalization & Deduplication
==========================================================
Tests normalization helpers and the deduplication algorithm
from app/services/algorithms/normalization.py.
"""
from __future__ import annotations

import pytest

from app.services.algorithms.normalization import (
    deduplicate_listings,
    make_url_hash,
    normalize_area_sqft,
    normalize_bhk,
    normalize_furnishing,
    normalize_locality,
    normalize_property_type,
    normalize_rent,
)


class TestNormalization:
    def test_furnishing_canonical(self):
        assert normalize_furnishing("Fully Furnished") == "fully-furnished"
        assert normalize_furnishing("unfurnished") == "unfurnished"
        assert normalize_furnishing("semi furnished") == "semi-furnished"
        assert normalize_furnishing(None) is None
        assert normalize_furnishing("unknown_garbage") is None

    def test_bhk_from_string(self):
        assert normalize_bhk("2 BHK") == 2
        assert normalize_bhk("3BHK") == 3
        assert normalize_bhk("studio") == 0
        assert normalize_bhk(2) == 2
        assert normalize_bhk(None) is None

    def test_area_from_string(self):
        assert normalize_area_sqft("850 sqft") == 850.0
        assert normalize_area_sqft("1,200") == 1200.0
        assert normalize_area_sqft(850.0) == 850.0
        assert normalize_area_sqft(None) is None

    def test_rent_from_string(self):
        assert normalize_rent("₹12,000") == 12000.0
        assert normalize_rent("12k") == 12000.0
        assert normalize_rent("12.5K") == 12500.0
        assert normalize_rent(8500.0) == 8500.0
        assert normalize_rent(None) is None

    def test_locality_normalization(self):
        assert normalize_locality("Anna Nagar") == "anna_nagar"
        assert normalize_locality("  Velachery  ") == "velachery"
        assert normalize_locality(None) is None

    def test_property_type(self):
        assert normalize_property_type("Apartment") == "flat"
        assert normalize_property_type("Independent House") == "house"
        assert normalize_property_type("Studio Apartment") == "studio"
        assert normalize_property_type(None) is None

    def test_url_hash_deterministic(self):
        url = "https://example.com/listings/123"
        h1 = make_url_hash(url)
        h2 = make_url_hash(url)
        assert h1 == h2
        assert len(h1) == 16
        assert make_url_hash(None) is None


class TestDeduplication:
    def _make_listing(self, **kwargs) -> dict:
        base = {
            "listing_id": "L1",
            "provider": "mock",
            "latitude": 12.975,
            "longitude": 80.220,
            "bhk": 2,
            "rent_monthly": 12000,
            "url_hash": None,
        }
        base.update(kwargs)
        return base

    def test_exact_duplicate_same_provider_id(self):
        listings = [
            self._make_listing(listing_id="L1"),
            self._make_listing(listing_id="L1"),
        ]
        result = deduplicate_listings(listings)
        clusters = {r["duplicate_cluster_id"] for r in result}
        assert len(clusters) == 1
        canonicals = [r for r in result if r["is_canonical"]]
        assert len(canonicals) == 1

    def test_coordinate_proximity_dedup(self):
        listings = [
            self._make_listing(listing_id="L1", latitude=12.9750, longitude=80.2200),
            self._make_listing(listing_id="L2", latitude=12.9750, longitude=80.2201),   # ~9m apart
        ]
        result = deduplicate_listings(listings)
        clusters = {r["duplicate_cluster_id"] for r in result}
        assert len(clusters) == 1

    def test_different_localities_not_duped(self):
        listings = [
            self._make_listing(listing_id="L1", latitude=12.975, longitude=80.220),
            self._make_listing(listing_id="L2", latitude=13.085, longitude=80.210),  # far away
        ]
        result = deduplicate_listings(listings)
        clusters = {r["duplicate_cluster_id"] for r in result}
        assert len(clusters) == 2

    def test_url_hash_dedup(self):
        listings = [
            self._make_listing(listing_id="L1", url_hash="abc123"),
            self._make_listing(listing_id="L2", url_hash="abc123"),
        ]
        result = deduplicate_listings(listings)
        clusters = {r["duplicate_cluster_id"] for r in result}
        assert len(clusters) == 1
