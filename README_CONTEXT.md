# RIVO Coding Context Pack

Read in order:
1. AGENTS.md
2. PROJECT_CONTEXT.md
3. DATA_SOURCES.md
4. ARCHITECTURE.md
5. ALGORITHMS.md
6. MVP_14H_PLAN.md
7. UI_UX_SPEC.md
8. DATA_LICENSES.md

## Target
Build a Chennai-first working prototype for PS-11-S3.

## Core product
```text
RIVO Home
actual rental candidates
+
income
+
family needs
+
workplace
+
transport preference
+
route computation
+
family facilities
=
explainable home recommendations
```

```text
RIVO City
occupation
+
rent surface
+
job opportunity
+
transit
=
worker affordability/accessibility
+
scenario comparison
```

## Core data flow
```text
Rental
PLFS
CUMTA GTFS
GCC GIS
OSM
Health / UDISE
WorldPop
CMRL scenario
       |
       v
normalize
       |
       v
PostGIS + H3
       |
   +---+---+
   |       |
 rent    route
 model   engine
   |       |
   +---+---+
       |
 facilities
       |
       v
recommendation
       |
       v
Next.js + MapLibre
```

## Hard truth
The hardest live data source is granular rental availability. Build the system with provider adapters and seed/local fallback rather than coupling the codebase to one portal.

## Do not hard-code demo answers
All displayed recommendation numbers must come from loaded data or a documented fixture. Mark fixtures as demo/sample.
