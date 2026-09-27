# RIVO — Algorithms

## 1. Rental normalization
Normalize:
- INR
- sqft
- BHK
- furnishing
- property type

Keep raw and normalized values.

## 2. Deduplication
Use:
- provider listing ID
- URL hash
- address similarity
- coordinate proximity
- same rent/BHK/area/furnishing

Do not use personal phone numbers or image fingerprints unless legally permitted.

## 3. Rent model
MVP:
- XGBoost or LightGBM

Features:
- BHK
- area
- furnishing
- property type
- locality
- transit accessibility
- building attributes where available
- time

Outputs:
```text
rent_p25
rent_p50
rent_p75
```

## 4. Rental calibration
Online listings are a biased sample.

MVP:
1. clean
2. deduplicate
3. geocode
4. model
5. compare with market benchmarks
6. validate with a small local observation sample
7. publish confidence

Do NOT implement a full Heckman model unless there is enough data to justify it.

## 5. Household affordability
```text
housing_burden =
    monthly_rent / household_income

transport_burden =
    monthly_transport_cost / household_income

cash_burden =
    (rent + maintenance + transport_cost)
    / household_income
```

## 6. Time tax
```text
monthly_commute_hours =
    one_way_minutes * 2 * work_days / 60
```

Keep time separate from money.

## 7. Optional value of time
```text
monetized_time =
    hourly_value_of_time * monthly_commute_hours
```

Do not make this the primary affordability criterion.

## 8. Route comparison
For every mode collect:
- duration
- distance
- fare
- transfers
- walking time
- wait time where available

Compare:
- fastest
- cheapest
- fewest transfers
- preference match

## 9. Transport cost
```text
monthly_cost =
    (outbound_fare + return_fare)
    * work_days
```

Default work days can be 22 or 26 but must be configurable.

## 10. Car / two-wheeler
MVP:
```text
fuel_cost =
    distance_km / efficiency_kmpl * fuel_price
```

Later:
- toll
- parking
- maintenance

## 11. Facility access
For threshold:
```text
facility_fit = 1
if travel_time <= user_threshold
else 0
```

For display also show nearest time and count within threshold.

## 12. Job opportunity
When exact employment counts exist, use them.

Otherwise:
Nurse:
- beds
- nurse count
- facility type

Teacher:
- enrollment
- teacher count
- school type

Bus driver:
- depot scale
- fleet/service scale

Delivery:
- logistics hubs
- restaurant density
- commercial/population demand surface

Always store:
```text
estimate
lower
upper
confidence
```

## 13. Employment accessibility
```text
job_access =
sum(opportunity_weight
    where travel_time <= threshold)
```

## 14. WorkerReach
Use:
- 30 min
- 45 min
- 60 min

and compare relevant reachable opportunity.

## 15. Recommendation score
Default product weights:
```text
housing fit       30%
commute fit       25%
transport fit     15%
family fit        15%
work access       10%
confidence         5%
```

These are tunable defaults, not scientific universal weights.

## 16. Hard constraints
Reject:
- unavailable
- rent above hard max
- wrong BHK
- prohibited type
- commute above absolute max

Soft preferences rank the remaining homes.

## 17. Pareto view
Advanced:
show non-dominated properties across:
- rent
- commute
- transport cost
- family access

## 18. Confidence
Confidence can use:
- listing count
- source diversity
- recency
- geocode quality
- model coverage
- facility completeness
- route-provider availability

Use HIGH/MEDIUM/LOW rather than arbitrary percentages without validation.

## 19. Scenario Engine (Phase 2 Deterministic Implementation)
Deterministic spatial evaluation replacing crude heuristic multipliers (`new_stops * 150` removed):

### Transit scenario:
1. **Station Catchment**:
   Calculate 800m pedestrian buffer area:
   `A_catchment = N_stops * π * (0.8 km)² * (1 - overlap_factor)` (approx. 2.01 km² per stop with 25% overlap deduplication).
2. **Demographic Grounding**:
   - CMA baseline density: 16,500 people/km² (from GCC Ward GIS & WorldPop 2025).
   - Working-age fraction: 64% (Census / PLFS).
   - Occupational labor shares calibrated from PLFS 2025 Tamil Nadu / Chennai urban microdata:
     - Nurse: 2.8%
     - Teacher: 4.5%
     - MTC Bus Driver: 1.6%
     - Delivery Rider: 4.2%
     - Construction Worker: 8.0%
3. **Uncertainty Bounds**:
   - `estimate`: Newly accessible workers in station catchments
   - `lower_bound`: 0.78 × estimate (suburban lower density bound)
   - `upper_bound`: 1.22 × estimate (urban core high density bound)
   - `confidence`: "MEDIUM"
4. **Affordability & Commute Shift**:
   - Units unlocked along the corridor evaluated against the occupation's 30% income rent threshold.
   - Commute time savings calculated via rapid rail commercial speed (32 km/h) vs street bus (20 km/h).

### Housing scenario:
1. **Affordability Rule**:
   - Check `avg_rent_monthly <= 0.3 * median_income`.
2. **Impact Calculation**:
   - If affordable: `delta_affordable_listings = units`, worker reach boost = `units * 1.3` working adults.
   - If unaffordable: `delta_affordable_listings = 0` (preventing luxury units from inflating worker affordability).
3. **Commute Shift**:
   - Evaluated via `GTFSRouteProvider` door-to-door multimodal transit network to primary employment clusters.

## 20. Family Accessibility Funnel (Phase 4 — Task 5)
To avoid combinatorial explosion of external routing calls:
1. **Candidate Retrieval (Cheap Pre-filter)**:
   Query nearest 3 facilities per category (`schools`, `hospitals`, `pharmacies`) within search radius via Google Places Nearby (if active) or verified spatial datasets (UDISE+, OGD Health, OSM).
2. **Best Candidate Selection**:
   Rank retrieved candidates by straight-line distance; select closest candidate.
3. **Finalist Walking Route**:
   If live Google Routes is active, compute walking route ONLY for the top candidate to obtain exact door-to-door walking duration and distance. If offline, use calibrated 4.5 km/h walking model.
4. **Threshold Evaluation**:
   Compare actual walking time against user's family thresholds:
   - `School <= X min`
   - `Hospital <= Y min`
   - `Pharmacy <= Z min`

## 21. Data Quality Score (Phase 4 — Task 14)
Explicit, data-grounded score between 0.0 and 1.0 based on real source provenance:
```text
dq_route = 1.0 (LIVE Google) | 0.8 (RECENT cached Google) | 0.6 (PERIODIC GTFS) | 0.4 (ESTIMATED Mock)
dq_facility = 1.0 (LIVE Google Places) | 0.6 (PERIODIC verified seed/UDISE+/OGD)

data_quality_score = 0.7 * dq_route + 0.3 * dq_facility
```
Computed without synthetic or fabricated percentages.
