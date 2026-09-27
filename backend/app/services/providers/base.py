"""
RIVO Backend — Provider Interfaces (Abstract Base Classes)
===========================================================
Defines contracts for all pluggable providers:
  - RentalProvider
  - RouteProvider
  - PlacesProvider
  - FacilityProvider
  - FuelPriceProvider

Every provider implementation (Mock, OTP, Google, Licensed…)
must implement these interfaces so the rest of the application
never depends on a specific external service.

This makes the app fully demoable without any external credentials
(use MockRentalProvider, MockRouteProvider, etc.) and lets teams
swap providers without touching business logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.schemas.misc import FacilityOut
from app.schemas.rental import RentalListingCreate, RentalSearchParams
from app.schemas.routing import RouteRequest, RouteResult


# ─────────────────────────────────────────────────────────────────────────────
# Rental Provider
# ─────────────────────────────────────────────────────────────────────────────
class RentalProvider(ABC):
    """
    Abstract interface for all rental listing sources.

    Implementations:
      MockRentalProvider          — deterministic seed data, always works
      OpenDatasetRentalProvider   — openly licensed dataset
      LicensedRentalProvider      — requires API key + permitted terms
      AuthorizedThirdPartyProvider — third-party with agreed access

    Note: NEVER scrape a site unless its terms of service explicitly permit it.
    This class is the enforcement point — only implement here if you have
    legal basis to access the data.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Machine-readable provider identifier (e.g. 'mock', 'licensed')."""

    @abstractmethod
    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        """
        Search for rental listings matching the given parameters.

        Implementations MUST:
          - Apply hard constraints (max_rent, bhk, property_type) before returning
          - Set data_freshness on every listing
          - Return an empty list (not raise) when no listings found
          - NOT return personally identifiable information beyond what is
            publicly available from the source
        """

    @abstractmethod
    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        """Fetch a single listing by provider-specific ID."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is currently reachable."""

    def health(self) -> dict:
        """Health and capability metadata."""
        return {
            "provider": self.provider_name,
            "available": self.is_available(),
            "freshness": self.freshness().value,
        }

    def freshness(self) -> DataFreshness:
        """Default freshness tier for this provider."""
        return DataFreshness.PERIODIC


# ─────────────────────────────────────────────────────────────────────────────
# Route Provider
# ─────────────────────────────────────────────────────────────────────────────
class RouteProvider(ABC):
    """
    Abstract interface for routing providers.

    Rule: NEVER compute thousands of routes.  The caller is responsible
    for filtering listings to 100–200 finalists before calling route.

    Implementations:
      MockRouteProvider       — fast, deterministic, no external calls
      OTPRouteProvider        — OpenTripPlanner 2.10 (open/reproducible)
      GoogleRouteProvider     — Google Routes API (live, billed)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Machine-readable name, e.g. 'google', 'otp', 'mock'."""

    @abstractmethod
    async def compute_route(self, request: RouteRequest) -> List[RouteResult]:
        """
        Compute routes for the requested modes.
        Returns an empty list if no route is found.
        Always sets provider and data_freshness on each RouteResult.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider's backend is reachable."""

    @abstractmethod
    def supports_mode(self, mode: str) -> bool:
        """Returns True if this provider can compute the given mode."""


# ─────────────────────────────────────────────────────────────────────────────
# Places Provider
# ─────────────────────────────────────────────────────────────────────────────
class PlacesProvider(ABC):
    """
    Abstract interface for facility/POI data.
    Used to enrich schools, hospitals and pharmacies.

    Implementations:
      OSMPlacesProvider      — OpenStreetMap Overpass API (ODbL)
      GooglePlacesProvider   — Google Places API (requires key + ToS)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def nearby_facilities(
        self,
        latitude: float,
        longitude: float,
        facility_type: str,
        radius_m: int,
        limit: int,
    ) -> List[FacilityOut]:
        """Return facilities of the given type within radius."""

    @abstractmethod
    def is_available(self) -> bool: ...


# ─────────────────────────────────────────────────────────────────────────────
# Facility Provider (DB-backed)
# ─────────────────────────────────────────────────────────────────────────────
class FacilityProvider(ABC):
    """
    Abstract interface for the local DB-backed facility lookup.
    The DB is pre-loaded from UDISE+, OGD health, OSM, etc.
    This avoids live API calls for every listing evaluation.
    """

    @abstractmethod
    async def nearest_school(
        self, lat: float, lon: float, threshold_minutes: Optional[int]
    ) -> Optional[FacilityOut]: ...

    @abstractmethod
    async def nearest_hospital(
        self, lat: float, lon: float, threshold_minutes: Optional[int]
    ) -> Optional[FacilityOut]: ...

    @abstractmethod
    async def nearest_pharmacy(
        self, lat: float, lon: float, threshold_minutes: Optional[int]
    ) -> Optional[FacilityOut]: ...

    @abstractmethod
    async def count_within_threshold(
        self,
        lat: float,
        lon: float,
        facility_type: str,
        threshold_minutes: int,
    ) -> int: ...


# ─────────────────────────────────────────────────────────────────────────────
# Fuel Price Provider
# ─────────────────────────────────────────────────────────────────────────────
class FuelPriceProvider(ABC):
    """
    Abstract interface for fuel price data.
    Used in two-wheeler / car cost estimation.

    MVP: uses configurable default from settings.
    Later: fetch from official IOC / BPCL price API.
    """

    @abstractmethod
    async def get_petrol_price_inr(self) -> float:
        """Return current petrol price in INR per litre."""

    @abstractmethod
    async def get_diesel_price_inr(self) -> float:
        """Return current diesel price in INR per litre."""

    @abstractmethod
    def is_available(self) -> bool: ...
