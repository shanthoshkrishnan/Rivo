# `data/seed/` — Seed & Fixture Data

This directory contains sample data files for local development and testing.

---

## Files

### `rental_seed.json`

12 sample rental listings for Chennai localities.

**⚠ IMPORTANT: These are NOT real rental listings.**

Every record has a `_note` field: `"SAMPLE DATA — not a real listing"`.

The `MockRentalProvider` reads this file automatically on startup.  
If the file is absent, the provider falls back to its hardcoded fixture.

Localities covered:
- Velachery, Tambaram, Adyar, Medavakkam, Perambur
- Sholinganallur, Porur, Chromepet, Anna Nagar, Avadi
- Pallikaranai, Mogappair

Rent range: ₹6,000 – ₹22,000 per month (realistic for Chennai 2024–25, but not verified).

---

## Rules

1. **Never put real personal data here** (no phone numbers, no names)
2. Label every fixture with `"_note": "SAMPLE DATA"` or equivalent
3. Do not commit licensed rental data to this directory
4. Seed files are for local development only; production uses real providers

---

## Extending seed data

To add more sample listings, append to `rental_seed.json` following the same schema.  
Required fields:
```json
{
  "listing_id": "SEED-XXX",
  "locality_raw": "Locality Name",
  "locality_normalized": "locality_name",
  "latitude": 12.9XXX,
  "longitude": 80.XXXX,
  "rent_monthly": 10000,
  "bhk": 2,
  "property_type": "flat",
  "is_available": true,
  "_note": "SAMPLE DATA — not a real listing"
}
```

All other fields are optional.
