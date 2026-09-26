"""
RIVO Backend — Open Government Data (OGD) Scrapers
====================================================
Scrapers for publicly available, openly licensed government data sources.

Legal basis:
  - data.gov.in uses the National Data Sharing and Accessibility Policy
    (NDSAP) / Open Government Data License India, which permits
    automated access and reuse with attribution.
    Reference: https://data.gov.in/terms-conditions

  - All records are tagged with source, attribution, and retrieval date.
  - Raw data is NOT republished; only processed records enter the DB.

Scrapers implemented here:
  1. ChennaiHealthOGDScraper  — hospital / health facility data
  2. GTFSFeedFetcher           — CUMTA GTFS transit feed

For rental data, see app/services/providers/ (never scrape rentals
without explicit ToS permission).
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.logging import logger
from app.scrapers.base import SafeScraper

# ─────────────────────────────────────────────────────────────────────────────
# Chennai Health Infrastructure OGD
# ─────────────────────────────────────────────────────────────────────────────

# Source: https://ap.data.gov.in/catalog/health-infrastructure-chennai
# License: Open Government Data License India (OGDL)
# Attribution: data.gov.in / Government of Tamil Nadu
HEALTH_OGD_API = "https://api.data.gov.in/resource/hospitals-chennai"


class ChennaiHealthOGDScraper(SafeScraper):
    """
    Fetches Chennai health infrastructure records from data.gov.in OGD API.

    Legal basis: Open Government Data License India (OGDL).
    Reference: https://data.gov.in/terms-conditions

    Output schema per record:
        facility_id, name, facility_type, bed_count, nurse_count,
        latitude, longitude, address, source_name, retrieved_at
    """

    BASE_URL = "https://api.data.gov.in"
    MIN_DELAY_SECONDS = 1.0

    def __init__(self, api_key: Optional[str] = None) -> None:
        super().__init__()
        self._api_key = api_key   # data.gov.in API key (free registration)

    async def fetch_hospitals(
        self,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch hospital records from OGD API.
        Returns a list of normalised hospital dicts.

        NOTE: The exact field names depend on the live API schema.
        Always validate against the source before storing.
        """
        params = {"format": "json", "limit": limit, "offset": offset}
        if self._api_key:
            params["api-key"] = self._api_key

        url = f"{HEALTH_OGD_API}?" + "&".join(f"{k}={v}" for k, v in params.items())
        html = await self._fetch(url)
        if not html:
            return []

        try:
            data = json.loads(html)
            records = data.get("records", [])
            now = datetime.now(timezone.utc).isoformat()
            results = []
            for rec in records:
                # Field names are approximate — adapt to actual API response
                results.append({
                    "facility_id": str(rec.get("id", "")),
                    "name": rec.get("hospital_name") or rec.get("name", "Unknown"),
                    "facility_type": rec.get("type") or rec.get("facility_type"),
                    "bed_count": self._safe_int(rec.get("beds") or rec.get("bed_count")),
                    "nurse_count": self._safe_int(rec.get("nurses") or rec.get("nurse_count")),
                    "latitude": self._safe_float(rec.get("latitude") or rec.get("lat")),
                    "longitude": self._safe_float(rec.get("longitude") or rec.get("long")),
                    "address": rec.get("address"),
                    "source_name": "Chennai Health Infrastructure OGD",
                    "source_url": "https://ap.data.gov.in/catalog/health-infrastructure-chennai",
                    "data_freshness": "PERIODIC",
                    "retrieved_at": now,
                })
            logger.info("ChennaiHealthOGDScraper fetched", count=len(results))
            return results
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Health OGD parse error", error=str(exc))
            return []

    def parse_page(self, html: str, url: str) -> list:
        # Raw parse handled in fetch_hospitals; not used via base scrape()
        try:
            return json.loads(html).get("records", [])
        except Exception:
            return []

    @staticmethod
    def _safe_int(val: Any) -> Optional[int]:
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        try:
            return float(val)
        except (TypeError, ValueError):
            return None


# ─────────────────────────────────────────────────────────────────────────────
# CUMTA GTFS Feed Fetcher
# ─────────────────────────────────────────────────────────────────────────────

# Source: https://opendata.cumta.org/
# License: Check CUMTA feed-specific terms and attribution (vary by feed)
CUMTA_GTFS_FEED_URL = "https://opendata.cumta.org/dataset/download/gtfs"   # placeholder


class GTFSFeedFetcher:
    """
    Downloads and extracts a GTFS zip feed from CUMTA.

    Unlike the SafeScraper base class, GTFS is downloaded as a zip file
    from an official open-data endpoint — not scraped from HTML.

    Returns parsed dicts for the minimum required GTFS files:
      stops, routes, trips, stop_times, calendar, calendar_dates

    Legal basis: CUMTA open data portal (verify feed-specific terms).
    Reference: https://opendata.cumta.org/
    """

    USER_AGENT = "RIVOBot/1.0"

    async def download(self, feed_url: str = CUMTA_GTFS_FEED_URL) -> Optional[Dict[str, bytes]]:
        """
        Download GTFS zip and return {filename: content_bytes} dict.
        Returns None if download fails.
        """
        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                headers={"User-Agent": self.USER_AGENT},
                follow_redirects=True,
            ) as client:
                resp = await client.get(feed_url)
                resp.raise_for_status()
                logger.info(
                    "GTFS feed downloaded",
                    url=feed_url,
                    bytes=len(resp.content),
                )
                files: Dict[str, bytes] = {}
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    for name in zf.namelist():
                        files[name] = zf.read(name)
                return files
        except Exception as exc:
            logger.error("GTFS download failed", url=feed_url, error=str(exc))
            return None

    def parse_stops(self, stops_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse stops.txt CSV into list of dicts."""
        import csv
        stops = []
        reader = csv.DictReader(io.StringIO(stops_bytes.decode("utf-8-sig")))
        for row in reader:
            stops.append({
                "stop_id": row.get("stop_id", ""),
                "stop_code": row.get("stop_code"),
                "stop_name": row.get("stop_name", ""),
                "stop_lat": float(row["stop_lat"]) if row.get("stop_lat") else None,
                "stop_lon": float(row["stop_lon"]) if row.get("stop_lon") else None,
                "stop_desc": row.get("stop_desc"),
                "location_type": int(row["location_type"]) if row.get("location_type") else 0,
                "parent_station": row.get("parent_station"),
                "wheelchair_boarding": (
                    int(row["wheelchair_boarding"]) if row.get("wheelchair_boarding") else None
                ),
            })
        logger.info("GTFS stops parsed", count=len(stops))
        return stops
