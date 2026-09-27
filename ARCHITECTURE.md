# RIVO — Architecture

## High-level

```text
                    RIVO
                      |
             +--------+--------+
             |                 |
          RIVO HOME         RIVO CITY
             |                 |
             +--------+--------+
                      |
                 FastAPI API
                      |
      +---------------+----------------+
      |               |                |
   Housing         Routing         Facilities
      |               |                |
  Rent model      Google/OTP       OSM / OGD
      |               |                |
      +---------------+----------------+
                      |
               PostgreSQL/PostGIS
                      |
                     H3
                      |
             Recommendation
                      |
              Next.js + MapLibre
```

## Components

### Frontend
- React 19 + TypeScript + Vite
- Tailwind CSS (vanilla CSS design tokens)
- Leaflet (warm Carto Positron basemap, route polylines, facility markers)
- Lucide React icons

### Backend
- FastAPI (Python 3.11)
- Pydantic v2
- SQLAlchemy 2.0 (AsyncSession via asyncpg / aiosqlite fallback)
- Alembic migrations

### Data & Spatial Storage
- PostgreSQL + PostGIS (primary production)
- Standalone SQLite (`data/rivo.db`) with custom spatial function stubs for local demo/testing
- H3 resolution 9 spatial indexing (with pure-Python fallback for secured OS runtimes)
- Authoritative seed fixtures (UDISE+ schools, OGD Chennai Health hospitals, OSM pharmacies, CUMTA GTFS stops)

### Routing Chain
Priority order:
1. Google Routes API (live on-demand, when API key is provided)
2. `GTFSRouteProvider` (local deterministic multimodal routing across 5,626 CUMTA/CMRL stops with real published fares and GeoJSON polylines)
3. OpenTripPlanner 2.10 (reproducible transit router fallback)
4. `MockRouteProvider` (offline emergency fallback, clearly labelled ESTIMATED)

### Route Caching
- Deterministic 4-decimal-place coordinate rounding (~11m spatial resolution)
- 30-minute departure time bucketing
- Memory LRU cache with TTL expiration (`ROUTE_CACHE_TTL = 3600s`)
- Persistent `route_cache` table schema
- Strict cache freshness semantics: Cached results are downgraded to `RECENT`, never presented as `LIVE`.

### Family Accessibility Funnel (Phase 4 — Task 5)
Cost-controlled multi-stage resolution:
1. Cheap Spatial Pre-Filter: Radius-bounded candidate discovery (up to 3 closest per facility type).
2. Nearby Search: Uses `GooglePlacesProvider` when configured, or verified local facility datasets (UDISE+, OGD Health, OSM).
3. Finalist Routing: Live Google Routes walking route is requested ONLY for the best candidate of finalist listings (never for all facilities around all rentals).
4. Exact Walking Evaluation: Actual door-to-door walking duration from Google Routes or calibrated 4.5 km/h walking speed model.

### Data Refresh Pipeline (Phase 4 — Task 8)
- Provider-aware reconciliation: `POST /api/v1/data/refresh` and `python -m scripts.refresh_data`.
- Flow: `NEW DATA -> VALIDATE -> DEDUPLICATE -> UPSERT -> MARK OBSERVED_AT`.
- Audits active rental candidates, Google Places connectivity, and periodic GTFS network feeds (CMRL & MTC).
- Safe failure handling: Never destroys working cache or active data if a refresh source is unreachable.

## Domain modules

### Housing
- provider adapters
- normalization
- dedupe
- geocoding
- rent model
- freshness

### Worker
- occupation
- income profile
- workplace opportunity

### Family
- schools
- hospitals
- pharmacies

### Routing
- provider abstraction
- mode comparison
- cache
- fare normalization

### Affordability
- budget constraints
- rent burden
- transport burden
- time tax
- facility access
- explanation

### Scenario
- new transit route
- new housing site
- before/after results

## Database tables

```text
rental_listings
rental_observations
rent_cells

worker_profiles
income_profiles

workplaces
employment_opportunities

schools
hospitals
pharmacies

transit_feeds
transit_stops
transit_routes
transit_fares

route_cache
travel_time_matrix

recommendation_results
scenarios
scenario_results

data_sources
```

## Spatial strategy
Every relevant point gets:
```text
lat/lon
H3 cell
GCC ward
```

Use H3 for:
- aggregation
- map layers
- caching
- city-level analysis

Use exact coordinates for live route computation where available.

## Routing optimization
Do not route every listing.

```text
all listings
  -> hard filters
  -> spatial filters
  -> family/facility filters
  -> 100–200 finalists
  -> route API
  -> top candidates
```

Cache route responses.

## Provider failure behavior
Rental provider down:
- use recent cache if allowed
- otherwise show estimated rent surface
- label data freshness

Google route down:
- use cached route
- use OTP for transit where possible
- show provider/freshness

Never hide provider failure.

## API surface

```text
GET  /api/rentals/search
POST /api/routes/compare
GET  /api/facilities/nearby
POST /api/recommendations/search
GET  /api/workers/occupations
POST /api/scenarios/evaluate
GET  /api/data/sources
```
