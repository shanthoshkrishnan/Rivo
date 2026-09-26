# RIVO — Master Coding-Agent Instructions

## Mission
Build RIVO for Team CLAIRES (ST1010), targeting:
**PS-11-S3 — Can the People Who Run the City Afford to Live In It?**

RIVO is a Chennai-first housing + mobility intelligence platform with two modes:

1. **RIVO Home** — finds currently available/known rental homes that fit income, household, housing requirements, workplace, transport preferences and family needs.
2. **RIVO City** — lets planners study worker affordability/accessibility and compare housing/transit scenarios.

## PS requirements
The supplied PS requires:
- spatial rent surface
- realistic door-to-door accessibility
- occupation-specific affordability
- historical change where defensible
- proposed transit/housing intervention testing

Do not replace those requirements with the family feature. Family context is an enhancement requested in feedback to CLAIRES.

## Core product promise
> RIVO finds homes that fit your income, family and commute — and shows cities where better housing and transport should go.

## Non-negotiable rules
- Chennai first.
- Inspect the repository before modifying it.
- Never manufacture live data.
- Clearly distinguish LIVE, PERIODIC, ESTIMATED and HISTORICAL data.
- Every important estimate needs source/date/confidence metadata.
- Do not claim an estimated employee count is exact.
- Do not treat online asking rent as ground truth.
- Do not use a single opaque AI score as the only explanation.
- Keep hard constraints separate from soft preferences.
- Cache expensive routing requests.
- Do not route every listing against every destination.
- Do not build India-wide support in the 14-hour MVP.
- Do not introduce microservices, Kafka, Spark or Kubernetes for the MVP.

## Recommended stack
Frontend:
- Next.js
- TypeScript
- Tailwind CSS
- MapLibre GL JS
- ECharts/Recharts

Backend:
- FastAPI
- Pydantic
- SQLAlchemy/SQLModel

Data:
- PostgreSQL + PostGIS
- H3
- DuckDB
- Parquet/GeoParquet
- Pandas/Polars
- GeoPandas/Shapely

Routing:
- Google Routes API for live user-facing route comparison, if configured and permitted.
- OpenTripPlanner 2.10 for reproducible multimodal transit routing.
- R5 later for large-scale accessibility/scenario analysis.

ML:
- XGBoost/LightGBM for rent estimation.
- Rules/statistics for confidence.
- No LLM required for the core decision engine.

## Provider architecture
Create interfaces for:
- RentalProvider
- RouteProvider
- PlacesProvider
- FacilityProvider
- FuelPriceProvider

Implement mock/local providers so the app remains demoable without external credentials.

## Data source hierarchy
Primary Chennai/current sources:
- GCC 2025 GIS
- CUMTA GTFS
- PLFS 2025
- Chennai Health Infrastructure OGD
- UDISE+
- MTC fares
- CMRL fares/project data
- OSM
- WorldPop 2025

Rental:
- licensed/authorized provider where legally permitted
- otherwise openly licensed seed data + clearly labelled sample data

Live route:
- Google Routes API on demand
- OTP fallback/reference

## Rental filtering order
1. availability
2. property type
3. BHK
4. hard rent budget
5. tenant/household restrictions
6. location validity
7. duplicate filtering
8. spatial/facility filtering
9. route evaluation
10. recommendation ranking

## Route optimization
Never calculate thousands of routes unnecessarily.

Use:
hard filters -> spatial filters -> facility filters -> route finalists -> ranking.

Cache:
origin/destination/mode/departure bucket/provider.

## Family layer
Support:
- adults
- children count
- child age bands
- school threshold
- hospital threshold
- pharmacy threshold

Do not store child names or unnecessary personal information.

## Definition of done
A feature is complete only when:
- backend logic exists
- API contract exists
- UI consumes real backend output
- loading/error/empty states exist
- source/freshness is preserved
- important logic has a test
- app still runs locally
