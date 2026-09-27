# RIVO — PHASE 7.1 SAFETY FIX REPORT
## Separation of Live-Test Safety Switch from Application Live API Access
**Team CLAIRES | ST1010 | PS-11-S3 | Chennai Pilot**  
**Date**: September 27, 2026  
**Status**: VERIFIED & COMPLETE  

---

## 1. Executive Summary & Core Principle

In Phase 7, the safety switch `RIVO_LIVE_API_TESTS=false` was introduced to prevent accidental Google Cloud quota consumption during development and testing. However, placing that check directly inside the application provider methods (`GoogleRouteProvider._call_api`, `GooglePlacesProvider._call_api`) coupled the live-test harness safety switch with the production application request path.

Phase 7.1 successfully decoupled these controls:
- **`RIVO_LIVE_API_TESTS`** governs **ONLY** the test and diagnostic layer (`tests/live/*`, `scripts/verify_live_google.py`, `scripts/live_smoke_test.py`). Default remains `false` to protect the project's quota during automated test runs.
- **Normal Application Access** depends strictly on credentials (`GOOGLE_ROUTES_API_KEY`, `GOOGLE_PLACES_API_KEY`) and runtime circuit health (`QuotaCircuitBreaker`).
- **Confirmation**: **"Normal application Google access is independent of the live-test safety switch."**

---

## 2. Decoupled Architecture

```
                  GOOGLE API KEYS
          (GOOGLE_ROUTES_API_KEY / PLACES)
                        │
                        ▼
            Normal RIVO Application Path
           (Search, Itinerary, Detail Mode)
                        │
                  Circuit Breaker
                 (Open / Closed)
                        │
                        ▼
                Google API Request
                        │
                 Fallback Chain
             (GTFS / Local Seed Data)


              LIVE TEST HARNESS & SCRIPTS
              (tests/live/*, verify scripts)
                        │
                        ▼
               RIVO_LIVE_API_TESTS
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
     false                            true
(SKIP with 0 calls)           (Permit execution)
```

---

## 3. Files Modified

| File | Change Details |
|---|---|
| [`backend/app/services/providers/route_google.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/providers/route_google.py) | Removed `RIVO_LIVE_API_TESTS` blocking from `_call_api` and `compute_route_matrix`. Normal provider execution is governed solely by `self.is_available()` (key presence + circuit health). |
| [`backend/app/services/providers/places_google.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/providers/places_google.py) | Removed `RIVO_LIVE_API_TESTS` blocking from `nearby_facilities` / `_call_api`. |
| [`backend/app/core/circuit_breaker.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/core/circuit_breaker.py) | Decoupled `get_routes_status()` and `get_places_status()` from `RIVO_LIVE_API_TESTS`. Returns `AVAILABLE` when keys are configured and circuits are not tripped. |
| [`backend/app/core/request_tracker.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/core/request_tracker.py) | Added `reset_current_tracker()` to isolate per-session budget tracking cleanly. |
| [`backend/tests/conftest.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/tests/conftest.py) | Added `autouse=True` fixture `reset_circuit_and_tracker` to prevent singleton state leakage across test boundaries. |
| [`backend/tests/unit/test_phase7_quota_optimization.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/tests/unit/test_phase7_quota_optimization.py) | Updated safety guard test to prove `_call_api` executes independently of `RIVO_LIVE_API_TESTS`. |
| [`backend/tests/unit/test_phase7_1_safety_separation.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/tests/unit/test_phase7_1_safety_separation.py) | New dedicated regression suite proving the three required Phase 7.1 properties. |

---

## 4. Tests Added & Regression Verification

### New Tests in `test_phase7_1_safety_separation.py`
1. `test_application_routes_provider_independent_of_live_test_switch`:
   Proves `GoogleRouteProvider._call_api` proceeds to make external calls when `RIVO_LIVE_API_TESTS=False`.
2. `test_application_places_provider_independent_of_live_test_switch`:
   Proves `GooglePlacesProvider.nearby_facilities` executes normally when `RIVO_LIVE_API_TESTS=False`.
3. `test_live_test_harness_gated_when_switch_is_false`:
   Proves that when `RIVO_LIVE_API_TESTS=False`, `ROUTES_CONFIGURED` and `PLACES_CONFIGURED` evaluate to `False`, skipping all tests under `tests/live/` with **0 live network calls**.
4. `test_live_test_harness_permitted_when_switch_is_true_mocked`:
   Proves that when `RIVO_LIVE_API_TESTS=True`, the live test gate allows requests (verified with mock transport, consuming **zero external quota**).
5. `test_circuit_breaker_status_independent_of_live_test_switch`:
   Proves status endpoints report `AVAILABLE` when keys are configured, regardless of `RIVO_LIVE_API_TESTS`.

---

## 5. Verification Results

- **Unit & Integration Suite**:
  ```bash
  pytest tests/unit tests/integration
  # 103 passed in 6.00s (0 live Google API calls made)
  ```
- **Live Tests**:
  ```bash
  pytest tests/live
  # 8 skipped in 0.95s (0 live Google API calls made)
  ```
- **Frontend Build**:
  ```bash
  npm run build
  # Built in 626ms with 0 errors
  ```
- **No Additional Quota Consumed**: All testing and verification performed via deterministic mocks and offline GTFS/local seed data.

---

## 6. Confirmation Statement

> **"Normal application Google access is independent of the live-test safety switch."**
