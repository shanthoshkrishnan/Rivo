# RIVO — UI/UX

## Product feel
Clean, modern, trustworthy, map-first.

Avoid:
- generic AI dashboard look
- dense GIS controls
- giant cards
- fake precision
- opaque “AI score”

## Navigation
```text
RIVO
Find a Home
City Planner
```

## RIVO Home
Headline:
> Find a home that fits your life — not just your budget.

Inputs:
- workplace
- household income
- home requirement
- rent budget
- family
- transport
- commute

CTA:
**Find suitable homes**

## Results
Map + property list.

Property card:
```text
₹11,500
2 BHK • 850 sqft

Best route:
Metro + Walk
38 min
₹40 one-way

Monthly:
Rent ₹11,500
Maintenance ₹1,000
Transport ₹1,600

Family:
School 9 min
Hospital 14 min
Pharmacy 4 min

Confidence:
HIGH

WHY RIVO
✓ within budget
✓ commute within limit
✓ school within target
✓ hospital within target
✓ transit match
```

## Route comparison
```text
WALK
52 min
₹0

TRANSIT
38 min
₹40
1 transfer

2-WHEELER
26 min
estimated fuel

DRIVE
31 min
estimated fuel
```

Show badges:
- Fastest
- Cheapest
- Fewest transfers
- Preferred

## Family panel
```text
1 child
School <= 15 min
Hospital <= 20 min
Pharmacy <= 10 min
```

Show:
- nearest facility
- time
- count within threshold

## City Planner
Controls:
- occupation
- income band
- threshold

Map:
- rent
- affordability
- job reach

Scenario:
```text
Current Network
vs
Proposed Network
```

## Explainability
Every recommendation has:
**Why this home?**

Generate text from real factors, not an LLM.

## Freshness
Use:
- LIVE
- UPDATED
- ESTIMATED
- HISTORICAL
- LOW DATA

## Map legend
Green = meets selected constraints
Yellow = trade-off
Red = outside selected constraints
Grey = insufficient data

Do not rely on color alone; add labels/icons.

## Loading
- listing skeletons
- route progress
- facility progress

Never show a blank page while data is loading.
