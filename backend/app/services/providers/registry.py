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
from app.services.providers.base import RentalProvider, RouteProvider
from app.services.providers.rental_mock import MockRentalProvider
from app.services.providers.route_google import GoogleRouteProvider, ProviderUnavailableError
from app.services.providers.route_mock import MockRouteProvider
from app.services.providers.route_otp import OTPRouteProvider

settings = get_settings()


@lru_cache(maxsize=1)
def get_rental_provider() -> RentalProvider:
    """
    Return the configured rental provider singleton.
    Falls back to MockRentalProvider if configuration is incomplete.
    """
    provider_name = settings.RENTAL_PROVIDER

    if provider_name == RentalProviderName.MOCK:
        logger.info("Rental provider: Mock (sample data)")
        return MockRentalProvider()

    if provider_name == RentalProviderName.OPEN_DATASET:
        try:
            from app.services.providers.rental_open_dataset import OpenDatasetRentalProvider
            logger.info("Rental provider: OpenDataset")
            return OpenDatasetRentalProvider()
        except ImportError:
            logger.warning("OpenDatasetRentalProvider not available; falling back to Mock")
            return MockRentalProvider()

    if provider_name in (RentalProviderName.LICENSED, RentalProviderName.AUTHORIZED_THIRD_PARTY):
        if not settings.LICENSED_RENTAL_API_KEY:
            logger.warning(
                "Licensed rental provider selected but API key missing; "
                "falling back to Mock"
            )
            return MockRentalProvider()
        try:
            from app.services.providers.rental_licensed import LicensedRentalProvider
            logger.info("Rental provider: Licensed")
            return LicensedRentalProvider()
        except ImportError:
            logger.warning("LicensedRentalProvider not available; falling back to Mock")
            return MockRentalProvider()

    logger.warning("Unknown rental provider %s; falling back to Mock", provider_name)
    return MockRentalProvider()


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
        if settings.google_routes_enabled:
            self._providers.append(GoogleRouteProvider())
            logger.info("Route provider chain: Google → OTP → Mock")
        else:
            logger.info("Route provider chain: OTP → Mock (Google key not set)")
        self._providers.append(OTPRouteProvider())
        self._providers.append(MockRouteProvider())

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
