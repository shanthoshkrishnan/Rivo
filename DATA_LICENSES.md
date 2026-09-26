# RIVO — Data License Registry

Treat every source as separately licensed.

## Important rules
1. Downloadable does not automatically mean redistributable.
2. API access does not automatically allow caching.
3. Do not publish raw rental data unless permitted.
4. Preserve attribution.
5. Store retrieval/effective dates.
6. Keep a source registry.
7. Review provider terms before production.

## Expected source handling

OpenStreetMap:
- ODbL
- attribution required

H3:
- open-source licence; include notices

OpenTripPlanner:
- open-source; include notices

Google Maps Platform:
- follow current Maps Platform terms, billing and caching restrictions

PLFS:
- follow government microdata access/usage terms

GCC GIS:
- verify current source terms

CUMTA GTFS:
- verify feed-specific terms and attribution

UDISE+:
- verify current reuse conditions

WorldPop:
- applicable products are CC BY 4.0; follow attribution

Rental provider:
- provider-specific; require explicit permitted basis

## Required metadata
```text
source_name
source_url
retrieved_at
effective_date
license
attribution
commercial_use_allowed
redistribution_allowed
retention_limits
notes
```
