# RIVO — Legitimate Rental Data Source Plan

**Team CLAIRES | ST1010 | PS-11-S3**  
**Document**: Architectural & Operational Plan for Real Rental Inventory  
**Version**: 1.0 (Phase 7 Post-Quota Optimization)  

---

## 1. Executive Summary & Core Principle

A core tenet of RIVO is absolute truthfulness regarding data provenance:
- **Never manufacture live data.**
- **Never connect unauthorized scrapers or violate terms of service of commercial real estate portals (e.g., MagicBricks, 99acres, NoBroker).**
- **Clearly label current CMRL-anchored 88 listings as `PERIODIC` / `ESTIMATED` ("Demo / seeded dataset").**

This document evaluates legitimate, authorized, and compliant paths for scaling RIVO Home's rental inventory across Chennai's key transit and employment corridors.

---

## 2. Evaluation of Candidate Data Providers

| Candidate Source | Mechanism | Legal & Terms Compliance | Chennai Coverage | Freshness | Technical Effort | Feasibility Status |
|------------------|-----------|--------------------------|------------------|-----------|------------------|-------------------|
| **Commercial Real Estate Portal Partner APIs** (e.g. Magicbricks/99acres B2B Partner API) | Formal B2B REST/JSON Partner API | 100% compliant under formal partner agreement | High (city-wide, all BHKs) | `LIVE` / daily sync | Medium (REST adapter + API key) | **Primary Target** for commercial pilot |
| **Open City / Civic Data Rental Feeds (OpenCity.in / GCC Data)** | Open Data Portal CSV/GeoJSON | Permissive Open Government / Creative Commons | Medium (municipal & public housing) | `PERIODIC` (quarterly/annual) | Low (direct DuckDB/PostGIS loader) | **Active Secondary** |
| **Direct Broker / Cooperative Housing Society API** (CREDAI Chennai / Builders Assn) | Syndicated XML/JSON MLS Feed | Direct bilateral contract / MOU | High in newly built transit corridors (OMR, GST, Ambattur) | `LIVE` / weekly updates | Medium (feed parser + normalization) | **High Feasibility** |
| **Crowdsourced & Verified Community Listings** (RIVO Tenant Direct Submit) | RIVO Self-Serve Listing Portal | Full 1st-party consent & user verification | Focused on key worker hubs (Government Hospitals, IT Parks, Industrial corridors) | `LIVE` | Low (already supported by schema) | **Immediate Pilot Next Step** |
| **Web Scraping without Authorization** | Automated HTML extractors | **STRICTLY PROHIBITED** (violates ToS, legal exposure, rate-limit bans) | Volatile | Unstable | High (breaks constantly) | **REJECTED** |

---

## 3. Recommended Path: Dual-Track Integration

### Track A: Commercial B2B Partner / MLS Syndicate Feed (Primary)
- **Target Partners**: CREDAI Chennai, NoBroker Developer/Broker Network API, or Magicbricks B2B Affiliate Feed.
- **Contract Type**: Bilateral API Partner License for Public Interest / Urban Planning Research.
- **Data Delivery**: Webhook on listing publish/update, or nightly delta sync via authorized SFTP/REST API.

### Track B: Verified Civic / GCC Open Rental Seed + Community Verification (Immediate)
- **Target Feeds**: Chennai Open Data Initiative (GCC Ward-level rental surveys), Slum Clearance Board / TNSCB public housing rosters, university student housing boards.
- **Data Delivery**: Periodic CSV / GeoJSON ingestion into PostGIS, labelled transparently as `PERIODIC`.

---

## 4. Required Schema & Field Alignment

Every provider feed maps directly to `RentalListingCreate` ([`app.schemas.rental`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/schemas/rental.py)):

```
Provider Feed Record
       ↓
Canonical Normalizer (clean strings, parse coordinates, extract BHK & rent)
       ↓
Deduplication Engine (ID hash, lat/lon proximity within 50m)
       ↓
PostGIS / In-Memory Seed Storage (with data_freshness tag)
```

### Essential Fields
- `listing_id`: Unique provider ID with provider prefix (`CREDAI-CH-10294`)
- `locality_normalized`: Lowercase trimmed canonical Chennai locality
- `latitude`, `longitude`: WGS-84 coordinates
- `rent_monthly`: Asking rent in INR (₹)
- `bhk`: Bedrooms count (0 = Studio, 1, 2, 3+)
- `is_available`: Boolean status
- `observed_at`: Ingestion timestamp
- `source_name`: Display attribution (e.g. "CREDAI Chennai Transit Corridor Feed")

---

## 5. Licensing, Attribution, & Caching Governance

1. **Licensing**:
   - Provider must grant programmatic consumption rights for housing-transit accessibility indexing.
   - User-facing displays must include the required attribution mark and provider listing ID.
2. **Attribution**:
   - Shown on every search card and detailed modal: `Rental source: <Provider Name> (<Freshness>)`.
   - Never overwrite provider attribution with "RIVO Verified" unless independently field-inspected.
3. **Caching Limits**:
   - Listings may be cached locally in SQLite/PostGIS for up to **7 days**.
   - Availability check must be refreshed before a user commits to viewing details.
   - De-listed properties must be purged or marked `is_available = False` upon daily delta receipt.

---

## 6. Integration Architecture & Effort Estimate

```
[Candidate Feed / API]
         │ (HTTP / Webhook / SFTP)
         ▼
[app/services/providers/rental_partner.py] (Implements RentalProvider)
         │
         ├── normalize_fields()
         ├── filter_hard_constraints()
         └── assign_freshness(DataFreshness.LIVE or PERIODIC)
         ▼
[RecommendationService]
```

- **Engineering Effort**: 12–16 developer hours (adapter implementation, unit tests, mock fixtures, schema validator).
- **Fallback Strategy**: If partner API is unreachable, automatically fall back to `MockRentalProvider` (CMRL seed) with freshness degraded to `PERIODIC` or `ESTIMATED`.

---

## 7. Conclusion

By enforcing this plan, RIVO maintains zero legal ambiguity, avoids scraping bans, upholds the non-negotiable hackathon rule against manufacturing live data, and guarantees that users and city planners can trust every rupee and commute minute displayed on screen.
