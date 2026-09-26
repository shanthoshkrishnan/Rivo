"""
RIVO Backend — Scraping Safety Framework
==========================================
IMPORTANT LEGAL NOTICE
-----------------------
Scraping a website without explicit permission from its Terms of Service
is potentially illegal and unethical.  RIVO's policy (from DATA_SOURCES.md):

  "Do not create a direct scraper unless the source terms/permission permit it."

This module provides:
  1. A robots.txt checker — ALWAYS respect robots.txt before scraping.
  2. A rate-limiter — polite delay between requests.
  3. A safe scraping base class — enforces both before any fetch.
  4. Clear audit logging of every request made.

Use this framework ONLY for sources that:
  - Explicitly permit scraping in their ToS, OR
  - Are licensed under an open license that permits automated access, OR
  - You have written permission from the operator.

For rental data specifically, use RentalProvider adapters instead of
scraping — see app/services/providers/.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.core.logging import logger


# ─────────────────────────────────────────────────────────────────────────────
# Robots.txt compliance
# ─────────────────────────────────────────────────────────────────────────────
class RobotsChecker:
    """
    Fetches and parses robots.txt for a given base URL.
    Caches the result per domain to avoid repeated fetches.

    Usage:
        checker = RobotsChecker()
        if await checker.can_fetch("https://example.com/page"):
            ...  # safe to proceed
    """

    def __init__(self, user_agent: str = "RIVOBot/1.0") -> None:
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    async def _get_parser(self, base_url: str) -> RobotFileParser:
        if base_url in self._cache:
            return self._cache[base_url]
        robots_url = urljoin(base_url, "/robots.txt")
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(robots_url)
                rp.parse(resp.text.splitlines())
                logger.info("Fetched robots.txt", url=robots_url, status=resp.status_code)
        except Exception as exc:
            logger.warning(
                "Could not fetch robots.txt — assuming disallowed",
                url=robots_url,
                error=str(exc),
            )
            # Conservative: assume disallowed if robots.txt unreachable
            rp.parse(["User-agent: *", "Disallow: /"])
        self._cache[base_url] = rp
        return rp

    async def can_fetch(self, url: str) -> bool:
        """
        Return True only if robots.txt permits fetching this URL
        for our user agent.
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        parser = await self._get_parser(base_url)
        allowed = parser.can_fetch(self._user_agent, url)
        if not allowed:
            logger.warning("robots.txt disallows fetch", url=url, ua=self._user_agent)
        return allowed


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiter (polite crawling)
# ─────────────────────────────────────────────────────────────────────────────
class RateLimiter:
    """
    Simple per-domain rate limiter.
    Enforces a minimum delay between requests to the same domain.
    """

    def __init__(self, min_delay_seconds: float = 2.0) -> None:
        self._min_delay = min_delay_seconds
        self._last_request: dict[str, float] = {}

    async def wait(self, domain: str) -> None:
        """Wait if necessary before making a request to the given domain."""
        last = self._last_request.get(domain, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < self._min_delay:
            wait_time = self._min_delay - elapsed
            logger.debug("Rate limiting", domain=domain, wait_seconds=round(wait_time, 2))
            await asyncio.sleep(wait_time)
        self._last_request[domain] = time.monotonic()


# ─────────────────────────────────────────────────────────────────────────────
# Safe scraper base class
# ─────────────────────────────────────────────────────────────────────────────
class SafeScraper:
    """
    Base class for any scraper in RIVO.

    Enforces:
      1. Legal basis check (robots.txt compliance)
      2. Rate limiting
      3. Audit logging of every request
      4. Conservative error handling

    Subclasses MUST:
      - Override `parse_page()` to extract data.
      - Set `BASE_URL` and `USER_AGENT`.
      - Document the legal basis for scraping in their class docstring.

    Example:
        class MyOpenDataScraper(SafeScraper):
            '''
            Scrapes MyOpenData.gov.in — licensed under NLDA/Open Government
            Data License India, which permits automated access.
            Reference: https://data.gov.in/terms-conditions
            '''
            BASE_URL = "https://myopendata.gov.in"
    """

    BASE_URL: str = ""
    USER_AGENT: str = "RIVOBot/1.0 (+https://rivo.claires.io/bot)"
    MIN_DELAY_SECONDS: float = 2.0

    def __init__(self) -> None:
        if not self.BASE_URL:
            raise ValueError(f"{self.__class__.__name__} must define BASE_URL")
        self._robots = RobotsChecker(user_agent=self.USER_AGENT)
        self._rate_limiter = RateLimiter(min_delay_seconds=self.MIN_DELAY_SECONDS)
        self._domain = urlparse(self.BASE_URL).netloc

    async def _fetch(self, url: str) -> Optional[str]:
        """
        Fetch a URL safely:
          1. Check robots.txt
          2. Rate limit
          3. Fetch with audit log
          4. Return text content or None on error
        """
        # Step 1: robots.txt check
        if not await self._robots.can_fetch(url):
            logger.error(
                "Scraping blocked by robots.txt — aborting",
                url=url,
                scraper=self.__class__.__name__,
            )
            return None

        # Step 2: rate limit
        await self._rate_limiter.wait(self._domain)

        # Step 3: fetch
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                },
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                logger.info(
                    "Scraper fetched",
                    scraper=self.__class__.__name__,
                    url=url,
                    status=resp.status_code,
                    bytes=len(resp.content),
                )
                return resp.text
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Scraper HTTP error",
                scraper=self.__class__.__name__,
                url=url,
                status=exc.response.status_code,
            )
        except Exception as exc:
            logger.error(
                "Scraper fetch error",
                scraper=self.__class__.__name__,
                url=url,
                error=str(exc),
            )
        return None

    def parse_page(self, html: str, url: str) -> list:
        """
        Override in subclass to extract structured data from HTML.
        Return a list of dicts matching the target schema.
        """
        raise NotImplementedError

    async def scrape(self, url: str) -> list:
        """Fetch and parse a single URL."""
        html = await self._fetch(url)
        if html is None:
            return []
        return self.parse_page(html, url)
