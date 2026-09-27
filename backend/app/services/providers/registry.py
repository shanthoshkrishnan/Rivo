"""
RIVO Backend — Provider Registry & Factory
============================================
Central factory that selects and configures the right provider
implementations based on application settings.

Routing strategy (per ARCHITECTURE.md):
  1. Google Routes API  — if key is configured and permitted
  2. OTP               — open/reproducible transit routing
  3. Mock              — always available; clearly labelled ESTIMATED

Provider failure handling (per ARCHITECTURE.md):
  - Rental provider down → use recent cache, then estimated rent surface
  - Google route down → use cached route, then OTP, then mock
  - Never hide provider failure from the UI

Singleton instances are created once at startup and reused.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import RentalProviderName, get_settings
from app.core.logging import logger
from app.services.providers.base import PlacesProvider, RentalProvider, RouteProvider
from app.services.providers.rental_mock import MockRentalProvider
from app.services.providers.route_google import GoogleRouteProvider, ProviderUnavailableError
from app.services.providers.route_gtfs import GTFSRouteProvider
from app.services.providers.route_mock import MockRouteProvider
from app.services.providers.route_otp import OTPRouteProvider

settings = get_settings()


@lru_cache(maxsize=1)
def get_rental_provider() -> RentalProvider:
    """
    Return the configured rental provider singleton.
    Defaults to RentalProviderRegistry (composite multi-tier provider)
    which prioritizes direct owner listings, licensed feeds, and periodic seed data.
    """
    from app.services.providers.rental_registry import rental_registry
    return rental_registry


def get_places_provider() -> PlacesProvider:
    """
    Return Google Places provider singleton or instance.
    is_available() reflects whether GOOGLE_PLACES_API_KEY is configured.
    """
    from app.services.providers.places_google import GooglePlacesProvider
    return GooglePlacesProvider()


def get_route_provider() -> RouteProvider:
    """
    Return the best available route provider using the priority chain:
      Google Routes API → OTP → Mock

    Returns a composite provider that tries in order and falls back gracefully.
    """
    return CompositeRouteProvider()


class CompositeRouteProvider(RouteProvider):
    """
    Tries Google Routes API first, then OTP, then Mock.
    The first provider that succeeds for a mode is used.
    Failures are logged and surfaced to the API response via freshness tags.
    """

    PROVIDER_NAME = "composite"

    def __init__(self) -> None:
        self._providers: list[RouteProvider] = []
        # Google is always candidate #1; is_available() dynamically gates execution
        self._providers.append(GoogleRouteProvider())
        self._providers.append(GTFSRouteProvider())
        self._providers.append(OTPRouteProvider())
        self._providers.append(MockRouteProvider())
        current_settings = get_settings()
        if current_settings.google_routes_enabled:
            logger.info("[ROUTE PROVIDER] selected=google reason=api_configured chain=Google → GTFS → OTP → Mock")
        else:
            logger.info("[ROUTE PROVIDER] selected=gtfs reason=google_not_configured chain=GTFS → OTP → Mock")

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        return True   # Mock is always the fallback

    def supports_mode(self, mode: str) -> bool:
        return True   # Mock supports all modes

    async def compute_route(self, request):
        last_error = None
        for provider in self._providers:
            try:
                if not provider.is_available():
                    continue
                logger.info(
                    "[ROUTE PROVIDER] selected=%s reason=%s modes=%s",
                    provider.provider_name,
                    "api_configured" if provider.provider_name == "google" else "chain_order",
                    request.modes,
                )
                results = await provider.compute_route(request)
                if results:
                    return results
            except ProviderUnavailableError as exc:
                last_error = exc
                logger.warning(
                    "Route provider unavailable, trying next",
                    provider=provider.provider_name,
                    error=str(exc),
                )
            except Exception as exc:
                last_error = exc
                logger.error(
                    "Route provider error, trying next",
                    provider=provider.provider_name,
                    error=str(exc),
                )
        # All providers failed — return mock as last resort
        logger.error("All route providers failed; returning mock estimate", error=str(last_error))
        return await MockRouteProvider().compute_route(request)
