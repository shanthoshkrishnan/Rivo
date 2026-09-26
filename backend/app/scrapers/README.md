# `app/scrapers/` — Safe Web Scrapers

This package provides a **robots.txt-respecting, rate-limited scraping framework** and specific scrapers for open government data sources.

---

## ⚠ Legal notice

> **Do not create a direct scraper unless the source terms/permission permit it.**
> — DATA_SOURCES.md

Every scraper in this package MUST document its legal basis in its class docstring. The `SafeScraper` base class enforces:
1. `robots.txt` compliance — fetch is blocked if disallowed
2. Rate limiting — minimum 2 second delay per domain
3. Audit logging — every HTTP request is logged with URL, status, and byte count

---

## Files

### `base.py`

#### `RobotsChecker`

Fetches and caches `robots.txt` per domain. Returns `True` only if the configured `User-Agent` (`RIVOBot/1.0`) is allowed to fetch the given URL.

```python
checker = RobotsChecker()
if await checker.can_fetch("https://example.com/page"):
    # safe to proceed
```

**Conservative default**: if `robots.txt` is unreachable, assumes **disallowed**.

#### `RateLimiter`

Enforces a minimum delay between requests to the same domain (default 2 seconds).

#### `SafeScraper`

Abstract base class. Subclasses must:
1. Define `BASE_URL`
2. Document the legal basis in the class docstring
3. Implement `parse_page(html, url) -> list`

```python
class MyOpenDataScraper(SafeScraper):
    """
    Legal basis: Open Government Data License India (OGDL).
    Reference: https://data.gov.in/terms-conditions
    """
    BASE_URL = "https://mydata.gov.in"

    def parse_page(self, html: str, url: str) -> list:
        soup = BeautifulSoup(html, "lxml")
        # ... extract data ...
        return records
```

---

### `ogd_scrapers.py`

#### `ChennaiHealthOGDScraper`

Fetches hospital records from the Chennai Health Infrastructure OGD API.

- **Source**: https://ap.data.gov.in/catalog/health-infrastructure-chennai
- **License**: Open Government Data License India (OGDL)
- **Attribution**: Government of Tamil Nadu / data.gov.in
- **Freshness**: PERIODIC

```python
scraper = ChennaiHealthOGDScraper(api_key="optional")
hospitals = await scraper.fetch_hospitals(limit=500)
# Returns: [{facility_id, name, facility_type, bed_count, nurse_count, lat, lon, ...}]
```

Output includes `source_name`, `source_url`, and `retrieved_at` on every record — required by `DATA_LICENSES.md`.

#### `GTFSFeedFetcher`

Downloads and parses CUMTA GTFS zip feed.

- **Source**: https://opendata.cumta.org/
- **License**: Verify feed-specific terms and attribution

```python
fetcher = GTFSFeedFetcher()
files = await fetcher.download("https://opendata.cumta.org/...")
stops = fetcher.parse_stops(files["stops.txt"])
```

Returns GTFS stops as list of dicts with `stop_id`, `stop_name`, `stop_lat`, `stop_lon`.

---

## Forbidden uses

- Do NOT scrape rental portals without written permission or explicit ToS allowance
- Do NOT store raw personal data (phone numbers, names from listings)
- Do NOT disable rate limiting or robots.txt checking
- Do NOT redistribute scraped data unless the license permits it

---

## Adding a new scraper

1. Create `scrapers/my_scraper.py`
2. Subclass `SafeScraper`
3. Document the **legal basis** in the class docstring
4. Set `BASE_URL` and `MIN_DELAY_SECONDS`
5. Implement `parse_page()`
6. Add a test in `tests/unit/test_scrapers.py` using a mock HTTP client
