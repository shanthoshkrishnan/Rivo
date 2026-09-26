# `app/api/v1/endpoints/` — API Endpoint Handlers

FastAPI route handlers implementing the RIVO REST API.  
All endpoints are registered in `app/api/v1/router.py` under the `/api/v1` prefix.

---

## Endpoints

### `rentals.py` — `/api/v1/rentals`

| Method | Path | Description |
|---|---|---|
| `GET` | `/search` | Search listings with hard constraints |
| `GET` | `/{listing_id}` | Fetch single listing by ID |

**Hard constraints applied by the provider before returning:**
1. `available_only=True` — only available listings
2. `property_type` — exact match if specified
3. `bhk` — exact match if specified  
4. `max_rent_monthly` — listings at or above this are excluded

Response always includes `data_freshness` label. The UI must display this.

---

### `routes.py` — `/api/v1/routes`

| Method | Path | Description |
|---|---|---|
| `POST` | `/compare` | Compare routes for all requested modes |

Returns `RouteComparison` with all modes, badges (fastest/cheapest/fewest-transfers), and per-mode `data_freshness`.

**⚠ Do NOT use this endpoint to batch-route listings.**  
Use `POST /recommendations/search` instead — it routes only the finalists.

---

### `facilities.py` — `/api/v1/facilities`

| Method | Path | Description |
|---|---|---|
| `GET` | `/nearby` | Find nearby school/hospital/pharmacy |

Query params: `latitude`, `longitude`, `facility_type`, `radius_km`, `limit`.

Uses PostGIS `ST_DWithin` for efficient spatial queries.  
`travel_time_minutes` is estimated as walking distance at 4.5 km/h — not a routed time.

---

### `recommendations.py` — `/api/v1/recommendations`

| Method | Path | Description |
|---|---|---|
| `POST` | `/search` | Full RIVO Home pipeline |

The main endpoint. Runs:
1. Hard constraint filtering (rent, BHK, type, availability)
2. Spatial filter (within `search_radius_km`)
3. Limit to ≤ 200 route finalists
4. Route evaluation for each finalist
5. Affordability calculation
6. Family facility access check
7. Weighted scoring (housing 30%, commute 25%, transport 15%, family 15%, access 10%, confidence 5%)
8. Explainability block (data-driven, no LLM)
9. Sort descending by total score
10. Paginate

Every result includes `best_route`, `all_routes`, `affordability`, `school_access`, `hospital_access`, `pharmacy_access`, `explainability`.

---

### `workers.py` — `/api/v1/workers`

| Method | Path | Description |
|---|---|---|
| `GET` | `/occupations` | List all supported occupations |
| `GET` | `/income/{occupation_key}` | PLFS income profile for occupation |

Income profiles try: Chennai → Tamil Nadu Urban → India Urban → fixture.  
**Income values are survey estimates — not exact salaries.**

---

### `scenarios.py` — `/api/v1/scenarios`

| Method | Path | Description |
|---|---|---|
| `POST` | `/evaluate` | RIVO City scenario evaluation |

Supports `scenario_type = "transit"` or `"housing"`.  
Returns before/after worker reach (30/45/60 min bands), affordable listings, and median commute.  
All results tagged `data_freshness=ESTIMATED`.

---

### `data_sources.py` — `/api/v1/data`

| Method | Path | Description |
|---|---|---|
| `GET` | `/sources` | List all registered data sources |

Returns the full data source registry with license, attribution, and freshness information.  
Implements the transparency requirement from `DATA_LICENSES.md`.

---

## Response conventions

All API responses follow these conventions:

| Convention | Details |
|---|---|
| `data_freshness` | Every response includes this field |
| Money | All monetary values in INR (Indian Rupees) |
| Distance | Metres (`_m`) unless suffixed `_km` |
| Time | Seconds (`_seconds`) unless suffixed `_minutes` or `_hours` |
| Confidence | `HIGH / MEDIUM / LOW` — never a raw float |
| Pagination | `{total, page, page_size, results}` |
| Errors | `{detail: string}` with appropriate HTTP status |

---

## Error handling

| Scenario | HTTP Status |
|---|---|
| Missing required parameter | 422 Unprocessable Entity |
| Listing not found | 404 Not Found |
| Invalid facility_type | 400 Bad Request |
| Provider unavailable | 200 with `data_freshness=ESTIMATED` (fallback used) |
| Unhandled server error | 500 (stack trace only in non-production) |
