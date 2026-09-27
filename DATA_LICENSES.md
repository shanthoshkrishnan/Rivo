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

Google Maps Platform (Routes API v2 & Places API New):
- follow current Maps Platform terms, billing and caching restrictions (Section 3.2.3)
- only request necessary attributes via X-Goog-FieldMask (no photos, reviews, or unnecessary personal data)
- transient route/places cache limited to permitted TTL (30-60m); never store content indefinitely
- cached results must strictly be displayed as RECENT, never LIVE

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
