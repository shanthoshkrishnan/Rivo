# RIVO — PHASE 8 REAL RENTAL INVENTORY REPORT
## Legitimate Rental Data Architecture, First-Party Listings, & Deduplication
**Team CLAIRES | ST1010 | PS-11-S3 | Chennai Pilot**  
**Date**: September 27, 2026  
**Status**: VERIFIED & COMPLETE  

---

## 1. Executive Summary

Phase 8 tackled the core product problem of rental data authenticity for the Chennai Pilot. RIVO's routing, transit accessibility, affordability, and family layers were already operational, but rental data relied primarily on station-anchored seed fixtures.

Rather than building brittle or legally compromised web scrapers that violate portal Terms of Service or harvest personal data, Phase 8 implemented a **legitimate multi-tier rental architecture**:
1. **RIVO Direct Listing Provider**: A fully functional first-party owner/landlord submission path (`POST /api/v1/rentals/direct`) with Chennai bounding box validation, explicit publishing consent, and instant search integration.
2. **Provider Registry (`RentalProviderRegistry`)**: Multi-tier provider coordination with priority:
   `Authorized Partner -> RIVO Direct (Live) -> Recent Cache -> Open Periodic Data -> Demo Seed`.
3. **Cross-Provider Deduplication Engine**: Detects near-duplicates within 50m, identical BHK, and rent within ±10%, clustering duplicates and electing a canonical listing.
4. **Availability & Verification States**: Distinct status tracking (`AVAILABLE`, `PENDING_CONFIRMATION`, `RECENTLY_SEEN`, `UNAVAILABLE`) and verification levels (`UNVERIFIED`, `LOCATION_VERIFIED`, `OWNER_ATTESTED`, `RIVO_VERIFIED`).
5. **Transparent Demo Separation**: When only demo data is present, the UI clearly displays: *"Live rental inventory is unavailable. Showing 88 seeded Chennai listings for demonstration."* When live listings exist, it separates counts (e.g. *X current listings + Y demo listings*).
6. **Empirical Market Summary**: `GET /api/v1/rentals/market-summary` computes actual median, p25, and p75 asking rents, with an `insufficient_data` guard when sample size is below 5.

---

## 2. Rental Source Status Table

| Source | Listings | Freshness | Availability | Legitimacy | Active |
|---|---|---|---|---|---|
| **Authorized Partner** | 0 | `LIVE` | Programmatic API | Licensed / Bilateral Contract | NO (Placeholder: `NOT_CONFIGURED`) |
| **RIVO Direct** | Dynamic | `LIVE` | Real-time Owner Verified | First-Party Consent | **YES** |
| **Open Dataset** | 88 | `PERIODIC` | Quarterly / Seed Sync | Open Government Data / CC | **YES** |
| **Demo Seed** | 88 | `ESTIMATED` / `PERIODIC` | Corridor Seed | Internal Model Fixture | **YES** |

---

## 3. Provider Architecture & Registry Prioritization

```
                       RENTAL SEARCH REQUEST
                                 │
                                 ▼
                     RentalProviderRegistry
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
   1. Authorized Partner   2. RIVO Direct         3. Open Dataset
      (Status: Inactive)      (Live Owner Feed)      (Periodic Open Data)
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 │
                                 ▼
                       4. Demo Seed Fallback
                   (CMRL 88 Corridor Listings)
                                 │
                                 ▼
               Chennai Spatial Bounding Box Filter
                   [12.75N - 13.35N, 80.00E - 80.35E]
                                 │
                                 ▼
               Cross-Provider Deduplication Engine
               (50m proximity + same BHK + rent ±10%)
                                 │
                                 ▼
                      Recommendation Pipeline
```

---

## 4. Providers Requiring Authorization vs Available Immediately

- **Providers Requiring Enterprise Partnership (`NOT_CONFIGURED`)**:
  - Magicbricks Partner Affiliate API
  - 99acres Developer API (Info Edge)
  - NoBroker Developer API
  - CREDAI Chennai Syndicated MLS XML/JSON Feed
  - *Documentation created: [`docs/RENTAL_PROVIDER_RESEARCH.md`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/docs/RENTAL_PROVIDER_RESEARCH.md)*.
- **Providers Available & Active Immediately**:
  - `RivoDirectListingProvider`: Native first-party owner/agent listing intake.
  - `OpenDatasetRentalProvider`: Ingests open civic housing surveys.
  - `MockRentalProvider`: 88 CMRL station-anchored seed properties with honest metadata.

---

## 5. First-Party RIVO Direct Listings (`POST /api/v1/rentals/direct`)

- **Payload Requirements**: Locality, coordinates, asking rent, maintenance, deposit, BHK, sqft, furnishing, property type, availability, and mandatory `consent_to_publish`.
- **Integrity Validation**:
  - Verifies coordinates fall inside Chennai pilot bounds (`12.75 <= lat <= 13.35` and `80.00 <= lon <= 80.35`). Out-of-bounds coordinates return HTTP 422.
  - Rejects submissions where `consent_to_publish=false` with HTTP 400.
  - Automatically assigns unique canonical ID: `RIVO-DIR-xxxxxxxx`.
  - Normalizes furnishing, BHK, rent, and locality.
  - Stamps `data_freshness = DataFreshness.LIVE`, `verification_status = VerificationStatus.OWNER_ATTESTED`, and `geocode_confidence = ConfidenceLevel.HIGH`.
  - Immediately searchable via `/api/v1/rentals/search` and `/api/v1/recommendations/search`.

---

## 6. Freshness & Availability Lifecycle

- **Data Freshness**:
  - `LIVE`: Retrieved directly from active provider or submitted directly to RIVO.
  - `RECENT`: Verified within permitted cache TTL (up to 24–72 hours).
  - `PERIODIC`: Open government dataset or periodic corridor seed.
  - `ESTIMATED`: Demo/synthetic fixture.
- **Availability Status**:
  - `AVAILABLE`: Actively confirmed on market.
  - `PENDING_CONFIRMATION`: Deposit in discussion or under review.
  - `RECENTLY_SEEN`: Seen within past 7 days, awaiting confirmation.
  - `UNAVAILABLE`: Rented or delisted.
  - `UNKNOWN`: Unconfirmed status.
- **Verification Level**:
  - `UNVERIFIED` -> `LOCATION_VERIFIED` -> `OWNER_ATTESTED` -> `RIVO_VERIFIED`.

---

## 7. Deduplication Algorithm Verification

- **Algorithm**:
  - Group by `(provider, listing_id)` (exact match).
  - Group by `url_hash`.
  - Group by coordinate distance `<= 50m`, identical `bhk`, and rent ratio `<= 1.10` (±10%).
- **Cluster Output**:
  - All matching records receive a shared `duplicate_cluster_id`.
  - Exactly one listing is marked `is_canonical = True` (prioritizing the most recently observed valid source).

---

## 8. Empirical Market Summary (`GET /api/v1/rentals/market-summary`)

- Returns:
  - `listings_observed`
  - `median_asking_rent`
  - `rent_p25`
  - `rent_p75`
  - `median_by_bhk` (e.g. `{1: 12000, 2: 18000, 3: 28000}`)
  - `median_by_locality` (e.g. `{"velachery": 16500, "adyar": 22000}`)
- **Insufficient Data Guard**:
  - If fewer than 5 live observations exist, returns `insufficient_data = True` to prevent misleading statistical claims.

---

## 9. Admin Dashboard Metrics (`GET /api/v1/rentals/admin/summary`)

Provides administrative oversight:
- `total_listings`, `current_listings`, `periodic_listings`, `demo_listings`, `stale_listings`, `unknown_availability`.
- `provider_health`: Health status of each provider in the registry.
- `records_ingested` and `last_refresh`.

---

## 10. Frontend Integration

1. **Clear Demo Banner**:
   - Displays alert banner when only demo data is present: *"Live rental inventory is unavailable. Showing 88 seeded Chennai listings for demonstration."*
   - Displays breakdown when live listings exist: *"X current listings + Y demo listings available"*.
2. **Card Badges**:
   - Availability badge (`AVAILABLE` / `RECENTLY_SEEN`).
   - Rental source indicator (`RIVO Direct (Live)` vs `Rental: PERIODIC (Seeded)`).
   - Geocode confidence tag (`Geo: HIGH / MED`).
3. **Detail Modal**:
   - Section 4 explicitly displays verification level, rental source, geocode confidence, and observation timestamp.

---

## 11. Verification Results

- **Backend Unit & Integration Tests**:
  - `pytest tests/unit tests/integration`
  - **116 passed** in 7.75s with **0 live Google API calls**.
  - All Phase 8 tests in `test_phase8_rental_inventory.py` passed (13/13).
- **Live Test Gating**:
  - `pytest tests/live`
  - **8 skipped** cleanly by default (`RIVO_LIVE_API_TESTS=false`).
- **Frontend Compilation**:
  - `npm run build`
  - TypeScript and Vite build succeeded in 658ms with **0 errors**.
- **Google Quota Untouched**: No external Google Routes or Google Places calls were made.

---

## 12. Conclusion & Next Phase

With Phase 8 complete:
- RIVO possesses a legitimate, fully functional first-party listing mechanism.
- The multi-tier provider registry handles authorized partners, direct owners, and open civic data without scraping.
- Seed listings remain transparently labelled as demo fixtures.
- **Next Phase**: With legitimate rental observation collection in place, rent prediction modeling (XGBoost/LightGBM spatial rent surface) can be developed safely in Phase 9.
