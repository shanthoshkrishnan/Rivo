# RIVO Demo Rental Inventory — 240 records

This is **synthetic demo inventory** for the Sustainathon prototype.

## Coverage
- 240 unique properties
- 1/2/3/4/5 BHK
- ₹8,000–₹65,000 monthly rent bands
- Apartment, Independent House, Independent Floor
- Unfurnished / Semi-Furnished / Fully Furnished
- Different deposits, maintenance, parking and tenant preferences
- Near/far school, hospital and pharmacy cases
- Near/far bus stop and metro cases
- Short/medium/long commute scenarios
- Family/bachelor/any tenant preference cases
- Gated and non-gated properties
- Pet-friendly and non-pet-friendly cases
- Multiple Chennai localities and price tiers

## Important
All records contain:
- `source=DEMO_SEEDED`
- `verification_state=DEMO`
- `eligible_for_model=false`
- `is_demo=true`

**Do not insert these rows into `rental_observations` and do not use them for ML/rent-market training.**

## Duplicate guarantee
- 240 unique `listing_id`
- 240 unique `property_code`
- 240 unique synthetic addresses
- 240 unique coordinate pairs

The application should also de-duplicate at response time by canonical `listing_id`/property identity before rendering cards.
