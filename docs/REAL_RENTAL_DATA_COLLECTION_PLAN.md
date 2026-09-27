# RIVO — Real Rental Data Collection Plan
## How to Legitimately Accumulate Chennai Rental Observations

**Phase 11 | Team CLAIRES | ST1010 | PS-11-S3 | Chennai Pilot**

---

## Context

RIVO's rent intelligence pipeline (Phase 9) is built and tested.
The ML model remains correctly gated at `NOT_READY_INSUFFICIENT_DATA`
because the repository contains **0 real observations**.

The model requires:

| Gate | Threshold |
|---|---|
| Real observations | ≥ 50 |
| Unique properties | ≥ 30 |
| Unique localities | ≥ 5 |
| BHK classes | ≥ 3 (e.g. 1BHK, 2BHK, 3BHK) |
| Independent sources | ≥ 2 |
| Temporal span | ≥ 7 days |
| Synthetic ratio | ≤ 10% |

**Until all gates pass, RIVO says: "Market range unavailable."**
This is correct and honest behavior. Do not lower the thresholds.

---

## What Is a Legitimate Observation?

A legitimate observation is a **verified price for a specific real
property at a specific real moment in time**, from a source that:

1. Is legally permitted to share the information, OR
2. Is publicly observable (rent boards, advertised listings), OR
3. Has explicitly given consent.

Every observation MUST have:

| Field | Requirement |
|---|---|
| `listing_id` | Non-identifying property reference |
| `locality` | Real Chennai locality name |
| `bhk` | Integer 0–10 |
| `rent_monthly` | INR, > 0, ≤ 10,00,000 |
| `observed_at` | ISO-8601 timestamp with timezone |
| `source` | Named collection channel |
| `availability_status` | AVAILABLE / PENDING_CONFIRMATION / RECENTLY_SEEN / UNAVAILABLE |

---

## Allowed Collection Channels

### Channel 1 — RIVO Direct Owner/Agent Submissions

Owners or verified letting agents submit listings directly through
the RIVO Direct form or API.

**Endpoint:** `POST /api/v1/rentals/direct`
**Freshness:** LIVE
**Verification:** OWNER_ATTESTED (not RIVO_VERIFIED by default)
**Source label:** `rivo_direct`

Required: `consent_to_publish: true`

This is the cleanest and most scalable channel.
Every submission is automatically recorded as an observation.

---

### Channel 2 — Authorized Partner Feeds

Rental portals or data providers that have agreed in writing to
share data with RIVO under a licensing or data-sharing agreement.

**Status:** Architecture exists (`AuthorizedPartnerRentalProvider`);
no partner agreement is active at Phase 11.

**Source labels:** Partner name (e.g. `nobrokerage_api_2025-09`)
**Requirements:** Written data sharing agreement, machine-readable feed

Do NOT build fake partner APIs. Do NOT scrape portal websites.

---

### Channel 3 — Permitted Open Datasets

Publicly accessible datasets published under open licenses
(CC-BY, OGL, ODbL) that include Chennai rental price information.

**Examples:**
- Tamil Nadu property registration data (historical deed values)
- GCC open data portal housing surveys
- Academic housing surveys published with open licenses

**Source labels:** Dataset name + vintage (e.g. `tn_property_registry_2024q4`)
**Verification:** UNVERIFIED until cross-referenced

Every record must preserve the original data licence reference.

---

### Channel 4 — Field Observations (Field Agents)

RIVO team members physically visit localities and record:
- Rent boards / "To Let" boards
- Confirmed prices from watchmen / caretakers
- Owner/tenant telephone interviews with consent

**Endpoint:** `POST /api/v1/rentals/admin/collect`
**Freshness:** LIVE
**Source labels:** `field_agent`, `field_survey`, `owner_interview`, `tenant_interview`
**Verification:** UNVERIFIED → LOCATION_VERIFIED (when coordinate confirmed)

Use the template at `data/templates/rivo_rental_observation_template.csv`
for structured field collection.

---

## Prohibited Channels

| Channel | Reason |
|---|---|
| Unauthorized web scraping | Violates terms of service; may be illegal |
| Bypassing CAPTCHA / Cloudflare | Technical access control violation |
| Login-required portals without API access | Unauthorized computer access |
| Generating synthetic/plausible rents | Fabrication |
| Converting demo seed data to "real" | Fabrication |
| Copying rental news article figures | Unverifiable; no primary source |

---

## Collection Workflow

```
New observation
      │
      ▼
Validation
  ├─ REJECTED: synthetic, demo, missing source, impossible rent,
  │            out-of-bounds coords, bhk out of range
  ├─ QUESTIONABLE: low geocode confidence, missing coordinates
  └─ VALID: all hard checks pass
      │
      ▼
Quality Check
  ├─ Verify source is named and genuine
  ├─ Verify observed_at is real (not invented)
  └─ Verify rent is plausible for locality + BHK
      │
      ▼
Deduplication
  ├─ Same listing_id + same day + same rent → duplicate snapshot → skip
  └─ New rent or new availability for same listing_id → new observation → keep
      │
      ▼
Approve
  └─ eligible_for_model=True if not synthetic, not demo, rent > 0
      │
      ▼
Publish (stored in observation_service)
      │
      ▼
Eligibility Count Updated
  └─ GET /api/v1/rentals/admin/data-quality shows new totals
```

---

## Suggested 3-Week Collection Sprint

| Week | Target | Method | Source labels |
|---|---|---|---|
| 1 | 15 obs, 3 localities | Field survey: Velachery, Adyar, T. Nagar | `field_agent` |
| 2 | 20 obs, +2 localities | Owner interviews: Mylapore, Anna Nagar | `owner_interview` |
| 3 | 15+ obs, verify all 50 | RIVO Direct submissions + re-check prices | `rivo_direct` |

After Week 3 with ≥50 eligible observations:

```bash
python -m scripts.train_rent_model
```

The eligibility gate will confirm readiness before any training begins.

---

## Monitoring Progress

```bash
# Check current gate status:
GET /api/v1/rentals/admin/data-quality

# Check real market statistics (only when ≥5 real obs):
GET /api/v1/rentals/real-market-summary

# Import field survey CSV:
python -m scripts.import_rental_observations data/field_survey.csv --dry-run
python -m scripts.import_rental_observations data/field_survey.csv --report
```

---

## Privacy Rules

- Do NOT store owner/tenant names, phone numbers, or national IDs.
- `listing_id` must be a non-identifying code (e.g. `FIELD-VEL-001`).
- `notes` field is internal-only and not published to the UI.
- Consent to publish is required for RIVO Direct listings.
- Field observations must be based on publicly observable facts.

---

*Team CLAIRES | Phase 11 | Chennai Pilot | 2026-09-27*
