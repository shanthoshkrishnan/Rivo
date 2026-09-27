# RIVO — Rental Provider Integration Requirements

**Team CLAIRES | ST1010 | PS-11-S3**  
**Component**: Rental Data Ingestion Architecture  
**Document Version**: 1.0 (Phase 5)

---

## 1. Overview & Objective

To transition RIVO Home from station-anchored seed fixtures to continuous current market data, an authorized rental source must be connected. This document defines the exact technical, legal, and operational specifications for integrating a new rental feed into RIVO's pluggable `RentalProvider` interface.

---

## 2. Pluggable Interface Contract

Any candidate rental provider MUST implement the `RentalProvider` abstract base class defined in [`app.services.providers.base`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/providers/base.py):

```python
class RentalProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Machine-readable provider identifier (e.g. 'licensed', 'magicbricks_partner')."""

    @abstractmethod
    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]:
        """
        Search for rental listings matching the given parameters.
        Must apply hard constraints before returning.
        Must set data_freshness on every listing.
        Must return [] on empty (never raise).
        """

    @abstractmethod
    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]:
        """Fetch a single listing by provider-specific ID."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider backend is currently reachable and authenticated."""
```

---

## 3. Required Schema & Fields

Every incoming listing record must be mapped into `RentalListingCreate` ([`app.schemas.rental`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/schemas/rental.py)):

| Field | Type | Mandatory? | Constraints & Description |
|---|---|---|---|
| `listing_id` | `str` | **Yes** | Unique provider-assigned identifier (e.g., `PROP-98214`). |
| `provider` | `str` | **Yes** | Provider slug matching `RentalProvider.provider_name`. |
| `city` | `str` | **Yes** | Fixed to `"Chennai"` for the PS-11-S3 pilot. |
| `locality_raw` | `str` | **Yes** | Original neighbourhood name as listed (e.g., `"Velachery, Vijayanagar"`). |
| `locality_normalized` | `str` | **Yes** | Canonical lowercase trimmed locality without punctuation. |
| `latitude` | `float` | **Yes** | WGS-84 coordinate (-90.0 to 90.0). |
| `longitude` | `float` | **Yes** | WGS-84 coordinate (-180.0 to 180.0). |
| `rent_monthly` | `float` | **Yes** | Non-negative monthly asking rent in INR (₹). |
| `maintenance_monthly`| `float` | No | Additional monthly maintenance charge in INR (defaults to 0.0). |
| `deposit` | `float` | No | Security deposit in INR. |
| `brokerage` | `float` | No | Broker fee in INR. |
| `bhk` | `int` | **Yes** | Integer bedrooms/hall/kitchen count (1 to 10; Studio = 0). |
| `area_sqft` | `float` | No | Super built-up or carpet area in square feet. |
| `furnishing` | `str` | No | Canonical enum: `"unfurnished"`, `"semi-furnished"`, `"fully-furnished"`. |
| `property_type` | `str` | No | Canonical enum: `"flat"`, `"house"`, `"pg"`, `"studio"`. |
| `is_available` | `bool` | **Yes** | Current listing availability status (`True` = active). |
| `observed_at` | `datetime`| **Yes** | UTC timestamp when this listing state was retrieved. |
| `source_name` | `str` | **Yes** | Human-readable attribution name (e.g., `"Partner Rental Network"`). |
| `source_url` | `str` | No | Permitted canonical URL for auditability. |
| `data_freshness` | `DataFreshness`| **Yes** | `LIVE` (if direct real-time API) or `RECENT` (if within TTL). |

---

## 4. Geocoding Requirements

1. **Explicit Coordinates Required**:
   - The recommendation pipeline strictly drops listings where `latitude` or `longitude` is missing (`_score_listing` requires coordinates for routing).
2. **Reverse / Forward Geocode Validation**:
   - Coordinates must fall strictly within the Greater Chennai Metropolitan Area (CMA) bounding box:
     * Latitude: `12.80` to `13.30`
     * Longitude: `79.95` to `80.35`
3. **Imprecise Coordinates**:
   - If only a locality name is provided, coordinate centroids must be assigned a `geocode_confidence: LOW` tag and must not be falsely declared as exact rooftop coordinates.

---

## 5. Deduplication & Cross-Source Reconciliation

To prevent the same apartment listed on multiple portals from biasing the recommendation engine:
1. **Cluster Identification** ([`app.services.algorithms.normalization`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/algorithms/normalization.py)):
   - Exact `listing_id` + `provider` match $\rightarrow$ update existing record.
   - Exact `url_hash` match $\rightarrow$ merge cluster.
   - Spatial Proximity $\le 50\text{ m}$ AND same `bhk` AND rent within $\pm 10\%$ $\rightarrow$ assign common `duplicate_cluster_id`.
2. **Canonical Selection**:
   - Only the most recently observed listing in each cluster is marked `is_canonical = True`.

---

## 6. Freshness & Provenance Rules

- **LIVE**: Only direct real-time partner API responses obtained during the active session.
- **RECENT**: Cached partner API listings within a 15-minute TTL.
- **PERIODIC**: Authorized batch feeds or GTFS-anchored snapshots updated on a recurring schedule.
- **ESTIMATED**: Synthetic, mock, or fallback listings.
- **Prohibition**: Synthetic fallback data must NEVER be labelled `LIVE` or `RECENT`.

---

## 7. Cache & Rate-Limiting Policy

- **Rental Cache TTL**: 900 seconds (15 minutes).
- **Hard Request Throttling**: Batch refreshes must be rate-limited to avoid degrading partner systems.
- **Circuit Breakers**: If a third-party feed errors or returns HTTP 429/5xx, RIVO enters graceful fallback mode to cached/seed data without wiping working memory.

---

## 8. Legal, Ethical & Data License Boundaries

Per project non-negotiable rules and [DATA_LICENSES.md](file:///c:/Project/Hackathons/Sustain-a-thon/Code/DATA_LICENSES.md):
1. **No Unauthorized Scraping**: Direct scraping of real estate web portals is strictly prohibited unless explicit written authorization or an API partner agreement exists.
2. **Respect Access Controls**: Never bypass CAPTCHA, authentication walls, Cloudflare challenges, or robots.txt disallow directives.
3. **No Personal PII**: Do NOT harvest, store, or display landlords' or tenants' personal telephone numbers, personal email addresses, or tenant identity proofs.
4. **Attribution**: Every listing displayed in RIVO Home must clearly present `Source: <source_name>` and `Observed: <observed_at>`.
