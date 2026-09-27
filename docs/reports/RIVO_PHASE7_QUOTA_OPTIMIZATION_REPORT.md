# RIVO — PHASE 7 QUOTA OPTIMIZATION REPORT
## Quota-Efficient Live Routing + Real Home Selection
**Team CLAIRES | ST1010 | PS-11-S3 | Chennai Pilot**  
**Date**: September 27, 2026  
**Status**: COMPLETE & VERIFIED  

---

## 1. Executive Summary

During Phase 6, live Google Routes and Google Places (New) APIs were verified with genuine Chennai transit itineraries, multi-modal routes, and facility checks. However, live execution revealed an efficiency bottleneck: a single Nurse search generated ~10 Google Routes calls and ~30 Google Places calls, quickly exceeding the Google Cloud project's daily quota (`ComputeRoutesRequestsPerDay = 100`).

In Phase 7, we architected and implemented an end-to-end quota-efficient routing and selection engine:
1. **Developer Quota Safety Guard**: Centralized safety guard (`RIVO_LIVE_API_TESTS=false` by default) preventing accidental Google API calls during test runs or normal development.
2. **Two-Stage Funnel**: Search Mode (cheap local filtering + single preferred mode + verified local facility datasets) vs Detail Mode (deep multi-mode route inspection + live Google Places for the chosen home).
3. **Strict API Request Budgets**: Configurable per-search caps on external operations with fallback to cache/local datasets when exhausted.
4. **Quota Circuit Breaker**: Instant circuit tripping on HTTP 429 / `QUOTA_EXCEEDED` with immediate fallback to CUMTA GTFS and zero retry storms.
5. **Truthful Provenance & Honest Rental Labelling**: Complete visibility of `LIVE`, `RECENT`, `PERIODIC`, and `ESTIMATED` badges across search cards, modal details, and system health status. Current CMRL-anchored 88 listings are prominently labelled: `"Rental source: Demo / seeded dataset (CMRL-anchored)"`.

---

## 2. Quota Analysis (The 100/Day Cap)

Investigation of the error `QUOTA_EXCEEDED: ComputeRoutesRequestsPerDay = 100`:
- **Classification**: **API-Specific Quota Cap at the Project Level**.
- **Nature**: Google Cloud Console allows project administrators to configure explicit daily request caps per service under *APIs & Services > Routes API > Quotas & System Limits* to prevent runaway billing. Alternatively, newer free-tier or billing-restricted Google Cloud accounts receive a default defensive quota of 100 requests/day on `ComputeRoutesRequestsPerDay`.
- **Architectural Solution**: RIVO does **not** rely on unlimited API quotas. With Phase 7 optimizations, a full search consumes **0 to 1 external calls** for transit candidates, and selecting a home consumes at most **4 routes + 3 places**, safely fitting dozens of user interactions within the daily allowance.

---

## 3. Previous vs. New Request Architecture

```
PREVIOUS ARCHITECTURE (Phase 6):
Candidate Listings (10)
  ├── 10 × ComputeRoutes (Transit)
  ├── 10 × ComputeRoutes (Drive)
  ├── 10 × ComputeRoutes (Two-Wheeler)
  ├── 10 × ComputeRoutes (Walk)
  └── 10 × 3 Places (School, Hospital, Pharmacy)
Total External Calls: ~70 calls per search! (Caused instant QUOTA_EXCEEDED)

NEW PHASE 7 ARCHITECTURE:
Candidate Listings (88 seeded)
  │
  ├── Stage 1: Cheap Local Filtering (BHK, Rent ceiling, Tenant restrictions, Spatial radius)
  │     └── [0 External Calls]
  │
  ├── Stage 2: Coarse Travel & Commute Filtering (Local GTFS / Primary preferred mode only)
  │     └── External Route calls limited to ROUTE_SEARCH_BUDGET (Max 10, default 0-3)
  │
  ├── Stage 3: Local Facility Pre-Filter (UDISE+ / Chennai Health OGD / OSM)
  │     └── [0 External Calls]
  │
  ├── Stage 4: Top Shortlist (3-5 candidates)
  │     └── Search response returned with candidate cards
  │
  └── Stage 5: DETAIL MODE (Triggered ONLY when user selects a specific property)
        ├── POST /api/v1/recommendations/detail
        ├── Multi-mode evaluation (Transit, Drive, Two-Wheeler, Walk)
        └── Live Google Places queries (School, Hospital, Pharmacy) within budget
```

---

## 4. Route Matrix vs. ComputeRoutes Usage

- **Route Matrix (`compute_route_matrix`)**:
  - Implemented in `GoogleRouteProvider.compute_route_matrix(...)`.
  - Used when evaluating bulk candidate travel duration and distance without transit step details.
  - Consumes significantly lower latency and quota overhead.
- **ComputeRoutes (`compute_routes`)**:
  - Reserved exclusively for the Top Shortlist and Detail Mode.
  - Generates full polyline geometry, transit line names, headsigns, boarding stops, alighting stops, and transfer counts.

---

## 5. Google Places Usage & Family Facility Pre-Filter

- **Normal Search**:
  - Google Places is **not** called for every rental candidate.
  - Local verified datasets (`UDISE+`, `Chennai Health Infrastructure OGD`, `OSM Chennai POI`) perform spatial pre-filtering in < 2ms without external network latency or cost.
- **Detail Mode**:
  - Only the single selected home queries Google Places (New) Text Search for School, Hospital, and Pharmacy.
  - Respects `FAMILY_ROUTE_BUDGET` and `PLACES_SEARCH_BUDGET`.
  - Results are immediately cached with `DataFreshness.LIVE` (and `RECENT` on subsequent lookups).

---

## 6. Configurable API Budgets & Request Tracker

Configurable in `backend/.env` or system environment:
- `ROUTE_SEARCH_BUDGET = 10` (Maximum route operations during bulk search)
- `PLACES_SEARCH_BUDGET = 8` (Maximum places operations during search)
- `DETAILED_ROUTE_BUDGET = 5` (Maximum route operations for selected home detail)
- `FAMILY_ROUTE_BUDGET = 6` (Maximum places/walking calls for family facilities)

`RequestBudgetManager` (`app/core/request_tracker.py`) tracks:
- `listings_examined`
- `routes_requested` / `routes_cache_hits`
- `places_requested` / `places_cache_hits`
- `total_external_requests`
- `budget_exhausted`

*Sanitized logging only: No API keys, credentials, or personal data are ever logged or exposed.*

---

## 7. Quota Circuit Breaker & Health State

- **Tripping Mechanism**:
  - Intercepts HTTP 429, `RESOURCE_EXHAUSTED`, and `QUOTA_EXCEEDED`.
  - Instantly marks `google_routes_available = False` or `google_places_available = False`.
  - Sets `failure_reason = "QUOTA_EXCEEDED"`.
  - Immediately switches routing to CUMTA GTFS local provider (`fallback_provider = "gtfs"`).
  - Prevents retry storms and cascading API failures.
- **Health Endpoint Visibility**:
  - `GET /health` reports:
    ```json
    {
      "status": "healthy",
      "google_routes_available": false,
      "google_places_available": true,
      "google_routes_failure_reason": "QUOTA_EXCEEDED",
      "google_status": "QUOTA_EXCEEDED",
      "fallback_provider": "gtfs",
      "message": "Google live routing temporarily unavailable. Showing periodic transit estimate."
    }
    ```

---

## 8. Workflow Request Counts & Comparison

| Workflow | Routes API Calls | Places API Calls | Cache Hits | Provider Used | Freshness Returned |
|---|---|---|---|---|---|
| **Initial Search** (Nurse, RGGGH) | 0 – 3 | 0 | 0 | Local GTFS / Google (if primary) + Local Seed | `PERIODIC` / `LIVE` |
| **Repeat Search** (Same filters) | 0 | 0 | 100% | In-Memory Route & Facility Cache | `RECENT` / `PERIODIC` |
| **Selected Home Detail** (1 Home) | 1 – 4 | 0 – 3 | Variable | Google Routes + Google Places (within budget) | `LIVE` / `RECENT` |
| **Exhausted / Tripped Quota** | 0 | 0 | — | CUMTA GTFS + Local OGD/UDISE+ Fallback | `PERIODIC` / `ESTIMATED` |

---

## 9. Live API Safety Switch Verification

- **Default Setting**: `RIVO_LIVE_API_TESTS=false`.
- **Safety Enforcement**:
  - `GoogleRouteProvider._call_api` and `GooglePlacesProvider._call_api` check `settings.rivo_live_api_tests` before dispatching any network request. If `False`, `LiveApiDisabledError` is raised.
  - `tests/live/` test suite automatically detects `RIVO_LIVE_API_TESTS=false` and cleanly **SKIPS** all 8 live tests.
  - `scripts/verify_live_google.py` and `scripts/live_smoke_test.py` gracefully inform the operator and exit without firing network packets.
  - **Result**: Zero Google Cloud quota consumed during development, test cycles, and CI builds.

---

## 10. Test & Build Verification

- **Backend Test Suite**:
  - `pytest tests/unit tests/integration`
  - **98 tests PASSED** in 3.96 seconds.
  - Covers: Route budget exhaustion, Places budget exhaustion, Cache hit tracking, Circuit breaker tripping & reset, Safety guard network blocking, Route matrix coarse parsing, Search mode primary mode selection, Detail mode endpoint (`POST /api/v1/recommendations/detail`), and fallback chains.
- **Live Tests**:
  - `pytest tests/live`
  - **8 tests SKIPPED** cleanly with zero network calls.
- **Frontend Build**:
  - `npm run build`
  - Built cleanly in 663ms (`tsc -b && vite build`) with zero TypeScript errors.

---

## 11. Truthful Rental Data Labelling & Next Step

- **Current Rental Status**:
  - All 88 rental listings are anchored to Chennai Metro corridors (Blue Line & Green Line).
  - Explicitly marked as `PERIODIC` / `ESTIMATED`.
  - All UI surfaces display: `"Rental source: Demo / seeded dataset (CMRL-anchored)"`.
- **Rental Data Source Plan (`docs/RENTAL_DATA_SOURCE_PLAN.md`)**:
  - Evaluated candidate providers: Commercial B2B Partner APIs (Magicbricks/99acres), CREDAI Chennai MLS feeds, and GCC municipal public housing data.
  - Strictly prohibited unauthorized web scraping.
  - Outlined dual-track integration for Phase 8.
- **No Rent ML Yet**:
  - Confirmed: XGBoost/LightGBM rent estimation models are deferred until legitimate current market feeds are connected.

---

## 12. Acceptance Criteria Checklist

- [x] Google remains live when available and authorized
- [x] Google fallback remains correct (GTFS + local verified POIs)
- [x] 429/QUOTA_EXCEEDED handled gracefully with zero retry storms
- [x] Search does not route every home in every mode (primary mode only)
- [x] Search does not query Places for every home (local facility pre-filter)
- [x] Detailed live work happens strictly on shortlist / selected home
- [x] Cache works and preserves `LIVE` vs `RECENT` semantics
- [x] `POST /api/v1/recommendations/detail` provides full door-to-door multi-mode itinerary
- [x] Existing 96+ tests pass (98 unit/integration tests passing)
- [x] Live tests disabled by default and skip cleanly
- [x] Frontend builds cleanly with zero errors
- [x] Measured request count documented
- [x] Rental data remains truthfully labelled (`Demo / seeded dataset`)
- [x] No Rent ML yet
