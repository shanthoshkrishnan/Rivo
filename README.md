# RIVO
### Worker Housing & Mobility Intelligence

> **“RIVO finds homes that fit your income, family and commute — and shows cities where better housing and transport should go.”**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI 0.111+](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB.svg)](https://react.dev/)
[![Vite 8](https://img.shields.io/badge/Vite-8.3-646CFF.svg)](https://vitejs.dev/)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind-v4.3-38B2AC.svg)](https://tailwindcss.com/)
[![Leaflet 1.9](https://img.shields.io/badge/Leaflet-1.9-199900.svg)](https://leafletjs.com/)
[![Tests Passing](https://img.shields.io/badge/tests-246%20passed%2C%208%20skipped-brightgreen.svg)]()
[![Google Quota Safe](https://img.shields.io/badge/Google%20Quota-0%20test%20calls%20(Protected)-success.svg)]()
[![Model Status](https://img.shields.io/badge/Rent%20ML-Gated%20(Insufficient%20Data)-orange.svg)]()

---

**Team:** CLAIRES  
**Team ID:** ST1010  
**Problem Statement:** PS-11-S3 — *Can the People Who Run the City Afford to Live In It?*  
**Pilot Geography:** Chennai Metropolitan Area (CMA), Tamil Nadu, India  

> 🚀 **Quick Start:** For step-by-step installation in under 3 minutes, see the [Quick Setup Guide (SETUP.md)](SETUP.md).

---

## Table of Contents

- [Quick Setup Guide (SETUP.md)](SETUP.md)
- [1. Problem](#1-problem)
- [2. RIVO Solution](#2-rivo-solution)
- [3. PS-11-S3 Requirement Coverage](#3-ps-11-s3-requirement-coverage)
- [4. Key Features](#4-key-features)
- [5. Architecture](#5-architecture)
- [6. Technology Stack](#6-technology-stack)
- [7. Core Recommendation Pipeline](#7-core-recommendation-pipeline)
- [8. Affordability Model](#8-affordability-model)
- [9. Routing Architecture](#9-routing-architecture)
- [10. Rental Data Architecture](#10-rental-data-architecture)
- [11. Rent Intelligence & ML](#11-rent-intelligence--ml)
- [12. Data Quality & Trust](#12-data-quality--trust)
- [13. Current Data Status](#13-current-data-status)
- [14. Where the Project Stands Today](#14-where-the-project-stands-today)
- [15. Development Phases](#15-development-phases)
- [16. API Endpoints](#16-api-endpoints)
- [17. Important Scripts](#17-important-scripts)
- [18. Setup](#18-setup)
- [19. Environment Variables](#19-environment-variables)
- [20. Testing](#20-testing)
- [21. Google API & Quota Safety](#21-google-api--quota-safety)
- [22. Data Collection Workflow](#22-data-collection-workflow)
- [23. Project Roadmap](#23-project-roadmap)
- [24. Limitations & Honest Status](#24-limitations--honest-status)
- [25. Demo Flow](#25-demo-flow)
- [26. Repository Structure](#26-repository-structure)
- [27. Data Licenses & Attribution](#27-data-licenses--attribution)
- [28. Final Evaluator Summary: Why RIVO](#28-final-evaluator-summary-why-rivo)

---

## 1. Problem

Modern cities rely on essential frontline workers — government nurses, school teachers, metropolitan bus drivers, sanitation workers, and delivery riders. Yet in rapidly expanding metropolises like Chennai:

1. **Nominal rent ≠ True household affordability:** A ₹10,000 apartment that requires a ₹4,000 monthly round-trip commute and 90 minutes of daily travel is often less affordable than an ₹11,500 apartment 15 minutes away by bus.
2. **The "Time Tax" penalizes frontline workers:** Long transit commutes exhaust workers before their shifts begin and extract hundreds of unpaid hours per year.
3. **Family infrastructure is omitted from housing tools:** Frontline workers are not isolated individuals; they have children needing neighborhood schools and elder relatives needing nearby clinics or pharmacies.
4. **Urban planners lack spatial evidence:** Municipal transit agencies (e.g., CUMTA, CMRL, MTC) and housing authorities (TNPCB, CMDA) plan infrastructure in silos, lacking unified spatial intelligence showing how transit extensions or affordable housing quotas change real worker access.

---

## 2. RIVO Solution

RIVO operates across two complementary modes that address both individual workers and systemic urban planning:

### RIVO Home (Worker & Household Discovery)
```text
Worker / Household
    ↓
Income + Housing + Workplace + Family Requirements
    ↓
Candidate Rental Properties
    ↓
Spatial Hard Filtering (search radius, BHK, hard budget)
    ↓
Transit / Road Accessibility (multimodal travel time & fare)
    ↓
Rent + Transport + Time Burden Calculation
    ↓
Family Facility Proximity Fit (Schools, Hospitals, Pharmacies)
    ↓
Explainable Recommendation Card (Data-driven reasons, no black box)
```

### RIVO City (Planner Scenario Intelligence)
```text
Authoritative Spatial Data (GCC GIS + CUMTA GTFS + PLFS 2025)
    ↓
RIVO City Scenario Engine
    ↓
Spatial Accessibility & Demographic Catchment (800m station buffers)
    ↓
Before-and-After Scenario Evaluation (Baseline vs Proposed Transit / Housing)
    ↓
Intervention Impact Report (WorkerReach, Affordability Shifts, Bounds)
```

### What Sets RIVO Apart
- **Multi-Dimensional Affordability:** Rent, transit fares, vehicle fuel costs, and maintenance are synthesized into explicit percentage burdens (`housing_burden`, `transport_burden`, `cash_burden`).
- **Commute as an Economic Time Tax:** Travel hours are tracked explicitly as monthly commute hours rather than hidden.
- **Family Context Layer:** Integrated thresholds for schools (UDISE+), government/private hospitals, and pharmacies.
- **Hard Constraints vs. Soft Scoring:** Hard criteria (budget ceiling, BHK, tenant restrictions) strictly filter candidates before weighted scoring begins.
- **Data Provenance & Anti-Fabrication:** Every number carries source, retrieval timestamp, confidence level (`HIGH`, `MEDIUM`, `LOW`), and freshness label (`LIVE`, `RECENT`, `PERIODIC`, `ESTIMATED`, `HISTORICAL`).
- **Explainable Decisions (No LLM black-box):** Recommendation rankings provide deterministic, mathematical justifications without stochastic hallucinations.

---

## 3. PS-11-S3 Requirement Coverage

| PS-11-S3 Requirement | RIVO Implementation | Current Status | Notes |
|---|---|---|---|
| **1. Spatial Rent Surface** | H3 hexagon resolution 8/9 aggregation with empirical and quantile fallbacks in `backend/app/services/ml/rent_surface.py` | **Implemented; Data-Dependent** | Surface algorithms and data structures exist; actively suppresses synthetic extrapolations until genuine observation thresholds are met. |
| **2. Realistic Door-to-Door Travel Time** | Multimodal router combining Google Routes API v2, local CUMTA/MTC GTFS timetable graph, and OpenTripPlanner fallback | **Fully Implemented & Verified** | Live Google comparison works when API key is provided; local GTFS timetable routing functions offline; mock router provides deterministic test fallback. |
| **3. Occupation-Specific Affordability** | 5 core Chennai occupations calibrated against PLFS 2025 Tamil Nadu Urban microdata (`nurse`, `teacher`, `bus_driver`, `delivery_rider`, `construction_worker`) | **Fully Implemented & Verified** | Endpoints return p25, median, and p75 income profiles, sample sizes, and max 30% rent budgets. |
| **4. Historical Affordability / Rent Change** | `RentalObservation` time-series table tracking price changes, availability shifts, and observation timestamps per listing | **Implemented; Pending Longitudinal Real Data** | Schema, migration, and history endpoints exist (`GET /rentals/{id}/history`); current repository has 0 multi-month genuine observation intervals. |
| **5. Transit / Housing Intervention Testing** | RIVO City Scenario Engine with 800m transit catchments, demographic density buffers, and speed-differential accessibility shifts | **Fully Implemented & Verified** | Planners can evaluate CMRL Phase II extensions, bus feeder corridors, and rental subsidy scenarios with confidence bounds. |

---

## 4. Key Features

### RIVO Home
- **3-Step Search Workflow:** Workplace & Commute, Worker & Household Budget, Family Amenities.
- **Occupation Presets:** Auto-prefills median salary and 30% rent ceiling from PLFS 2025.
- **Hard Constraint Gating:** Enforces hard caps on rent, minimum BHK, and spatial radius before ranking.
- **Door-to-Door Multimodal Routing:** Compares Transit (Metro + Bus), Two-Wheeler, and Walking routes with travel durations and monthly ticket/fuel costs.
- **Economic Burden Metrics:** Calculates exact `housing_burden`, `transport_burden`, `cash_burden`, and `monthly_commute_hours`.
- **Family Infrastructure Matching:** Evaluates proximity to primary/secondary schools, general hospitals, and pharmacies within walking thresholds.
- **Deterministic Explainability:** Provides structured pros and cons (`"Commute is 22 min within your 45 min ceiling"`, `"Rent is 28% of household income"`).
- **Interactive Leaflet Map:** Displays workplace marker, search buffer radius, candidate listings, transit stations, and walking routes.

### RIVO City (Planning Mode)
- **Station Catchment Analysis:** 800m pedestrian walking buffers around transit nodes.
- **Demographic Grounding:** Uses Greater Chennai Corporation (GCC) ward density averages (16,500 people/km²) and PLFS labor shares.
- **Scenario Simulation:** Evaluates proposed transit lines (e.g., CMRL Phase II Madhavaram–SIPCOT corridor) and housing subsidies.
- **WorkerReach Metrics:** Compares 30-min, 45-min, and 60-min reachable worker populations before and after interventions.
- **Confidence Bounds:** Generates lower bound, expected estimate, and upper bound ranges.

### Rental Data Architecture & Integrity
- **First-Party RIVO Direct:** Verified listing intake for Chennai landlords with property-owner consent.
- **Multi-Provider Registry:** Ingests from direct listings, licensed providers, open datasets, and seed data.
- **Observation Time-Series:** Tracks repeated visits/checks per property without overwriting historical rents.
- **Spatial Deduplication:** Merges records matching identical coordinates within 50m and similar rent/BHK profiles.
- **Data Quality Dashboard:** Admin endpoint tracking data provenance, geocode confidence, and gate progress.
- **Strict ML Eligibility Gate:** Blocks ML rent training until 50+ real, non-synthetic observations across 5+ localities are recorded.

---

## 5. Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (SPA)                                  │
│   React 19 + TypeScript + Vite 8.3 + Tailwind CSS v4 + Leaflet 1.9    │
│   • RIVO Home Search      • RIVO City Planner      • Sources Registry │
│   • Leaflet Chennai Map   • Detail Route Modal     • Burden Cards     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API (FastAPI)                           │
│   FastAPI 0.111+ • Pydantic v2 • AsyncSession • Request Budget Tracker │
│   • /api/v1/recommendations  • /api/v1/rentals    • /api/v1/routes     │
│   • /api/v1/scenarios        • /api/v1/workers    • /api/v1/facilities │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│           DOMAIN SERVICES            │  │     ROUTING & PLACES CHAIN   │
│  • RecommendationService (Funnel)    │  │  • Google Routes API v2      │
│  • ObservationService (Quality/Gate) │  │  • Google Places API (New)   │
│  • ScenarioEngine (Demographics)     │  │  • CUMTA/MTC GTFS Timetable  │
│  • Affordability & Scoring Math      │  │  • OpenTripPlanner Client    │
│  • CircuitBreaker (External Quota)   │  │  • Mock Offline Router       │
└───────────────────┬──────────────────┘  └──────────────┬───────────────┘
                    │                                    │
                    ▼                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          DATA / STORAGE LAYER                          │
│  • PostgreSQL + PostGIS (Production) / SQLite + aiosqlite (Dev Local) │
│  • Redis 5.0+ (Transient Route & Listing Cache)                        │
│  • Uber H3 Grid (Spatial Indexing Resolution 8/9)                      │
│  • CUMTA/MTC GTFS Feeds (Stops, Trips, Fares)                          │
│  • GCC GIS 2025 Wards & Chennai Health OGD Data                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Frontend Framework** | React | `19.2.8` | Component-based reactive user interface |
| **Frontend Build Tool** | Vite | `8.3.0` | Ultra-fast HMR and production asset bundling |
| **Language (Frontend)** | TypeScript | `~6.0.2` | Type-safe frontend client implementation |
| **Styling** | Tailwind CSS | `^4.3.3` | Modern utility-first responsive styling system |
| **Mapping** | Leaflet / React-Leaflet | `^1.9.4` | Interactive Chennai spatial mapping and route rendering |
| **Icons** | Lucide React | `^1.48.0` | Lightweight modern UI iconography |
| **Backend Framework** | FastAPI | `>=0.111.1` | High-performance asynchronous REST API |
| **Server** | Uvicorn (standard) | `>=0.30.1` | ASGI server runtime |
| **Data Validation** | Pydantic / Pydantic-Settings | `>=2.10.0` / `>=2.5.0` | Strict schema validation and typed settings |
| **Database ORM** | SQLAlchemy | `>=2.0.31` | Asynchronous ORM and relational models |
| **Database Drivers** | asyncpg / aiosqlite | `>=0.29.0` / `>=0.20.0` | Async PostgreSQL (prod) and SQLite (dev fallback) |
| **Database Migrations** | Alembic | `>=1.13.2` | Schema migrations tracking PostGIS/SQLite schemas |
| **Spatial Indexing** | Uber H3 (Python) | `>=4.0.0` | Discrete hexagonal spatial grid at resolutions 8 and 9 |
| **Geometry** | Shapely / GeoAlchemy2 | `>=2.0.0` / `>=0.15.2` | Geometric predicates, point-in-polygon, PostGIS types |
| **Caching** | Redis / aiohttp / httpx | `>=5.0.7` / `>=0.27.0` | In-memory route/places caching with strict TTLs |
| **ML Libraries** | LightGBM / Scikit-Learn | `>=4.3.0` / `>=1.5.0` | Quantile regression and baseline statistical models |
| **Testing** | Pytest / Pytest-Asyncio | `9.1.1` / `1.4.0` | Automated unit, integration, and live test harness |

---

## 7. Core Recommendation Pipeline

RIVO does **not** make expensive external route calls for every listing in the database. Instead, it processes requests through a deterministic, phased pipeline:

```text
Database / Registry Listings (88+ properties)
    │
    ▼ [Phase 1: Availability Filter]
Drop unavailable, rented-out, or pending-confirmation listings
    │
    ▼ [Phase 2: Property Type & BHK Filter]
Keep only requested BHK configurations (e.g., 2 BHK) and property types
    │
    ▼ [Phase 3: Hard Rent Ceiling Filter]
Strict filter: rent_monthly <= user_max_rent_monthly (no exceptions)
    │
    ▼ [Phase 4: Household & Tenant Filter]
Filter vegetarian/family restrictions where specified
    │
    ▼ [Phase 5: Location Validity Filter]
Drop records without valid coordinates within Chennai CMA bounding box
    │
    ▼ [Phase 6: Spatial Deduplication]
Merge duplicate listings across providers within 50m radius
    │
    ▼ [Phase 7: Spatial Radial Filter]
Drop properties exceeding search_radius_km (Haversine distance from workplace)
    │
    ▼ [Phase 8: Facility Access Pre-Score]
Compute walking proximity to nearest schools, hospitals, and pharmacies
    │
    ▼ [Phase 9: Route Candidate Pruning]
Prune candidate pool to top spatial finalists (≤ 15 properties)
    │
    ▼ [Phase 10: Multimodal Route Evaluation]
Evaluate travel time, transfers, walking legs, and fares (Google Routes / GTFS)
    │
    ▼ [Phase 11: Commute Threshold Filter]
Drop properties where commute duration exceeds max_commute_minutes
    │
    ▼ [Phase 12: Affordability Burden Calculation]
Calculate housing_burden, transport_burden, cash_burden, and monthly commute hours
    │
    ▼ [Phase 13: Multi-Component Weighted Ranking]
Combine Housing (30%), Commute (25%), Transport (15%), Family (15%), Work (10%), Confidence (5%)
    │
    ▼ [Phase 14: Explainability Generation]
Generate deterministic positive and negative reasons
    │
    ▼ [Phase 15: Pagination & Response Assembly]
Return ranked list with route timelines, maps, and metadata
```

---

## 8. Affordability Model

RIVO evaluates household economics using grounded formulas rather than a single opaque score.

### Mathematical Formulations

$$\text{Housing Burden} = \frac{\text{Monthly Rent}}{\text{Monthly Household Income}}$$

$$\text{Transport Burden} = \frac{\text{Monthly Transport Cost}}{\text{Monthly Household Income}}$$

$$\text{Cash Burden} = \frac{\text{Monthly Rent} + \text{Maintenance} + \text{Monthly Transport Cost}}{\text{Monthly Household Income}}$$

$$\text{Monthly Commute Hours (Time Tax)} = \frac{\text{One-Way Travel Minutes} \times 2 \times \text{Work Days per Month}}{60}$$

$$\text{Monthly Transit Cost} = (\text{Outbound Transit Fare} + \text{Return Transit Fare}) \times \text{Work Days}$$

$$\text{Monthly Two-Wheeler Cost} = \left(\frac{2 \times \text{Commute Distance (km)} \times \text{Work Days}}{\text{Efficiency (45 km/L)}}\right) \times \text{Fuel Price (₹105/L)}$$

### Recommendation Component Weights

The composite match score ($\text{Score} \in [0.0, 1.0]$) is computed using the canonical weights configured in `backend/app/services/algorithms/affordability.py`:

| Component | Weight | Criteria |
|---|---|---|
| **Housing Score** | `0.30` | Rent savings relative to maximum budget ceiling minus high cash-burden penalty |
| **Commute Score** | `0.25` | Commute time relative to maximum acceptable commute threshold (1.0 = 0 min) |
| **Transport Score** | `0.15` | Monthly transport cost relative to household income (0% burden = 1.0, ≥50% = 0.0) |
| **Family Score** | `0.15` | Proximity fit across requested amenities (Schools, Hospitals, Pharmacies) |
| **Work Access Score** | `0.10` | Reachability to secondary employment hubs within 45 minutes |
| **Confidence Score** | `0.05` | Data provenance certainty (`HIGH` = 1.0, `MEDIUM` = 0.6, `LOW` = 0.2) |
| **Total** | **`1.00`** | Normalized aggregate score |

---

## 9. Routing Architecture

RIVO uses a tiered provider fallback chain to balance live Google API accuracy, offline reproducibility, and quota safety:

```text
                  Incoming Route Request
                            │
                            ▼
               Is Redis Cache Warm (< 1 hr)?
                 ├── YES ──► Return Cached Route (Label: RECENT)
                 └── NO
                            │
                            ▼
              Is GOOGLE_ROUTES_API_KEY Configured?
                 ├── YES ──► Call Google Routes v2 (computeRoutes)
                 │           (Label: LIVE, Quota Tracker decrements)
                 └── NO
                            │
                            ▼
              Does CUMTA/MTC GTFS Graph have Route?
                 ├── YES ──► Compute Timetable Transit Route (Label: PERIODIC)
                 └── NO
                            │
                            ▼
              Is OpenTripPlanner (OTP) Server Online?
                 ├── YES ──► Call Local OTP 2.10 Engine (Label: ESTIMATED)
                 └── NO
                            │
                            ▼
              Deterministic Mock Router Fallback
              Haversine Distance × 1.3 Chennai Road Curvature
              (Label: ESTIMATED / SAMPLE DATA)
```

### Safety & Quota Architecture
- **Server-Side Key Isolation:** Google API keys are stored only in `backend/.env` and are never exposed to the client.
- **Request Budgets:** `RequestBudgetManager` enforces strict per-request limits:
  - Max 10 routes per search
  - Max 8 places searches
  - Max 5 detailed routes
- **Circuit Breaker:** Automatically trips after consecutive upstream failures, gracefully degrading to local GTFS routing without throwing 500 errors.
- **Field Masks:** Live Google requests use explicit `X-Goog-FieldMask` headers requesting only essential route legs, avoiding charges for unneeded attributes.

---

## 10. Rental Data Architecture

Rental data is handled with strict provenance tracking to ensure demo data never contaminates production market intelligence.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        RENTAL DATA PROVIDERS                           │
├─────────────────────────┬─────────────────────────┬────────────────────┤
│   RIVO Direct           │   Authorized Partner    │   Mock Provider    │
│   First-party verified  │   Commercial API        │   88 CMRL-anchored │
│   listings submitted by │   adapter (inactive     │   seed listings    │
│   verified owners       │   until licensed)       │   for local demo   │
│   [LIVE / VERIFIED]     │   [PERIODIC]            │   [DEMO / PERIODIC]│
└────────────┬────────────┴────────────┬────────────┴──────────┬─────────┘
             │                         │                       │
             ▼                         ▼                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│               UNIFIED OBSERVATION SERVICE & STORAGE                    │
│   • Enforces mandatory provenance: listing_id, locality, bhk, rent,   │
│     observed_at, source                                                │
│   • Assigns Verification: VERIFIED_DIRECT, VERIFIED_AD, UNVERIFIED     │
│   • Assigns Availability: AVAILABLE, PENDING, RECENTLY_SEEN, RENTED    │
│   • Tracks Observation History (does not overwrite past prices)        │
│   • Strict Separation: is_demo=True / is_synthetic=True records are    │
│     EXCLUDED from ML gates, data-quality reports, and market medians   │
└────────────────────────────────────────────────────────────────────────┘
```

> **CRITICAL DATA AUDIT:**  
> Current Verified Genuine Rental Observations in Repository: **`0`**  
> Seed Demo Listings (CMRL Metro Corridors): **`88`** (labelled `DEMO` / `PERIODIC`)  
> Current Real Rental Market Inventory: **`0`**  
> Synthetic Data Ratio Allowed for ML: **`≤ 10.0%`**

---

## 11. Rent Intelligence & ML

RIVO includes a complete statistical and machine learning pipeline in `backend/app/services/ml/` that is **intentionally blocked** by an automated eligibility gate.

### Model Eligibility Safeguards
The ML pipeline executes an eligibility gate (`backend/app/services/ml/eligibility.py`) before allowing any training:

| Gate Parameter | Required Threshold | Current Value | Gate Status |
|---|---|---|---|
| **Real Observations** | $\ge 50$ | `0` | ❌ BLOCKED |
| **Unique Properties** | $\ge 30$ | `0` | ❌ BLOCKED |
| **Unique Localities** | $\ge 5$ | `0` | ❌ BLOCKED |
| **BHK Classes** | $\ge 3$ | `0` | ❌ BLOCKED |
| **Independent Sources** | $\ge 2$ | `0` | ❌ BLOCKED |
| **Temporal Span** | $\ge 7$ days | `0` | ❌ BLOCKED |
| **Synthetic Ratio** | $\le 10\%$ | `0.0%` | ✅ PASS |
| **Overall ML Status** | **READY** | **NOT_READY_INSUFFICIENT_DATA** | ❌ **BLOCKED** |

### ML Pipeline Architecture (Ready for Real Data)
When real observations fulfill all gates, `python -m scripts.train_rent_model` executes:
1. **Baseline Model:** Hierarchical median fallback (Locality + BHK $\rightarrow$ Locality $\rightarrow$ Citywide BHK median).
2. **Feature Extraction:** Spatial transit density (GTFS stops within 800m), hospital/school counts, distance to Central Chennai, H3 resolution 8/9 indexes.
3. **Quantile Regression:** LightGBM models trained on pinball loss for $P_{25}$, $P_{50}$, and $P_{75}$ rent distributions.
4. **Temporal Split Validation:** Strictly chronologically split train/test datasets to prevent future leakage.
5. **Promotion Guardrails:** ML candidate must achieve lower MAE and valid quantile ordering ($P_{25} < P_{50} < P_{75}$) before replacing baseline.

---

## 12. Data Quality & Trust

RIVO guarantees that bad, synthetic, or unverified records cannot silently enter the analytical engine.

### Trust Lifecycle

```text
1. Collect
   Field enumerator records property using standardized CSV template
   ↓
2. Validate
   Pydantic schema enforces types, valid Chennai coordinates (lat: 12.75–13.35, lon: 80.00–80.35)
   ↓
3. Quality Check
   quality_warnings() evaluates geocode confidence, source attribution, and freshness
   ↓
4. Deduplicate
   Spatial coordinate matching (≤ 50m) and price similarity cluster near-duplicates
   ↓
5. Classify & Label
   Assigns provenance, data_freshness (LIVE / PERIODIC / ESTIMATED), and verification tier
   ↓
6. Observe Again
   Updates create new time-stamped RentalObservation rows to preserve longitudinal price history
   ↓
7. Audit
   GET /api/v1/rentals/admin/collection-progress tracks real vs demo records in real time
```

---

## 13. Current Data Status

| Dataset / Component | Primary Source | Current State | Classification | Consumed By |
|---|---|---|---|---|
| **Rental Listings (Demo)** | CMRL Metro Corridors Seed | 88 records | `PERIODIC` / `ESTIMATED` | RIVO Home Search (Sample/Demo mode) |
| **Rental Observations** | Field Collection / Ingestion | 0 real records | `NOT READY` | Observation Service & ML Gate |
| **Bus Transit Timetables** | CUMTA GTFS Feed | Offline snapshot | `PERIODIC` | Local Route Engine (`route_gtfs.py`) |
| **Metro Transit Timetables** | CMRL GTFS / Project Data | Offline snapshot | `PERIODIC` | Local Route Engine (`route_gtfs.py`) |
| **Live Route Computation** | Google Routes API v2 | Optional / Keyed | `LIVE` / `RECENT` | Route Provider (`route_google.py`) |
| **Health Facilities** | Chennai Health Infra OGD | 54 seed facilities | `PERIODIC` | Facility Matcher (`facilities.py`) |
| **School Facilities** | UDISE+ / OSM | 62 seed facilities | `PERIODIC` | Facility Matcher (`facilities.py`) |
| **Worker Incomes** | PLFS 2025 TN Urban | 5 occupations | `PERIODIC` | Worker Profile Engine (`workers.py`) |
| **Ward Boundaries & Density** | Greater Chennai Corp GIS | 200 wards (GIS) | `PERIODIC` | Scenario Engine (`scenarios.py`) |
| **Rent ML Quantile Model** | LightGBM Pipeline | Untrained | `NOT READY` | Rent Estimation (`rent_model.py`) |

---

## 14. Where the Project Stands Today

### Completed Engineering
- Full end-to-end recommendation engine with 15-stage filtering, routing, scoring, and explainability.
- Multi-dimensional affordability model accounting for rent, transit fares, two-wheeler fuel, and commute hours.
- Frontline worker income calibrations from PLFS 2025 for 5 core occupations.
- Multimodal routing integrating Google Routes API v2, local CUMTA/MTC GTFS, and mock fallbacks.
- Planner scenario evaluation engine with 800m station pedestrian buffers and demographic projections.
- RIVO Direct listing and admin field observation collection endpoints.
- Automated ML eligibility safeguards, data-quality reporting, and collection progress tracking.
- Interactive React 19 + Leaflet frontend with modern responsive Tailwind CSS styling.
- 246 automated tests passing with 0 failures and 0 Google API quota calls during development.

### Current Blocker
- **Ground-Truth Rental Observations:** The system has **0 genuine field rental observations**. It requires 50+ real, non-synthetic observations across at least 5 Chennai localities to unlock the ML rent model.

### Not Yet Activated
- **Production ML Rent Model:** Intentionally inactive (`NOT_READY_INSUFFICIENT_DATA`).
- **Live Google Routes in Local Dev:** Intentionally bypassed via mock/GTFS routers unless explicit credentials are provided and `RIVO_LIVE_API_TESTS=true`.
- **Third-Party Rental Scraping:** Intentionally rejected; RIVO does not perform unauthorized scraping of protected rental portals.

### Why RIVO Refuses to Fabricate Data
Many hackathon submissions fabricate data or use LLMs to hallucinate asking rents. RIVO explicitly rejects this. When real rental data is absent, the system displays `INSUFFICIENT_DATA`, blocks model training, and provides an operational collection interface to gather real facts. **Data honesty is a core architectural feature.**

---

## 15. Development Phases

- **Phase 1 — Audit & Baseline Architecture:** Established project boundaries, core schemas, and repository structure.
- **Phase 2 — Core Infrastructure & GTFS Engine:** Integrated CUMTA GTFS transit timetables, UDISE+ schools, health facilities, H3 spatial indexing, and basic scenario engine.
- **Phase 3 — Live Google Integrations:** Built Google Routes API v2 and Google Places (New) adapters with transient caching.
- **Phase 4/5 — Hardening & Deterministic Verification:** Implemented circuit breakers, field masks, request trackers, and zero-key local fallbacks.
- **Phase 6 — Google Live Verification:** Verified live Chennai routes and nearby places with authenticated Google test suites.
- **Phase 7 — Quota Protection & Funnel Optimization:** Introduced candidate pruning ($\le 15$ finalists) and coarse route matrices to prevent excessive API consumption.
- **Phase 7.1 — Safety Switch Separation:** Completely decoupled test-suite execution (`RIVO_LIVE_API_TESTS=false`) from application runtime API access.
- **Phase 8 — Rental Inventory & Deduplication:** Built RIVO Direct provider, multi-provider registry, and spatial deduplication.
- **Phase 9 — Rent Intelligence & Eligibility Safeguards:** Built LightGBM quantile regression pipeline and established the 7-parameter ML gate.
- **Phase 10 — Observation Acquisition Pipeline:** Created bulk ingestion scripts (CSV/JSON/NDJSON) and observation history models.
- **Phase 11 — Real Data Readiness Audit:** Validated that production models remain blocked until genuine observations are recorded.
- **Phase 12 — Operational Field Collection:** Built mobile-friendly field quickstart guide, `/admin/collection-progress` tracking endpoint, quality warning heuristics, and Phase 12 operational test suite.

---

## 16. API Endpoints

All backend endpoints are mounted under `/api/v1` (with system endpoints at root):

### System & Health
- `GET /` — API service metadata and version
- `GET /health` — Health check, circuit breaker status, and Google API status

### Recommendations (RIVO Home)
- `POST /api/v1/recommendations/search` — Execute full 15-stage recommendation pipeline
- `POST /api/v1/recommendations/detail` — Retrieve detailed multimodal itinerary for a selected home

### Rentals & Market Intelligence
- `GET /api/v1/rentals/search` — Search listings with spatial and budget filters
- `GET /api/v1/rentals/{listing_id}` — Retrieve single rental listing details
- `GET /api/v1/rentals/{listing_id}/history` — Retrieve time-series observation history
- `POST /api/v1/rentals/direct` — Submit first-party RIVO Direct rental listing
- `PATCH /api/v1/rentals/direct/{listing_id}` — Update availability or rent for direct listing
- `GET /api/v1/rentals/market-summary` — Locality/BHK rent summary
- `GET /api/v1/rentals/real-market-summary` — Strict real-data-only market summary (excludes demo listings)
- `POST /api/v1/rentals/market-estimate` — Predict rent percentiles ($P_{25}, P_{50}, P_{75}$)
- `GET /api/v1/rentals/eligibility` — Inspect ML model eligibility status and gate checklist
- `GET /api/v1/rentals/admin/summary` — Admin inventory and provider summary
- `POST /api/v1/rentals/admin/collect` — Field-agent observation intake endpoint
- `GET /api/v1/rentals/admin/data-quality` — Detailed data-quality report and gate metrics
- `GET /api/v1/rentals/admin/collection-progress` — Operational progress by locality, BHK, and source

### Routing & Navigation
- `POST /api/v1/routes/compare` — Compare multimodal routes (Transit, Two-Wheeler, Walk)
- `POST /api/v1/routes/itinerary` — Detailed step-by-step route itinerary with polylines

### Workers & Demographics
- `GET /api/v1/workers/occupations` — List supported Chennai frontline occupations
- `GET /api/v1/workers/income/{occupation_key}` — Retrieve PLFS 2025 income distribution

### Facilities & Amenities
- `GET /api/v1/facilities/nearby` — Query nearby schools, hospitals, and pharmacies

### Planning Scenarios (RIVO City)
- `POST /api/v1/scenarios/evaluate` — Evaluate transit/housing intervention scenarios

### Data Sources & Transparency
- `GET /api/v1/data/sources` — Data provenance and license registry
- `POST /api/v1/data/refresh` — Trigger periodic cache and feed refresh

---

## 17. Important Scripts

All scripts are executed from the repository root using the backend virtual environment:

### Data Seeding & Facility Ingestion
```bash
# Seed initial worker profiles, datasets, and 88 demo listings into SQLite/Postgres
backend/.venv/Scripts/python -m scripts.seed_data

# Ingest Chennai health and school facilities from seed/OGD files
backend/.venv/Scripts/python -m scripts.ingest_facilities
```

### Rental Observation Ingestion
```bash
# Dry-run observation import from CSV (validates rows without writing)
backend/.venv/Scripts/python -m scripts.import_rental_observations data/templates/rivo_rental_observation_template.csv --dry-run

# Import observations and print data quality report
backend/.venv/Scripts/python -m scripts.import_rental_observations data/chennai_field_batch_01.csv --report
```

### Deterministic Persona Demo
```bash
# Run end-to-end Nurse at Rajiv Gandhi Govt Hospital workflow in CLI
backend/.venv/Scripts/python -m scripts.demo_nurse_workflow
```

### ML Rent Model Training (Gated)
```bash
# Attempt to train rent model (strictly checks eligibility gates before training)
backend/.venv/Scripts/python -m scripts.train_rent_model
```

### Google API Configuration Check
```bash
# Verify Google API key presence and circuit breaker configuration
backend/.venv/Scripts/python -m scripts.check_google_config
```

---

## 18. Setup

### Prerequisites
- **Python:** 3.11 or 3.12 (Python 3.11.0 verified)
- **Node.js:** v18+ or v20+ with npm
- **Database:** Local SQLite (automatic default) or PostgreSQL 15+ with PostGIS 3+

### 1. Clone Repository
```bash
git clone https://github.com/shanthoshkrishnan/Rivo.git
cd Rivo
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

pip install -r requirements.txt
# Optional: pip install -r requirements-extras.txt
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

### 4. Environment Configuration
```bash
cd ../backend
cp .env.example .env
```
*(The default `.env` works out-of-the-box in local mock/GTFS mode without any API keys.)*

### 5. Seed Database
```bash
# From repository root:
backend/.venv/Scripts/python -m scripts.seed_data
```

### 6. Start Applications

**Start Backend Server:**
```bash
# From repository root:
backend/.venv/Scripts/uvicorn app.main:app --app-dir backend --reload --port 8000
```
*API Swagger documentation available at: `http://localhost:8000/docs`*

**Start Frontend Development Server:**
```bash
# From frontend directory:
npm run dev
```
*Frontend interface available at: `http://localhost:5173`*

### 7. Production Frontend Build Verification
```bash
# From frontend directory:
npm run build
```
*(Executes `tsc -b && vite build` — compiles cleanly in ~1.0s).*

---

## 19. Environment Variables

All variables are loaded via `backend/app/core/config.py` from `backend/.env`:

| Variable | Required? | Default | Purpose |
|---|---|---|---|
| `APP_ENV` | Optional | `development` | Environment mode (`development`, `staging`, `production`) |
| `APP_SECRET_KEY` | Optional | `change-me...` | Application secret key for signing |
| `DATABASE_URL` | Optional | `sqlite+aiosqlite:///...` | Async database connection string |
| `DATABASE_SYNC_URL` | Optional | `sqlite:///...` | Sync connection string for Alembic/seeding |
| `REDIS_URL` | Optional | `redis://localhost:6379/0` | Transient route and listing cache |
| `GOOGLE_ROUTES_API_KEY` | Optional | `""` | Google Routes API v2 key for live transit routes |
| `GOOGLE_PLACES_API_KEY` | Optional | `""` | Google Places API (New) key for nearby facilities |
| `RIVO_LIVE_API_TESTS` | **Test Only** | `false` | When `false`, test suite strictly refuses external Google calls |
| `ROUTE_SEARCH_BUDGET` | Optional | `10` | Max Google Routes calls allowed per search request |
| `PLACES_SEARCH_BUDGET` | Optional | `8` | Max Google Places calls allowed per search request |
| `RENTAL_PROVIDER` | Optional | `mock` | Primary provider (`mock`, `open_dataset`, `licensed`) |
| `DEFAULT_PETROL_PRICE_INR` | Optional | `105.0` | Petrol cost per liter in Chennai for vehicle cost calculation |
| `DEFAULT_DIESEL_PRICE_INR` | Optional | `92.0` | Diesel cost per liter in Chennai |
| `CORS_ORIGINS` | Optional | Localhost ports | Allowed CORS origins for web application |

---

## 20. Testing

RIVO features a comprehensive automated test suite covering unit math, API contracts, integration flows, and data safeguards.

### Running Tests
```bash
# Run complete test suite (246 unit & integration tests, 8 skipped live tests):
backend/.venv/Scripts/pytest backend/tests -v

# Run with short tracebacks:
backend/.venv/Scripts/pytest backend/tests -q
```

### Verified Test Results
```text
============================= test session summary =============================
Platform: Windows (Python 3.11.0) / Pytest 9.1.1
Collected: 254 items

PASSED:  246 tests (100% of non-external tests)
SKIPPED: 8 tests (Live Google tests intentionally skipped to protect quota)
FAILED:  0 tests
TIME:    ~8.6 seconds
```

### Zero-Quota Test Safety
All unit and integration tests use mocked Google responses, local GTFS tables, and deterministic fixtures. **0 Google API calls** are made during standard test execution.

---

## 21. Google API & Quota Safety

RIVO implements enterprise-grade quota protection to ensure development and testing never exhaust live API limits:

1. **Safety Switch (`RIVO_LIVE_API_TESTS=false`):** Live test files (`backend/tests/live/*`, `verify_live_google.py`) automatically detect this flag and skip execution.
2. **Key Isolation:** Keys are never transmitted to client browsers or printed in log files.
3. **Route Candidate Funnel:** Spatial filters prune the candidate pool from 88+ properties down to at most 15 finalists before evaluating routes.
4. **Per-Request Hard Budgets:** `RequestBudgetManager` caps API consumption per HTTP request.
5. **Circuit Breaker:** Tracks upstream HTTP 429 (Too Many Requests) or 5xx errors and opens after 3 failures, cleanly routing requests through local GTFS and OpenTripPlanner fallbacks.

---

## 22. Data Collection Workflow

To advance RIVO from demo status to a production-grade rent surface, field teams follow the Phase 12 operational protocol:

### Field Collection Steps
1. **Field Observation Template:** Collect observations using [data/templates/rivo_rental_observation_template.csv](file:///c:/Project/Hackathons/Sustain-a-thon/Code/data/templates/rivo_rental_observation_template.csv).
2. **Mobile Quickstart Guide:** Consult [docs/field/RIVO_FIELD_COLLECTION_QUICKSTART.md](file:///c:/Project/Hackathons/Sustain-a-thon/Code/docs/field/RIVO_FIELD_COLLECTION_QUICKSTART.md) for coordinate capture, availability classification (`AVAILABLE`, `PENDING_CONFIRMATION`), and verification states (`VERIFIED_DIRECT`, `VERIFIED_AD`).
3. **Dry-Run Import:**
   ```bash
   python -m scripts.import_rental_observations data/my_batch.csv --dry-run
   ```
4. **Execute Import & Review Data Quality:**
   ```bash
   python -m scripts.import_rental_observations data/my_batch.csv --report
   ```
5. **Inspect Live Gate Status:**
   ```bash
   curl http://localhost:8000/api/v1/rentals/admin/collection-progress
   ```

### Target Initial Quota
- **5 Localities:** Velachery, Guindy, Thiruvanmiyur, Sholinganallur, Chromepet
- **10 Properties per Locality:** 50 genuine properties total
- **Diversity:** Minimum 3 BHK classes (1BHK, 2BHK, 3BHK) across at least 2 independent sources (e.g., `field_agent`, `owner_interview`).

---

## 23. Project Roadmap

```text
Phase 12 Complete (Current)
   │
   ▼
[Step 1: Operational Field Collection]
Deploy field enumerators across 5 target Chennai corridors to collect 50+ genuine observations.
   │
   ▼
[Step 2: Observation Validation & Deduplication]
Ingest batches via scripts.import_rental_observations; verify spatial bounds and coordinate precision.
   │
   ▼
[Step 3: Longitudinal Observation Updates]
Re-observe properties after 2–4 weeks to build time-series price change and availability delta data.
   │
   ▼
[Step 4: Unlock ML Eligibility Gate]
Automated verification that real_observations >= 50, unique_properties >= 30, localities >= 5.
   │
   ▼
[Step 5: Train & Validate Quantile Rent Surface]
Execute python -m scripts.train_rent_model; validate LightGBM P25/P50/P75 on temporal hold-out split.
   │
   ▼
[Step 6: Activate Spatial Rent Surface in RIVO City]
Publish smoothed H3 resolution 8/9 rent surface tiles across Chennai Metropolitan Area.
   │
   ▼
[Step 7: Stakeholder Pilot & Institutional Deployment]
Conduct pilot reviews with Chennai Unified Metropolitan Transport Authority (CUMTA) and CMDA planners.
```

---

## 24. Limitations & Honest Status

- **Rental Market Data:** The current repository contains **0 genuine Chennai rental observations** and 88 CMRL-anchored demo properties. Production rent estimates are withheld until real field data is populated.
- **ML Rent Model:** Currently inactive by design (`NOT_READY_INSUFFICIENT_DATA`).
- **Live Google API Usage:** Live route calculation requires valid user-supplied Google API keys; otherwise, the system seamlessly operates on local GTFS and mock routers.
- **No Unauthorized Scraping:** RIVO does not bypass CAPTCHAs, Cloudflare, or login firewalls of commercial rental portals. Data acquisition relies exclusively on direct listings, authorized partnerships, and field observation.
- **Single-City Scope:** The current MVP is exclusively built and calibrated for the **Chennai Metropolitan Area (CMA)**.

---

## 25. Demo Flow

Evaluators can test both RIVO Home and RIVO City in under 3 minutes:

### 1. Launch Applications
Follow the [Setup](#18-setup) instructions to launch backend (`:8000`) and frontend (`:5173`).

### 2. Experience RIVO Home (Nurse Persona)
1. Open `http://localhost:5173`.
2. Notice the pre-filled persona: **Nurse / Healthcare Worker** at **Chennai Central / Park Town**.
3. **Inspect Inputs:**
   - Household Income: ₹24,000 / month (calibrated from PLFS 2025).
   - Max Rent Budget: ₹15,000.
   - Max Commute: 60 minutes via Transit & Walking.
   - Family: 2 Adults, 1 Child (Age 6–12), School $\le$ 20 min, Hospital $\le$ 25 min.
4. **Click "Find Homes":**
   - The interactive Leaflet map centers on Chennai Central and renders candidate rental homes within the 18km radius.
   - Click any listing card (e.g., in Chintadripet or Egmore) to inspect the **Affordability Breakdown**:
     - Housing Burden (Rent / Income)
     - Transport Burden (Fare / Income)
     - Cash Burden (Total Outflow / Income)
     - Monthly Commute Hours (Time Tax)
   - View nearby facilities (Schools, Hospitals, Pharmacies) with walking times.
5. **View Multimodal Route:**
   - Click **"View Multimodal Commute"** to open the route timeline modal showing walking legs, metro boardings, transfers, and fare breakdown.

### 3. Experience RIVO City (Planning Mode)
1. Click the **"City Planner"** tab in the top navigation.
2. Select an occupation (e.g., **School Teacher** or **Nurse**).
3. Select an infrastructure scenario (e.g., **CMRL Phase II Corridor Extension** or **Bus Feeder Optimization**).
4. Click **"Evaluate Spatial Impact"**:
   - Inspect the **WorkerReach** metrics comparing 30-min, 45-min, and 60-min reachable worker populations.
   - View the before-and-after affordability shift and pedestrian catchment buffer statistics.

### 4. Review Data Provenance
1. Click the **"Data Sources"** tab in the top navigation.
2. Review the 11 registered authoritative datasets (GCC GIS, CUMTA GTFS, PLFS 2025, UDISE+, WorldPop) with licensing terms and update frequencies.

---

## 26. Repository Structure

```text
Rivo/
├── AGENTS.md                   # Agent guidelines & project invariants
├── ALGORITHMS.md               # Mathematical specifications of all formulas
├── ARCHITECTURE.md             # System architectural blueprints
├── DATA_LICENSES.md            # Data source licensing registry
├── DATA_SOURCES.md             # Authoritative Chennai data inventory
├── README.md                   # Master evaluator & technical documentation
├── backend/
│   ├── alembic/                # Database migrations (PostGIS / SQLite)
│   ├── app/
│   │   ├── api/v1/             # REST endpoints (rentals, routes, scenarios, etc.)
│   │   ├── core/               # Configuration, circuit breaker, logging, budgets
│   │   ├── db/                 # Session management, Redis caching
│   │   ├── models/             # SQLAlchemy ORM models (Rental, Facility, Worker)
│   │   ├── schemas/            # Pydantic v2 data contracts
│   │   ├── services/
│   │   │   ├── algorithms/     # Pure math: affordability, scoring, scenario engine
│   │   │   ├── ml/             # Eligibility gate, LightGBM quantile regression
│   │   │   └── providers/      # Google, GTFS, OTP, RIVO Direct, Mock adapters
│   │   └── utils/              # Spatial helpers, H3 indexing, Haversine
│   ├── data/seed/              # Seed fixtures (facilities, GTFS tables, demo listings)
│   ├── requirements.txt        # Backend dependencies
│   ├── scripts/                # Seeding, import, training, verification scripts
│   └── tests/                  # 254 unit, integration, and live tests
├── data/
│   ├── seed/                   # Raw seed files (GTFS, facilities, rentals)
│   └── templates/              # Standardized CSV field collection templates
├── docs/
│   ├── field/                  # Mobile-friendly field quickstart guide
│   └── reports/                # Phase 1 through Phase 12 verification reports
└── frontend/
    ├── package.json            # React 19, Vite 8, Tailwind v4, Leaflet
    ├── src/
    │   ├── components/
    │   │   ├── DataSources/    # Transparency registry view
    │   │   ├── RivoCity/       # Urban planning scenario interface
    │   │   └── RivoHome/       # Search form, listing card, Leaflet map, route modal
    │   ├── services/           # Backend API client integration
    │   └── types/              # TypeScript API contract definitions
    └── vite.config.ts          # Vite build configuration
```

---

## 27. Data Licenses & Attribution

RIVO respects the terms of all authoritative data providers:

- **Greater Chennai Corporation (GCC) GIS 2025:** City administrative wards, zones, and population density benchmarks.
- **Chennai Unified Metropolitan Transport Authority (CUMTA):** Chennai metropolitan transit stops, route geometries, and GTFS schedules.
- **Periodic Labour Force Survey (PLFS) 2025:** Ministry of Statistics and Programme Implementation (MoSPI) microdata for Tamil Nadu Urban wage distributions.
- **Chennai Health Infrastructure (OGD Platform India):** Government general hospitals, urban primary health centers, and dispensaries.
- **UDISE+ (Department of School Education & Literacy):** Chennai government and aided school locations.
- **OpenStreetMap (OSM):** Base street network and local commercial amenities under the Open Database License (ODbL).
- **WorldPop (2025):** 100m spatial population distributions (CC BY 4.0).
- **Google Maps Platform (Routes API v2 & Places API New):** Transient live route comparisons subject to Google Maps Platform Terms of Service (transient caching $\le 1$ hour; no permanent data storage).

---

## 28. Final Evaluator Summary: Why RIVO

1. **Worker-Centered Urban Economics:** Moves beyond nominal rents to evaluate the true financial and physical toll of urban living on the frontline workers who keep Chennai functioning.
2. **Transparent Multi-Dimensional Affordability:** Eliminates opaque "AI scores" in favor of explainable metrics: Housing Burden, Transport Burden, Cash Burden, and Commute Time Tax.
3. **Real-World Multimodal Accessibility:** Synthesizes Chennai Metro, MTC buses, two-wheelers, and walking into realistic door-to-door transit plans.
4. **Family-Aware Housing Discovery:** Integrates school, healthcare, and pharmacy access directly into the housing search funnel.
5. **Rigorous Data Integrity & Anti-Fabrication Safeguards:** Intentionally refuses to train ML models on synthetic or insufficient data, demonstrating true engineering discipline and data governance.
6. **Unified Dual-Mode Platform:** Connects individual worker housing decisions with macro-level spatial transit and housing scenario planning for municipal authorities.
