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
- Next.js
- TypeScript
- Tailwind
- MapLibre GL JS
- ECharts/Recharts

### Backend
- FastAPI
- Pydantic
- SQLAlchemy/SQLModel

### Data
- PostgreSQL + PostGIS
- H3
- DuckDB
- Parquet/GeoParquet
- GeoPandas/Shapely
- Pandas/Polars

### Routing
MVP:
- Google Routes API: live user-facing route comparison
- OpenTripPlanner 2.10: open/reproducible transit routing

Later:
- R5 for batch accessibility/scenarios

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
