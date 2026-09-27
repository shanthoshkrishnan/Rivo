# RIVO — Rental Provider Research & Discovery

**Team CLAIRES | ST1010 | PS-11-S3**  
**Document**: Legitimate Rental Data Provider Analysis  
**Version**: 1.0 (Phase 8)  

---

## 1. Executive Summary & Legal Guardrails

RIVO PS-11-S3 addresses the housing-transit mismatch for Chennai's workforce. To deliver reliable and trustworthy recommendations, RIVO requires real rental inventory.

### Strict Legal & Ethical Ground Rules:
- **No Unauthorized Scraping**: Commercial real estate portals (e.g., Magicbricks, 99acres, NoBroker, Housing.com) explicitly prohibit automated extraction, crawling, and scraping in their Terms of Service.
- **No Circumvention of Controls**: No bypassing of CAPTCHAs, Cloudflare WAF, authentication walls, or robots.txt.
- **No PII Harvesting**: No collection or storage of landlord phone numbers, personal emails, Aadhaar/PAN, tenant names, or identity documents.
- **Truthful Labeling**: A provider is **NOT** marked "AVAILABLE" simply because its website exists. Only verified programmatic feeds with valid API credentials or data-sharing agreements may be activated.

---

## 2. In-Depth Evaluation of Candidate Providers

| Provider / Channel | Official Feed / API? | Chennai Coverage | Commercial / Research Terms | Display to End Users? | Permitted Caching | Attribution Required | Status in RIVO |
|---|---|---|---|---|---|---|---|
| **Magicbricks B2B Affiliate Feed** | Yes (Enterprise B2B REST API) | High (All Chennai zones) | Bilateral commercial contract required | Yes (summaries + canonical link) | Max 7 days | Yes ("Powered by Magicbricks") | **PLANNED PARTNER** (Requires Enterprise Agreement) |
| **99acres Developer API (Info Edge)** | Yes (Restricted partner API) | High (OMR, GST, Central) | Enterprise developer agreement | Yes (with link back) | Max 7 days | Yes | **PLANNED PARTNER** (Requires Partnership Agreement) |
| **NoBroker Partner MLS** | Internal partner endpoints | High (Gated communities & flats) | Commercial agreement | Yes | Max 24 hours | Yes | **PLANNED PARTNER** (Requires Enterprise Agreement) |
| **CREDAI Chennai MLS Feed** | Syndicated XML/JSON | High in newly built transit corridors | Non-profit / civic research MOU | Yes | 14 days | Yes ("CREDAI Chennai") | **RECOMMENDED FOR CIVIC PILOT** |
| **OpenCity.in / GCC Public Housing** | Open Data (CSV/GeoJSON) | Moderate (Slum Board, Municipal) | Permissive CC-BY / OGD India | Yes | Unlimited | Yes ("OpenCity.in / GCC") | **ACTIVE (PERIODIC)** |
| **RIVO Direct Listings (First-Party)** | Yes (Native `POST /api/v1/rentals/direct`) | Growing (direct owner submission) | Full 1st-party ownership & explicit consent | Yes | Permanent (owner controlled) | "RIVO Direct (Owner Verified)" | **ACTIVE (LIVE / FIRST-PARTY)** |
| **Web Scraping without Authorization** | No official API | N/A | **PROHIBITED** by law & ToS | Illegal / Copyright infringement | Prohibited | N/A | **REJECTED** |

---

## 3. Detailed Provider Profiles

### 3.1 CREDAI Chennai (Confederation of Real Estate Developers' Associations of India)
- **Feasibility**: High for an urban-governance and public-interest initiative.
- **Feed Format**: Standardized Real Estate Transaction XML/JSON feed.
- **Coverage**: Strong coverage along Metro Phase 1 and Phase 2 expansion corridors (OMR, Porur, Madhavaram, Poonamallee).
- **Licensing**: Available through academic/civic partnership for transit-oriented development research.
- **Data Attributes Included**: Carpet area, RERA registration ID, locality, asking rent, maintenance, parking, building completion date.

### 3.2 GCC Ward Housing Surveys & OpenCity.in
- **Feasibility**: Fully open and immediate.
- **Feed Format**: Periodic tabular CSV / GeoJSON datasets.
- **Coverage**: Municipal staff quarters, urban poor relocation settlements (Perumbakkam, Semmencherry), and informal rental survey points.
- **Licensing**: Open Government Data (OGD) Platform India / Creative Commons Attribution.
- **Data Freshness**: Marked as `PERIODIC` because datasets are updated biannually or quarterly.

### 3.3 RIVO Direct Listing Portal (First-Party)
- **Feasibility**: 100% operational immediately.
- **Mechanism**: Landlords, housing cooperative societies, or institutional employers submit rental availability directly via `POST /api/v1/rentals/direct`.
- **Verification Levels**:
  - `UNVERIFIED`: Self-submitted without coordinate or document check.
  - `LOCATION_VERIFIED`: Coordinates mathematically verified within Chennai GCC boundaries and geocoded against OSM/GCC basemaps.
  - `OWNER_ATTESTED`: Owner confirmed availability and terms.
  - `RIVO_VERIFIED`: Field-inspected or physically verified.

---

## 4. Caching and Attribution Policies

1. **Cache TTL Standards**:
   - `LIVE` partner data: 24 to 72 hours max before mandatory availability ping.
   - `RECENT` cached data: Up to 7 days.
   - `PERIODIC` open data: 90 days.
   - `STALE`: Listings older than TTL become `NEEDS_REFRESH` and degrade to `PERIODIC`.
2. **Attribution & Deep-linking**:
   - Every card displays the source provider: `Rental source: <Provider Name>`.
   - Where permitted by source terms, an external canonical link (`View original listing`) is rendered without scraping or reproducing proprietary imagery.

---

## 5. Architectural Conclusion

RIVO does not pretend to have magical live access to commercial portals that require paid enterprise contracts. Instead, RIVO provides a **multi-tier provider registry**:
1. Placeholders for authorized commercial partner feeds (`status = NOT_CONFIGURED`).
2. An active, fully functional **RIVO Direct Listing Provider** for live first-party owner inventory.
3. Open dataset providers for periodic municipal and survey data.
4. Transparently labelled demo seed data for offline resilience and demonstration.
