# RIVO — PHASE 9 RENT INTELLIGENCE REPORT
## Data Sufficiency Audit, Hierarchical Baseline, & Quantile Rent Surface
**Team CLAIRES | ST1010 | PS-11-S3 | Chennai Pilot**  
**Date**: September 27, 2026  
**Status**: COMPLETE (Safeguards: ENFORCED | Pipeline: READY | Production ML: GATED BY DATA SUFFICIENCY)

---

## 1. Executive Summary

Phase 9 establishes the **Rent Intelligence Layer** for RIVO in Chennai. The core engineering principle of this phase is:

> **RIVO never trains an ML model on synthetic station-anchored fixtures or fake observations. A truthful "Insufficient real rental data" is strictly preferred over statistically meaningless rent predictions.**

Rather than fabricating 1,000 synthetic rows to artificially force a model training cycle, Phase 9:
1. **Audited Data Sufficiency**: Evaluated the repository's real vs. demo inventory against deterministic engineering safeguards.
2. **Built Hierarchical Baseline Benchmark**: Implemented an empirical hierarchical median model (`H3 Cell -> Locality -> Citywide BHK -> Global Median`) with MAE, RMSE, and MedAE metrics.
3. **Engineered Deterministic Transit Features**: Integrated local CMRL and MTC GTFS stops to compute `nearest_metro_distance_m`, `nearest_bus_stop_distance_m`, and `transit_accessibility_index` without external API calls.
4. **Constructed LightGBM Quantile ML Architecture**: Built a multi-quantile regressor ($\alpha=0.25, 0.50, 0.75$) with strict temporal train/validation splitting, safe promotion rules, and monotonic interval guarantees ($p25 \le p50 \le p75$).
5. **Gated Production Training**: Implemented `python -m backend.scripts.train_rent_model` which evaluates the eligibility safeguards and safely blocks ML training until genuine observations accumulate.
6. **Integrated RIVO Home & Market Positioning**: Added Asking Rent vs Expected Market Range (`Within estimated market range`, `Above RIVO estimated market range`, `Market range unavailable`) clearly separated from Affordability housing burden, and truthfully marked historical trends unavailable.

---

## 2. Rental Data Inventory & Audit Result

| Metric | Count | Provenance / Classification |
|---|---|---|
| **Total Listings Ingested** | 88 | Seed / Sample Data |
| **Live Listings** | 0 | First-party direct provider (prior to user submissions) |
| **Recent Listings (Cache)** | 0 | Cached within TTL |
| **Periodic Listings** | 88 | CMRL metro-anchored sample listings |
| **Demo / Seed Listings** | 88 | `eligible_for_model = False` (Internal sample) |
| **Unique Real Properties** | 0 | Excludes synthetic fixtures |
| **Unique Real Localities** | 0 | Excludes synthetic fixtures |
| **Unique Real BHK Classes** | 0 | Excludes synthetic fixtures |
| **Observed Real Rent Records** | 0 | Database `rental_observations` table |

---

## 3. Model Eligibility Gate & Engineering Safeguards

RIVO enforces deterministic safeguards in [`backend/app/services/ml/eligibility.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/ml/eligibility.py) before permitting any statistical ML model training:

```text
Threshold Safeguards:
  1. MIN_REAL_OBSERVATIONS = 50   (Current: 0  -> FAIL)
  2. MIN_UNIQUE_PROPERTIES = 30   (Current: 0  -> FAIL)
  3. MIN_LOCALITIES        = 5    (Current: 0  -> FAIL)
  4. MIN_BHK_CLASSES       = 3    (Current: 0  -> FAIL)
  5. MIN_SOURCE_COUNT      = 2    (Current: 0  -> FAIL)
  6. MAX_SYNTHETIC_RATIO   = 10%  (Current: 100% -> FAIL)
  7. MIN_TEMPORAL_SPAN     = 7d   (Current: 0d -> FAIL)
```

- **Eligibility Status**: `NOT_READY_INSUFFICIENT_DATA`
- **Model Eligible**: `False`
- **Safeguard Message**: *"Insufficient real rental observations for ML training. Model training blocked."*

---

## 4. Pipeline Architecture & Feature Engineering

### 4.1 Feature Set
The feature vector extracted by [`TransitFeatureExtractor`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/ml/features.py) grounds predictions in physical housing attributes and transit proximity:
1. `bhk`: Number of bedrooms (normalized integer).
2. `area_sqft`: Usable carpet area (sqft).
3. `locality`: Categorical encoded locality.
4. `furnishing`: Categorical encoded furnishing level (`unfurnished`, `semi-furnished`, `fully-furnished`).
5. `property_type`: Categorical encoded property type (`flat`, `independent_house`, etc.).
6. `latitude`, `longitude`: WGS-84 coordinates.
7. `nearest_metro_distance_m`: Haversine distance to nearest CMRL Metro station (from local GTFS).
8. `nearest_bus_stop_distance_m`: Haversine distance to nearest MTC bus stop (from local GTFS).
9. `transit_accessibility_index`: Composite accessibility score $[0.0, 1.0]$.
10. `h3_index`: Resolution 8 spatial index for regional smoothing.

### 4.2 Quantile Methodology (p25, p50, p75)
Rather than multiplying predictions by arbitrary fixed percentages (e.g. $\pm 15\%$), RIVO trains separate LightGBM quantile regression models:
- $\alpha = 0.25$ for 25th percentile (lower quartile)
- $\alpha = 0.50$ for 50th percentile (median)
- $\alpha = 0.75$ for 75th percentile (upper quartile)

If sample size is sparse, the hierarchical baseline uses empirical group quantiles with a monotonic ordering guard ($p25 \le p50 \le p75$).

### 4.3 Spatial Rent Surface & H3 Smoothing
[`RentSurfaceService`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/app/services/ml/rent_surface.py) computes hexagonal rent cells (resolution 8). For sparse cells, it executes multi-tier hierarchical smoothing:
$$\text{Target Cell} \longrightarrow \text{Neighboring Cells (k-ring 1)} \longrightarrow \text{Locality Fallback} \longrightarrow \text{Citywide Baseline}$$
Every fallback step reduces the reported confidence level (`HIGH` $\to$ `MEDIUM` $\to$ `LOW` $\to$ `INSUFFICIENT_DATA`).

---

## 5. RIVO Home Integration & Decoupled Dimensions

### 5.1 Affordability vs. Market Position
In compliance with Task 16 & 17, RIVO keeps **Affordability** strictly decoupled from **Market Position**:
- **Affordability (Personal Feasibility)**:
  - Housing Burden: $\text{Rent} / \text{Income} = 28.5\%$
  - Transport Burden: $\text{Transit Cost} / \text{Income} = 5.2\%$
  - Combined H+T Burden: $33.7\%$
- **Market Position (Market Valuation)**:
  - Asking Rent: ₹18,000
  - Estimated Market Range: ₹15,500 – ₹17,500
  - Position: *"Above RIVO estimated market range"* (or *"Within estimated market range"*)
  - Confidence: `LOW` / `MEDIUM` / `INSUFFICIENT_DATA`
  - Model Version: `MODELLED • baseline_v1`

### 5.2 Historical Affordability Status (Task 24)
When historical depth is unavailable, the modal and API truthfully report:
> *"Historical trend unavailable for this locality (RIVO refuses to fabricate historical snapshots)."*

---

## 6. Verification & Test Suite

```bash
backend/.venv/Scripts/pytest backend/tests -v
```

- **Full Suite**: **126 passed**, **8 skipped** in 7.49s (0 external live calls).
- **Phase 9 Test Coverage** ([`test_phase9_rent_intelligence.py`](file:///c:/Project/Hackathons/Sustain-a-thon/Code/backend/tests/unit/test_phase9_rent_intelligence.py)):
  1. `test_demo_observations_fail_eligibility`: Blocks 88 demo records from training.
  2. `test_eligible_dataset_passes_safeguards`: Verified with a 60-observation real fixture.
  3. `test_demo_and_corrupt_records_are_dropped`: Drops corrupt rents and out-of-bounds coordinates.
  4. `test_gtfs_transit_features`: Validates metro/bus distances and transit index.
  5. `test_baseline_hierarchical_fit_and_predict`: Tests hierarchical median fallbacks and MAE/RMSE calculation.
  6. `test_temporal_split_chronological`: Validates chronological train/val splits.
  7. `test_ml_quantile_training_and_ordering`: Validates LightGBM quantile regression and monotonic $p25 \le p50 \le p75$.
  8. `test_h3_surface_building_and_smoothing`: Tests hexagonal aggregation and k-ring neighbor smoothing.
  9. `test_market_summary_endpoint`: Validates `GET /api/v1/rentals/market-summary` insufficient-data behavior.
  10. `test_market_estimate_endpoint`: Validates `POST /api/v1/rentals/market-estimate`.
- **Frontend Build**: `npm run build` completed cleanly in 678ms with **0 errors**.

---

## 7. Component Status Table

| Component | Status | Evidence |
|---|---|---|
| **Real observations** | 0 (Active production) | Database count (`rental_observations` table) |
| **Demo exclusion** | **PASS** | 88 demo records flagged `eligible_for_model=False` |
| **Baseline Model** | **READY** | Hierarchical median fallback with MAE/RMSE |
| **ML Model (LightGBM)** | **GATED (PIPELINE READY)** | Quantile regression implemented, safely gated by safeguards |
| **P25 Methodology** | **READY** | LightGBM quantile ($\alpha=0.25$) & empirical quantiles |
| **P50 Methodology** | **READY** | LightGBM quantile ($\alpha=0.50$) & empirical medians |
| **P75 Methodology** | **READY** | LightGBM quantile ($\alpha=0.75$) & empirical quantiles |
| **H3 Rent Cells** | **READY** | Resolution 8 spatial cells with k-ring neighbor smoothing |
| **Historical Trends** | **UNAVAILABLE (TRUTHFUL)** | Truthfully marked unavailable without fabrication |
| **RIVO Home Integration** | **READY** | Listing card badge & detail modal market position section |
