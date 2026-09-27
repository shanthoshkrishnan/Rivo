"""
RIVO Backend — Authorized Commercial Partner Rental Provider Placeholder
========================================================================
Implements RentalProvider for commercial real estate partner APIs (e.g. Magicbricks,
99acres, NoBroker, CREDAI) under formal bilateral agreement.

Status: NOT_CONFIGURED
- This provider does NOT scrape or impersonate browsers.
- Remains inactive until actual commercial API keys or syndicated feeds are provided.
- Demonstrates pluggable interface compliance without violating external ToS.
"""
from __future__ import annotations

from typing import List, Optional

from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.schemas.rental import RentalListingCreate, RentalSearchParams
from app.services.providers.base import RentalProvider


class AuthorizedPartnerRentalProvider(RentalProvider):
    """
    Placeholder adapter for authorized commercial partner feeds.
    Remains unavailable until official credentials and feed URLs are configured.
    """

    PROVIDER_NAME = "authorized_partner"

    def __init__(self, partner_name: str = "CREDAI / Partner Syndicate") -> None:
        self._partner_name = partner_name
        self._status = "NOT_CONFIGURED"

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        # Strictly False until official feed credentials exist
        return False

    def health(self) -> dict:
        return {
            "provider": self.provider_name,
            "status": self._status,
            "available": False,
            "reason": "Requires bilateral enterprise/partner API credentials. Scraping is strictly prohibited.",
            "freshness": DataFreshness.LIVE.value,
        }

    def freshness(self) -> DataFreshness:
        return DataFreshness.LIVE

    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        if not self.is_available():
            logger.debug("[PARTNER RENTAL] Provider inactive: %s", self._status)
            return []
        return []

    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        return None
