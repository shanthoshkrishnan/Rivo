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

## 19. Scenario
Transit scenario:
```text
current network
+
proposed stops/routes
=
scenario network
```

Then recompute accessibility.

Housing scenario:
```text
new site
+
units
+
rent
=
new housing supply
```

Compare:
- worker reach
- commute time
- transport cost
- affordable area
