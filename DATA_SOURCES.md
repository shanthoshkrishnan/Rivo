# RIVO — Chennai Data Sources

## Source registry

| Layer | Source | Role |
|---|---|---|
| City boundary | GCC GIS 2025 | wards/zones/study area |
| Transit | CUMTA GTFS | routes/stops/trips/schedules |
| Roads | OpenStreetMap | walking/street network |
| Income | PLFS 2025 | occupation income distributions |
| Hospitals | Chennai Health Infrastructure OGD | facilities + nurse opportunity |
| Schools | UDISE+ + mapped locations | family facilities + teacher opportunity |
| Pharmacies | OSM; optional permitted Places API | family access |
| Population | WorldPop 2025 | population weighting |
| Metro scenario | CMRL Phase II | proposed-network scenario |
| Bus fares | MTC | commute cost |
| Metro fares | CMRL | commute cost |
| Rentals | licensed/authorized source | current homes |
| Historical rent | openly licensed/historical datasets + market reports | training/calibration |

## Official/current references

GCC GIS:
https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/EDPMobile2025/FeatureServer/layers

CUMTA:
https://opendata.cumta.org/

PLFS 2025:
https://microdata.gov.in/NADA/index.php/catalog/284

Chennai Health Infrastructure:
https://ap.data.gov.in/catalog/health-infrastructure-chennai

CMRL:
https://chennaimetrorail.org/cmrl-profile/

MTC fares:
https://mtcbus.tn.gov.in/Home/fares

CMRL fare calculator:
https://chennaimetrorail.org/fare-calculator/

WorldPop:
https://hub.worldpop.org/geodata/summary?id=73807

OpenTripPlanner:
https://github.com/opentripplanner/OpenTripPlanner

Google Routes:
https://developers.google.com/maps/documentation/routes/

Google Places (New):
https://developers.google.com/maps/documentation/places/web-service/nearby-search

## Rental data policy
Do not create a direct scraper unless the source terms/permission permit it.

Implement:
- MockRentalProvider
- OpenDatasetRentalProvider
- LicensedRentalProvider
- AuthorizedThirdPartyRentalProvider

This keeps the app independent of a single portal.

## Rental fields
```text
listing_id
provider
observed_at
first_seen_at
last_seen_at
city
locality_raw
locality_normalized
address_raw
latitude
longitude
geocode_confidence
rent_monthly
maintenance_monthly
deposit
brokerage
property_type
bhk
bedrooms
area_sqft
furnishing
bathrooms
tenant_preference
availability
url_hash
duplicate_cluster_id
model_rent_p25
model_rent_p50
model_rent_p75
data_confidence
```

## Income
Use PLFS occupation codes and earnings to construct:
```text
income_p25
income_median
income_p75
sample_size
confidence
```

If Chennai is statistically too sparse:
Chennai -> Tamil Nadu urban -> India urban
and lower confidence accordingly.

## Workplace
Do not claim exact employee counts unless a source provides them.

Use:
```text
workplace_id
category
subcategory
latitude
longitude
estimated_jobs
jobs_lower
jobs_upper
confidence
source
```

## Transit
Minimum GTFS:
- stops
- routes
- trips
- stop_times
- calendar
- calendar_dates
- shapes

Optional:
- transfers
- frequencies
- fares
- pathways

## Route result
```text
origin
destination
mode
departure_time
provider
distance_m
duration_seconds
walk_seconds
wait_seconds
in_vehicle_seconds
transfer_count
fare_amount
route_geometry
observed_at
```

## Freshness
UI labels should include:
- LIVE
- RECENT
- PERIODIC
- ESTIMATED
- HISTORICAL
- LOW CONFIDENCE
