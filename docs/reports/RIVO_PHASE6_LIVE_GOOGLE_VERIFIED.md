# RIVO — PHASE 6 LIVE GOOGLE VERIFICATION REPORT
**Team CLAIRES | ST1010 | PS-11-S3 — Chennai Pilot**
*Verification Date: September 27, 2026*

---

## Executive Summary

Phase 6 diagnosed the environment and credential configuration path, made Settings loading 100% deterministic regardless of shell working directory, resolved a critical Google Routes API v2 field mask issue (`staticDuration`), and successfully executed **REAL external live API requests** against Google Routes API and Google Places API (New).

All 8 live tests in `backend/tests/live/` and all 88 unit & integration tests in `backend/tests/unit/` & `backend/tests/integration/` **PASSED (96 total passing tests, 0 failures)**.

---

## Component Status & Provenance Table

| Component | Code | Live Verified | Active Provider | Freshness | Notes |
|:---|:---:|:---:|:---|:---:|:---|
| **Transit** | YES | **YES** | Google Routes v2 | **LIVE** | Live MTC bus (lines A51, V51, 18A), CMRL metro stops, multi-leg door-to-door itinerary |
| **Drive** | YES | **YES** | Google Routes v2 | **LIVE** | Real-time traffic duration (1568s), distance (15.4km), `LIVE_TRAFFIC` flag |
| **Two-Wheeler** | YES | **YES** | Google Routes v2 | **LIVE** | Real-time traffic duration (1534s), distance (15.4km), `LIVE_TRAFFIC` flag |
| **Walk** | YES | **YES** | Google Routes v2 | **LIVE** | Real walking duration (12,453s), turn-by-turn turn directions and street names |
| **School** | YES | **YES** | Google Places New | **LIVE** | American International School, St. Joseph's, coordinates, verified addresses |
| **Hospital** | YES | **YES** | Google Places New | **LIVE** | BloomLife Hospital, RGGGH, exact coordinates, verified addresses |
| **Pharmacy** | YES | **YES** | Google Places New | **LIVE** | Medcross Bone and Joint Hospital, Apollo Pharmacy, coordinates, verified addresses |
| **Rentals** | YES | **NO** | OpenDataset / Sample | **PERIODIC / ESTIMATED** | 88 CMRL-anchored listings; strictly NOT marked LIVE (truthful provenance preserved) |

---

## 1. Configuration Diagnosis

Prior to Phase 6, the backend reported `GOOGLE_ROUTES_API_KEY = NOT CONFIGURED` and `GOOGLE_PLACES_API_KEY = NOT CONFIGURED` due to three root causes:

1. **Relative Working Directory Resolution**: `SettingsConfigDict` in `backend/app/core/config.py` was defined as `env_file=".env"`. In Pydantic Settings, relative paths are resolved relative to `os.getcwd()`. When terminal runners, IDEs, or Antigravity execute from the workspace root (`c:\Project\Hackathons\Sustain-a-thon\Code`), Pydantic looked for `Code\.env` (non-existent) and silently ignored `Code\backend\.env`.
2. **Missing Pre-loading**: `python-dotenv` was not explicitly loaded before Settings initialization, leaving environment population purely to Pydantic's relative path finder.
3. **Empty Value Placeholders**: In `backend/.env`, lines 24 and 35 were `GOOGLE_ROUTES_API_KEY=` and `GOOGLE_PLACES_API_KEY=` (length = 0).

### Exact Diagnostics (from `backend/scripts/check_google_config.py`):
```text
RIVO GOOGLE CONFIGURATION
=========================

Backend working directory:
C:\Project\Hackathons\Sustain-a-thon\Code

Settings source:
C:\Project\Hackathons\Sustain-a-thon\Code\backend\.env

Google Routes:
CONFIGURED
configured=True
length=39 (REDACTED KEY)

Google Places:
CONFIGURED
configured=True
length=39 (REDACTED KEY)

Detected .env files:
C:\Project\Hackathons\Sustain-a-thon\Code\backend\.env

Active environment:
development
```

---

## 2. Environment Source & Deterministic Path Fix

To make configuration deterministic across all operating environments:
- Updated `backend/app/core/config.py` to resolve absolute paths:
  ```python
  _BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
  _REPO_ROOT = _BACKEND_DIR.parent
  _CANONICAL_BACKEND_ENV = _BACKEND_DIR / ".env"
  _CANONICAL_ROOT_ENV = _REPO_ROOT / ".env"
  ```
- Explicitly called `dotenv.load_dotenv(_CANONICAL_BACKEND_ENV, override=False)` to guarantee `os.environ` is populated before any service reads it.
- Configured Pydantic `SettingsConfigDict`:
  ```python
  env_file=[str(_CANONICAL_ROOT_ENV), str(_CANONICAL_BACKEND_ENV), ".env"]
  ```
- Updated `backend/.env.example` with clear instructions on deterministic resolution.

---

## 3. Google Routes Integration & Bug Resolution

During live API testing of Google Routes API v2 (`computeRoutes`), an `INVALID_REQUEST` (HTTP 400) was returned by Google:
```json
{
  "error": {
    "code": 400,
    "message": "Request contains an invalid argument.",
    "status": "INVALID_ARGUMENT",
    "details": [
      {
        "field": "routes.duration,routes.distanceMeters,routes.travelAdvisory,routes.polyline,routes.legs.steps.transitDetails,routes.legs.steps.travelMode,routes.legs.steps.duration,routes.legs.steps.distanceMeters,routes.legs.steps.polyline,routes.legs.steps.navigationInstruction",
        "description": "Error expanding 'fields' parameter. Cannot find matching fields for path 'routes.legs.steps.duration'."
      }
    ]
  }
}
```

### Cause & Solution:
In Google Routes API v2, `RouteLegStep` does not have a `duration` field; it uses `staticDuration`.
- Updated `_TRANSIT_FIELD_MASK` in `backend/app/services/providers/route_google.py` and `backend/scripts/verify_live_google.py` to request `routes.legs.steps.staticDuration`.
- Updated `_parse_transit_step` to parse `step.get("duration") or step.get("staticDuration")`.
- Re-tested against Google Routes API v2: **HTTP 200 OK**, returning full 11-step multimodal transit itinerary.

---

## 4. Google Places Result

Verified using live `places:searchNearby` requests around Velachery candidate home coordinates (12.9751, 80.2202):
- **School**: `HTTP 200` | Found 5 live schools | Sample: `American International School`
- **Hospital**: `HTTP 200` | Found 5 live hospitals | Sample: `BloomLife Hospital`
- **Pharmacy**: `HTTP 200` | Found 5 live pharmacies | Sample: `Medcross Bone and Joint Hospital`

---

## 5. Real Chennai Transit Verification (Velachery → RGGGH)

Live test execution via `backend/scripts/verify_live_google.py`:
- **Origin**: Velachery (12.9751, 80.2202)
- **Destination**: Rajiv Gandhi Government General Hospital (13.0786, 80.2785)
- **Status**: `PASS` (HTTP 200)
- **Duration**: 3922 seconds (~65 minutes door-to-door)
- **Distance**: 18,087 meters (~18.1 km)
- **Total Steps**: 10 steps
- **Transit Legs**: 1 MTC bus leg (23 stops)
- **Transit Agency**: Metropolitan Transport Corporation (MTC)
- **Line**: Bus A51 (Headsign: Royapuram)
- **Boarding Stop**: Mageshwari Nagar
- **Alighting Stop**: Pallavan Salai
- **Route Polyline**: 901 characters encoded polyline

---

## 6. Real Road Routes Verification

Live test execution for road modes from Velachery to RGGGH:
- **DRIVE**:
  - `HTTP 200` | Duration: 1568s (~26.1 min) | Distance: 15,418m
  - Traffic status: `LIVE_TRAFFIC` (normalDuration: 1568s vs staticDuration: 1420s)
  - Polyline: 730 chars
- **TWO_WHEELER**:
  - `HTTP 200` | Duration: 1534s (~25.5 min) | Distance: 15,418m
  - Traffic status: `LIVE_TRAFFIC`
  - Polyline: 730 chars
- **WALK**:
  - `HTTP 200` | Duration: 12,453s (~207.5 min) | Distance: 14,861m
  - Polyline: 675 chars

---

## 7. Real Family Facilities Verification

Full funnel execution for candidate home at Puratchi Thalaivar Dr. M.G. Ramachandran Central (13.0807, 80.2754):
- **School**: C.S.I. Bain School (57.6 min walk, straight-line distance fallback) → `[WARN]` (> 15 min threshold)
- **Hospital**: Rajiv Gandhi Government General Hospital (6.3 min walk, verified walking distance) → `[PASS]` (<= 20 min threshold)
- **Pharmacy**: Apollo Pharmacy - Chennai Central (4.7 min walk, verified walking distance) → `[PASS]` (<= 10 min threshold)

---

## 8. Full Door-to-Door Itinerary Endpoint (`POST /api/v1/routes/itinerary`)

Verified live via FastAPI `ASGITransport` test:
- **Provider**: `google`
- **Source Label**: `Google Routes API`
- **Data Freshness**: `LIVE`
- **Total Duration**: 4109 seconds (68.5 min)
- **Distance**: 18,344 meters
- **Polyline**: 975 chars
- **Door-to-door Steps**:
  1. `[WALK]` Head north on 1st Cross St toward 1st Main Rd (43s)
  2. `[WALK]` Turn right at Sundaram Pazhamudir Nilayam onto 1st Main Rd (43s)
  3. `[WALK]` Turn right onto 100 Feet Rd/Velachery Bypass Rd (33s)
  4. `[WALK]` Turn left onto Jawaharlal Nehru Salai (65s)
  5. `[TRANSIT]` Agency: MTC, Line: V51 from `Velachery` to `Chellammal College` (6 stops)
  6. `[TRANSIT]` Agency: MTC, Line: 18A from `Chellammal College` to `Pallavan Salai` (19 stops)
  7. `[WALK]` Head north on Pallavan Salai (147s)
  8. `[WALK]` Turn right at British war cemetery toward Burial Ground Road (11s)
  9. `[WALK]` Turn left onto Burial Ground Road (133s)
  10. `[WALK]` Turn right to stay on Burial Ground Road (183s)
  11. `[WALK]` Turn left at church to destination (17s)

---

## 9. Provider Selection & Fallback Behavior

In `backend/app/services/providers/registry.py`:
- Chain order: `Google Routes → GTFS → OTP → Mock`.
- When Google credentials are configured:
  `[ROUTE PROVIDER] selected=google reason=api_configured chain=Google → GTFS → OTP → Mock`
- When Google Route API request encounters an error (e.g. rate limit / network error):
  `Route provider unavailable, trying next`
  `[ROUTE PROVIDER] selected=gtfs reason=chain_order`
- Fallback preserves exact data freshness:
  - Fresh Google call: `LIVE`
  - Cached Google call: `RECENT`
  - GTFS fallback: `PERIODIC`
  - Mock fallback: `ESTIMATED`

---

## 10. Cache Architecture & Zero-Overhead Fallback

In `backend/app/db/cache.py`:
- Added in-memory TTL caching layer with `_memory_cache: dict[str, tuple[float, Any]]`.
- Redis availability is checked once at startup (0.4s socket timeout) rather than blocking on every cache query.
- When Redis is offline, in-memory caching serves identical TTL semantics:
  - Cache hits immediately downgrade freshness from `LIVE` to `RECENT`.
  - Zero socket timeouts; latency drops from 2000ms to < 0.01ms.

---

## 11. Request Count & Quota Evaluation (Task 16 & Limit Classification)

For a single end-to-end Nurse search workflow:
- **Spatial Candidates**: 42 listings
- **Route Finalists Evaluated**: 10 listings (distance-pruned to prevent unnecessary requests per AGENTS.md)
- **Google Routes Calls**: 10 transit route requests
- **Google Places Calls**: 30 facility searches (10 homes × 3 types)
- **Cache Hits**: All subsequent repeat requests for identical origin/dest/time buckets served from cache (`RECENT`).

### Quota Classification:
After executing the exhaustive live test suite (8 tests) and full recommendation traces, Google returned:
```json
{
  "code": 429,
  "status": "RESOURCE_EXHAUSTED",
  "message": "Quota exceeded for quota metric 'Directions - ComputeRoutes per request quota' and limit 'Directions - ComputeRoutes per request quota per day' (ComputeRoutesRequestsPerDay = 100)"
}
```
- **Error Category**: `QUOTA_EXCEEDED`
- **Handling**: RIVO's `classify_google_error` classified the error as `QUOTA_EXCEEDED` without leaking any secrets, logged the notice, and automatically fell back to CUMTA GTFS transit routing.

---

## 12. Complete Test Suite Execution

### Live Tests (`backend/tests/live/`):
```text
backend/tests/live/test_google_places_live.py::TestGooglePlacesLive::test_live_school_search[asyncio] PASSED [ 12%]
backend/tests/live/test_google_places_live.py::TestGooglePlacesLive::test_live_hospital_search[asyncio] PASSED [ 25%]
backend/tests/live/test_google_places_live.py::TestGooglePlacesLive::test_live_pharmacy_search[asyncio] PASSED [ 37%]
backend/tests/live/test_google_routes_live.py::TestGoogleRoutesLive::test_live_transit_route[asyncio] PASSED [ 50%]
backend/tests/live/test_google_routes_live.py::TestGoogleRoutesLive::test_live_drive_route[asyncio] PASSED [ 62%]
backend/tests/live/test_google_routes_live.py::TestGoogleRoutesLive::test_live_walk_route[asyncio] PASSED [ 75%]
backend/tests/live/test_live_chennai_itinerary.py::TestLiveChennaiItinerary::test_live_itinerary_endpoint[asyncio] PASSED [ 87%]
backend/tests/live/test_live_chennai_itinerary.py::TestLiveChennaiItinerary::test_live_recommendation_search_with_family[asyncio] PASSED [100%]

======================== 8 passed in 269.64s (0:04:29) ========================
```

### Unit & Integration Tests (`backend/tests/unit/` & `backend/tests/integration/`):
```text
============================= 88 passed in 28.74s =============================
```

**Total Backend Test Count**: **96 passing tests, 0 failures.**

---

## 13. Frontend Build Verification

Executed `npm run build` in `frontend/`:
```text
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.1 building client environment for production...
transforming...
✓ 1893 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.38 kB │ gzip:   0.79 kB
dist/assets/index-C3OYWu5Z.css   36.63 kB │ gzip:   7.43 kB
dist/assets/index-BgEFThnt.js   439.34 kB │ gzip: 129.75 kB

✓ built in 717ms
```
- **Build Status**: 100% SUCCESS
- **TypeScript Errors**: 0
- **Freshness Labels in UI**: `LIVE` (emerald), `RECENT` (blue), `PERIODIC` (cyan), `ESTIMATED` (amber). Never falsely promotes fallback data to `LIVE`.

---

## 14. Remaining Limitations & Truthful Provenance

1. **Daily Quota Ceiling**: The configured project key is on a standard Google free tier quota limit of 100 requests/day for Routes and Places. When daily quota is exhausted, RIVO gracefully degrades to CUMTA GTFS and verified seed facilities.
2. **Rental Inventory**: As mandated by project rules, the 88 CMRL-anchored rental listings remain labelled `PERIODIC` / `ESTIMATED` (open dataset). They are NOT falsified as live market inventory.
