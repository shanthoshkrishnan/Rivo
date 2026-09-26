# RIVO — Project Context

## Team
Team: CLAIRES
Team ID: ST1010
Pilot city: Chennai

## Problem
PS-11-S3 describes workers such as nurses, teachers, bus drivers and delivery riders being pushed toward the urban edge because housing and jobs are not planned as one system.

The required model connects:
- rental conditions
- realistic transport accessibility
- occupation-specific income
- employment opportunity
- time/cost burden
- policy interventions

Source: supplied `Software_Problem_Statements.pdf`.

## Product
RIVO = worker housing + mobility intelligence.

### RIVO Home
User supplies:
- workplace
- household income
- adults
- children
- child age bands
- home requirement
- rent budget
- transport modes
- maximum walking time
- maximum transfers
- maximum commute
- school/hospital/pharmacy limits

Result:
- live/current rental candidates when available
- rent + maintenance
- route alternatives
- time
- distance
- fare
- monthly commute cost
- transfers
- family facilities
- confidence/freshness
- explainable recommendation

### RIVO City
Planner supplies:
- occupation
- income percentile/band
- commute threshold
- city geography
- scenario

Result:
- affordable-accessible zones
- job reach
- commute time/tax
- transport burden
- before/after scenario metrics

## Family feedback
Feedback to CLAIRES requested:
- number of children
- essential facilities including schools, hospitals and pharmacies

Implement this as a **Family Accessibility layer**.

It should enhance the core PS rather than replace it.

## Key insight
A low-rent house is not necessarily a low-cost or livable house.

RIVO considers:
- housing cost
- transport cost
- commute time
- workplace access
- family-facility access

## Data truth model
Actual:
- listing information returned by a provider
- route response returned by a routing provider
- source facility records

Estimated:
- rent surface predictions
- employment opportunity weights
- inferred facility/job coverage

Historical:
- historical datasets/reports

Always display status/source/freshness.

## Existing precedent
Relevant prior art:
- CNT Housing + Transportation Index
- HUD Location Affordability Index
- Conveyal/R5
- OpenTripPlanner
- Indian academic H+T work

Do not claim RIVO invented H+T. RIVO's differentiator is the integrated Chennai/India worker-and-family model.

## Current Chennai inputs
- CUMTA GTFS for transit
- GCC 2025 GIS for current administrative geography
- PLFS 2025 for occupation/earnings
- Chennai Health Infrastructure OGD for health facilities/nurse opportunity
- UDISE+ / mapped schools
- OSM for roads and POIs
- WorldPop 2025 for population weighting
- CMRL Phase II for a real transit scenario
- MTC/CMRL fare sources
