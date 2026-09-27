# RIVO — Field Collection Quickstart
## For use on mobile devices during field collection

**Phase 12 | Team CLAIRES | ST1010 | PS-11-S3**

---

## What qualifies as an observation?

A **real fact** about a **real Chennai property** at a **real moment in time**:

- You personally saw the rent board / spoke to the owner
- An owner/agent directly told you the rent
- A publicly posted advertisement you can verify

**NOT acceptable:**
- Invented or estimated rents
- "Approximate" figures without a source
- Data from websites you had to log in to access

---

## Fields to capture (minimum)

| Field | Example | Notes |
|---|---|---|
| `listing_id` | `FIELD-VEL-001` | Your unique code for this property |
| `locality` | `Velachery` | Standard locality name |
| `bhk` | `2` | Bedrooms |
| `rent_monthly` | `18000` | Monthly rent in INR |
| `observed_at` | `2026-09-27T10:30:00+05:30` | When you recorded it |
| `source` | `field_agent` or `owner_interview` | How you got the information |
| `availability_status` | `AVAILABLE` | See states below |

---

## How to capture coordinates

**Preferred:** Drop a pin in Google Maps / Apple Maps at the property.
Long-press the map → copy coordinates.

Expected format: `13.0418, 80.2341`
First number = latitude, Second = longitude.

If you can't get exact coordinates, record only the locality and set
`geocode_confidence = LOW`.

Chennai valid range:
- Latitude: 12.75 to 13.35
- Longitude: 80.00 to 80.35

---

## Availability states

| State | When to use |
|---|---|
| `AVAILABLE` | Owner/agent confirmed it's available right now |
| `PENDING_CONFIRMATION` | Seen advertised; not yet confirmed with owner |
| `RECENTLY_SEEN` | Was available 2–4 weeks ago; current status unknown |
| `UNAVAILABLE` | Confirmed it has been taken |
| `UNKNOWN` | No information on current availability |

**Never mark `RECENTLY_SEEN` as `AVAILABLE` without a fresh confirmation.**

---

## Verification states

| State | When to use |
|---|---|
| `UNVERIFIED` | Recorded from a board or advertisement |
| `LOCATION_VERIFIED` | You confirmed the property location in person |
| `OWNER_ATTESTED` | Owner or authorized agent confirmed the rent |
| `RIVO_VERIFIED` | RIVO field team has independently verified (reserved for RIVO staff) |

---

## How to avoid duplicates

Use consistent `listing_id` codes. Agree on a naming scheme with your team:

```
FIELD-{LOCALITY_SHORT}-{SEQUENCE}
Examples:
  FIELD-VEL-001  (Velachery, first property)
  FIELD-ADY-001  (Adyar, first property)
  FIELD-TN-001   (T. Nagar, first property)
```

If you visit the same property again with a **new rent or new availability**,
keep the same `listing_id` and record a new observation.
The system will track the history correctly.

---

## How to record source

Use one of these consistent source labels:

| Source | When to use |
|---|---|
| `field_agent` | You observed a rent board without speaking to anyone |
| `owner_interview` | Owner directly confirmed the rent to you |
| `tenant_interview` | Tenant confirmed the rent |
| `building_manager` | Building manager or watchman confirmed |
| `rivo_direct` | Submitted directly through the RIVO Direct form |
| `authorized_partner` | From a licensed data partner API |

Do NOT invent source labels. Stick to this list so source diversity
is counted correctly.

---

## How to upload CSV

1. Fill the template at `data/templates/rivo_rental_observation_template.csv`
2. Save your entries as CSV
3. Run:

```bash
# Preview first:
python -m scripts.import_rental_observations your_survey.csv --dry-run

# Import:
python -m scripts.import_rental_observations your_survey.csv --report
```

---

## How to submit a single observation (API)

```bash
curl -X POST http://localhost:8000/api/v1/rentals/admin/collect \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "FIELD-VEL-001",
    "locality": "Velachery",
    "bhk": 2,
    "rent_monthly": 18000,
    "source": "field_agent",
    "availability_status": "AVAILABLE",
    "latitude": 12.9816,
    "longitude": 80.2180
  }'
```

---

## How to check data readiness

```bash
curl http://localhost:8000/api/v1/rentals/admin/collection-progress
```

Response shows:
```json
{
  "real_observations": 0,
  "unique_properties": 0,
  "localities": [],
  "blocking_reasons": [
    "real_observations: 0 / 50",
    "unique_properties: 0 / 30",
    "localities: 0 / 5",
    "bhk_classes: 0 / 3",
    "source_diversity: 0 / 2",
    "temporal_span_days: 0 / 7"
  ],
  "model_eligibility_status": "NOT_READY_INSUFFICIENT_DATA"
}
```

Keep collecting until `model_ready: true`.

---

## Collection targets

| Locality | Properties needed | BHK mix |
|---|---|---|
| Velachery | 10 | 1BHK, 2BHK, 3BHK |
| Adyar | 10 | 1BHK, 2BHK, 3BHK |
| T. Nagar | 10 | 2BHK, 3BHK |
| Mylapore | 10 | 2BHK, 3BHK |
| Anna Nagar | 10 | 1BHK, 2BHK, 3BHK |
| **Total** | **50** | **≥3 BHK classes** |

Use at least **2 independent sources** (e.g. field_agent + owner_interview).
Spread collection across at least **7 calendar days**.

---

*RIVO Field Collection | Phase 12 | 2026-09-27*
