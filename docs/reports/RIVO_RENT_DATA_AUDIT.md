# RIVO — Phase 9 Rental Data Sufficiency Audit
## Empirical Inventory Assessment & Model Eligibility Safeguards
**Team CLAIRES | ST1010 | PS-11-S3 | Chennai Pilot**  
**Date**: September 27, 2026  
**Status**: COMPLETE (Eligibility Gate: `NOT_READY_INSUFFICIENT_DATA`)

---

## 1. Executive Summary

Phase 9 establishes the **Rent Intelligence Layer** for RIVO in Chennai. In strict compliance with the **Non-Negotiable Data Rule**, RIVO does **not** train machine learning models on synthetic station-anchored fixtures or fake observations.

This audit evaluates the database and seed files against deterministic engineering safeguards to determine whether sufficient non-synthetic evidence exists to train an ML model.

---

## 2. Rental Data Inventory

| Metric | Count | Category / Classification |
|---|---|---|
| **Total Listings Available** | 88 | Seed / Sample Data |
| **Live Listings** | 0 | Real-time direct provider (before owner submissions) |
| **Recent Listings (Cache)** | 0 | Within TTL |
| **Periodic Listings** | 88 | CMRL corridor-anchored sample dataset |
| **Demo / Estimated Listings** | 88 | `eligible_for_model = False` |
| **Unique Real Properties** | 0 | Excludes synthetic fixtures |
| **Unique Real Localities** | 0 | Excludes synthetic fixtures |
| **Unique Real BHK Classes** | 0 | Excludes synthetic fixtures |
| **Observed Real Rent Records** | 0 | Database `rental_observations` table |

### Seed Listing Breakdown (Demo / Periodic Anchor Data)
- **Total Seed Listings**: 88 listings
- **BHK Classes**: 1 BHK (44 listings), 2 BHK (44 listings)
- **Localities Represented**: 42 metro station localities across Chennai
- **Property Types**: 100% Flat
- **Furnishing**: Semi-furnished (44), Unfurnished (44)
- **Asking Rent Range**: ₹6,500 to ₹16,000 / month
- **Source**: `RIVO Sample Data` (internal sample anchored to GTFS stops)

---

## 3. Model Eligibility Gate Evaluation

RIVO enforces deterministic engineering safeguards before permitting statistical or ML model training:

```text
Safeguard Rules & Minimum Thresholds:
  1. MIN_REAL_OBSERVATIONS = 50
  2. MIN_UNIQUE_PROPERTIES = 30
  3. MIN_LOCALITIES        = 5
  4. MIN_BHK_CLASSES       = 3 (e.g. 1, 2, 3 BHK)
  5. MIN_SOURCE_COUNT      = 2
  6. MAX_SYNTHETIC_RATIO   = 10%
  7. MIN_TEMPORAL_SPAN     = 7 days
```

### Evaluation Result
- **Eligibility Status**: `NOT_READY_INSUFFICIENT_DATA`
- **Model Eligible**: `False`
- **Safeguard Failures**:
  - `Insufficient real observations: 0 available, minimum required is 50.`
  - `Too few unique properties: 0 available, minimum required is 30.`
  - `Too few localities represented: 0 available, minimum required is 5.`
  - `Too few BHK classes: 0 available, minimum required is 3.`
  - `Insufficient source diversity: 0 sources, minimum required is 2.`
  - `Dataset dominated by synthetic/demo records: 100.0% synthetic, maximum allowed is 10.0%.`

---

## 4. Policy Decision

1. **NO ARTIFICIAL DATA FABRICATION**: RIVO refuses to manufacture 1,000 fake rental rows merely to satisfy an ML loss function.
2. **PIPELINE IS READY, BUT SAFELY GATED**: The entire LightGBM quantile regression pipeline (`RentMLModel`), spatial feature extractor (`TransitFeatureExtractor`), and hierarchical baseline (`RentBaselineModel`) are fully implemented and tested with fixtures, but production model training remains **disabled** until real observations accumulate.
3. **TRUTHFUL REPORTING**: When end-users or planners query rent estimates without sufficient localized empirical observations, RIVO returns:
   - `confidence = "INSUFFICIENT_DATA"`
   - `status = "NOT_READY_INSUFFICIENT_DATA"`
   - `market_position_label = "Market range unavailable"`
