# `app/models/` — SQLAlchemy ORM Models

All database tables are defined here as SQLAlchemy 2.0 mapped classes.
Every model inherits from `app.db.session.Base`.

PostGIS `GEOMETRY(POINT, 4326)` columns are used for all spatial data.
H3 index (`h3_index VARCHAR(20)`) is stored alongside geometry for cheap hex-level queries.

---

## Files

### `rental.py` — `RentalListing`

Maps to `rental_listings` table.

Key fields:
| Field | Purpose |
|---|---|
| `provider` | Source identifier (mock / open_dataset / licensed) |
| `listing_id` | Provider-specific listing ID |
| `geom` | PostGIS POINT (WGS-84) — enables spatial queries |
| `h3_index` | H3 resolution-9 hex for aggregation |
| `rent_monthly` | Normalised monthly rent in INR |
| `rent_monthly_raw` | Original value before normalisation (audit trail) |
| `bhk`, `area_sqft` | Physical attributes |
| `furnishing` | `unfurnished / semi-furnished / fully-furnished` |
| `model_rent_p25/p50/p75` | ML model outputs (null until pipeline runs) |
| `data_confidence` | `HIGH / MEDIUM / LOW` |
| `data_freshness` | `LIVE / PERIODIC / ESTIMATED / HISTORICAL` |
| `duplicate_cluster_id` | Groups near-duplicate listings |
| `is_canonical` | `True` for the primary listing in a duplicate cluster |

Unique constraint: `(provider, listing_id)` — re-ingesting updates, never duplicates.

---

### `worker.py` — `WorkerProfile`, `IncomeProfile`, `Workplace`

**`WorkerProfile`** — occupation types RIVO reasons about.
- `occupation_key`: `nurse / teacher / bus_driver / delivery_rider / construction_worker`
- `nic_code`, `nco_code`: Aligned with PLFS 2025 NIC-2008 / NCO codes

**`IncomeProfile`** — PLFS-derived income distribution per occupation × geography.
- Geography fallback chain: `chennai → tamil_nadu_urban → india_urban`
- Stores `income_p25 / income_median / income_p75 / sample_size / confidence`
- **CRITICAL**: Do not claim exact salaries. These are survey-based estimates.

**`Workplace`** — Known employment locations (hospitals, schools, depots, hubs).
- `estimated_jobs / jobs_lower / jobs_upper / confidence` — always a range, never a point claim.
- `relevant_occupations`: JSON list of occupation keys (e.g. `["nurse","doctor"]`)

---

### `facility.py` — `School`, `Hospital`, `Pharmacy`

Three facility tables for the Family Accessibility layer.

| Model | Source | Freshness |
|---|---|---|
| `School` | UDISE+ | PERIODIC (annual) |
| `Hospital` | Chennai Health OGD | PERIODIC |
| `Pharmacy` | OpenStreetMap + optional Google Places | PERIODIC |

All three share: `geom`, `h3_index`, `gcc_ward`, `latitude`, `longitude`, `address`, `source_name`, `data_freshness`.

`Hospital` additionally stores `bed_count` and `nurse_count` for nurse job-opportunity estimation.

---

### `routing.py` — `RouteCache`, `TransitStop`, `TransitFare`

**`RouteCache`** — Stores computed route results to prevent redundant API calls.
- Cache key: `(origin_h3, dest_h3, mode, departure_bucket, provider)`
- `departure_bucket`: time rounded to 30-min window (e.g. `"08:00"`)
- `expires_at`: set to `NOW() + ROUTE_CACHE_TTL` on insert

**`TransitStop`** — GTFS stops from CUMTA feed.

**`TransitFare`** — MTC bus and CMRL metro fare rules (distance-band → INR).

---

### `recommendation.py` — `RecommendationResult`, `Scenario`, `ScenarioResult`

**`RecommendationResult`** — Persisted recommendation for audit and reproducibility.
- Component scores stored separately: `score_housing`, `score_commute`, `score_transport`, `score_family`, `score_work_access`, `score_confidence`
- `why_recommended` / `why_not_recommended`: pipe-separated human-readable reasons (data-driven, no LLM)

**`Scenario`** + **`ScenarioResult`** — RIVO City scenario engine tables.
- Before/after `worker_reach_30/45/60min` and `affordable_listings` per scenario.

---

### `data_source.py` — `DataSource`

Registry entry for every external data source.
Implements `DATA_LICENSES.md` metadata block:
- `license`, `attribution`, `commercial_use_allowed`, `redistribution_allowed`, `retention_limits`
- `retrieved_at`, `effective_date`, `data_freshness`

---

## Spatial strategy (per ARCHITECTURE.md)

Every spatial record gets:
- `latitude`, `longitude` — decimal degrees WGS-84
- `geom GEOMETRY(POINT, 4326)` — PostGIS for spatial queries
- `h3_index VARCHAR(20)` — H3 resolution 9 (~174 m hex) for aggregation
- `gcc_ward VARCHAR(16)` — GCC ward from GCC GIS 2025
