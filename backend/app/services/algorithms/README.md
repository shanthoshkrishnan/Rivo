# `app/services/algorithms/` — Pure-Function Algorithms

All algorithms from `ALGORITHMS.md` are implemented here as **pure functions** — no database access, no external calls, no side effects.

This makes them:
- Easy to test in isolation
- Safe to call from any context (sync or async)
- Auditable: inputs → deterministic outputs

---

## `affordability.py`

### §5 Household affordability

```python
result = compute_affordability(
    rent_monthly=12000,
    maintenance_monthly=800,
    transport_cost_monthly=1600,
    household_income_monthly=24000,
    one_way_commute_minutes=38,
    work_days=22,
)
# result.housing_burden   = 0.5     (rent / income)
# result.transport_burden = 0.0667  (transport / income)
# result.cash_burden      = 0.6     (rent+maint+transport / income)
# result.monthly_commute_hours = 27.87 hours
```

### §6 Time tax
```
monthly_commute_hours = one_way_minutes × 2 × work_days / 60
```
Stored separately from money — **not** merged into an opaque score.

### §9 Monthly transit cost
```
monthly_cost = (outbound_fare + return_fare) × work_days
```

### §10 Fuel cost
```
fuel_cost = (distance_km / efficiency_kmpl) × fuel_price_inr
```

### §11 Facility fit
```python
facility_fit(travel_time_minutes=10, threshold_minutes=15)  # → True
facility_fit(travel_time_minutes=16, threshold_minutes=15)  # → False
facility_fit(travel_time_minutes=None, threshold_minutes=15) # → None (unknown)
```

### §15 Recommendation score

Default weights (tunable, not scientific):
| Component | Weight |
|---|---|
| Housing fit | 30% |
| Commute fit | 25% |
| Transport fit | 15% |
| Family fit | 15% |
| Work access | 10% |
| Confidence | 5% |

Individual score functions:
- `compute_housing_score(rent, max_rent, cash_burden)` → 0–1
- `compute_commute_score(commute_min, max_commute_min)` → 0–1
- `compute_transport_score(monthly_transport_cost, income)` → 0–1
- `compute_family_score(school_fits, hospital_fits, pharmacy_fits)` → 0–1
- `compute_total_score(...)` → 0–1 weighted aggregate

### §16 Hard constraints

```python
result = check_hard_constraints(
    rent_monthly=12000, max_rent_monthly=15000,
    bhk=2, required_bhk=2,
    property_type="flat", required_property_type="flat",
    is_available=True,
    commute_minutes=38, max_commute_minutes=60,
)
# result.passes  = True
# result.failures = []
```

Hard constraints always come before soft preferences. If `passes=False`, the listing is excluded before scoring.

### §18 Confidence

```python
level = compute_confidence_level(
    listing_count=5,
    source_diversity=2,
    has_geocode=True,
    has_route=True,
    has_facility_data=True,
)
# → ConfidenceLevel.HIGH
```

Returns `HIGH / MEDIUM / LOW` — never an arbitrary float percentage.

### Explainability

```python
positive, negative = generate_why_text(
    passes_rent=True, passes_commute=True, passes_bhk=True,
    school_fits=True, hospital_fits=False, pharmacy_fits=True,
    preferred_mode_matched=True, hard_failures=[],
)
# positive = ["within_budget", "commute_within_limit", "school_within_target", "transit_match"]
# negative = ["hospital_far"]
```

Generated from **data only** — no LLM, no opaque AI score.

---

## `normalization.py`

### §1 Normalization

| Function | Input | Output |
|---|---|---|
| `normalize_furnishing(raw)` | `"Fully Furnished"` | `"fully-furnished"` |
| `normalize_property_type(raw)` | `"Apartment"` | `"flat"` |
| `normalize_bhk(raw)` | `"2 BHK"` | `2` |
| `normalize_area_sqft(raw)` | `"850 sqft"` | `850.0` |
| `normalize_rent(raw)` | `"₹12,000"` | `12000.0` |
| `normalize_locality(raw)` | `"Anna Nagar"` | `"anna_nagar"` |
| `make_url_hash(url)` | URL string | 16-char SHA-256 hex |

Raw values are always preserved alongside normalised values.

### §2 Deduplication

```python
listings = deduplicate_listings(listings, coord_threshold_m=50.0)
# Each listing gets: duplicate_cluster_id, is_canonical
```

Deduplication uses (in order):
1. Same `(provider, listing_id)` — exact match
2. Same `url_hash`
3. Within 50 m + same BHK + rent within 10%

**Rule**: Phone numbers and image fingerprints are NOT used.

---

## Testing

All algorithm functions have unit tests in `tests/unit/test_affordability.py` and `tests/unit/test_normalization.py`.

Run:
```bash
pytest tests/unit/
```
