# RIVO Frontend — Worker Housing & Mobility Intelligence

Welcome to the frontend application for **RIVO (Team CLAIRES, ST1010)**, targeting **PS-11-S3: Can the People Who Run the City Afford to Live In It?**

The frontend is a Chennai-first spatial decision and planning platform built with **React 19**, **TypeScript**, **Vite**, **Tailwind CSS v4**, and **Leaflet**.

---

## 🎨 Warm & Minimalist Design System

To ensure a comfortable, human-centric aesthetic suitable for workers, families, and city planners, the interface is deliberately designed with **warm neutrals, terracotta accents, and zero blue backgrounds**.

### Color Palette Tokens
| Token | Hex | Role |
| :--- | :--- | :--- |
| **Canvas Background** | `#FAF8F5` | Soft warm sand base for the entire page |
| **Surface Card** | `#FFFFFF` | Crisp warm white card surfaces |
| **Muted Surface** | `#F5EFEB` | Warm sandstone background for badges & panels |
| **Subtle Border** | `#EBE4DC` | Fine hairline borders preventing visual congestion |
| **Primary Accent** | `#C25E38` | Warm Terracotta for primary actions, active pins, badges |
| **Secondary Accent** | `#D9822B` | Warm Ochre / Amber for highlights |
| **Positive / Passed** | `#3E7353` | Warm Sage Olive for met constraints |
| **Constraint Exceeded** | `#B83A2E` | Warm Brick for trade-offs & warnings |
| **Primary Text** | `#2C2523` | Deep warm charcoal for readable typography |
| **Muted Text** | `#7A6F68` | Warm stone for labels, helper text, and attributions |

### Uncongested Layout Principles
- **Stepped Form Navigation**: Input controls are partitioned into 3 clear steps (`Workplace & Travel` → `Worker & Budget` → `Family Layer`) so the user is never overwhelmed by a dense wall of inputs.
- **Split View**: Left column displays spacious listing cards with real monthly cost breakdowns and explainability bullets; right column hosts the interactive Chennai Leaflet map.
- **Micro-Typography & Pills**: Clear, pill-shaped tags for transit modes, confidence tiers, and data freshness.

---

## 🚀 Core Workflows

### 1. RIVO Home (`Find a Home`)
- **Workplace Destination**: Select from pre-mapped Chennai hubs (Chennai Central, Tidel Park OMR, Guindy Industrial SIDCO, Ambattur OT, Rajiv Gandhi Govt Hospital, Sriperumbudur) or custom coordinates.
- **Worker & Income Profiles**: Select worker occupation (Nurse, School Teacher, MTC Bus Driver, Delivery Rider, Construction Worker). Auto-populates PLFS 2025 monthly earnings and suggested 30% rent ceiling.
- **Family Accessibility Layer**: Configures adult/child count, child age bands (`0-5`, `6-12`, `13-17`), and travel limits to registered schools (UDISE+), hospitals (Chennai Health OGD), and pharmacies (OSM).
- **Results & Real Living Cost**:
  - Displays monthly Rent + Maintenance + Estimated Commute Cost.
  - Multi-modal door-to-door comparison (Metro/Bus, 2-Wheeler, Walk, Car) with badges: *Fastest*, *Cheapest*, *Fewest Transfers*.
  - **"Why RIVO Recommends This"**: Explainable data-driven bullet points (e.g., `✓ within budget`, `✓ commute within limit`, `✓ school within target`).
  - Transparent data freshness and confidence flags (`PERIODIC`, `ESTIMATED`, `HIGH/MEDIUM`).

### 2. RIVO City (`City Planner`)
- **Policy Question**: *Can the People Who Run Chennai Afford to Live In It?*
- **Scenario Simulator**:
  - Compares the **Current Chennai Network** against **Proposed Interventions** (such as CMRL Phase II Corridor 4 or GCC Outer Ring Road Affordable Housing Enclaves).
  - Evaluates deltas in **45-Min Worker Reach**, **Affordable Listing Count**, and **Median Commute Minutes Saved**.
  - Summarizes spatial takeaways for urban planners.

### 3. Data Transparency & Provenance Registry
- Surfaces all 11 authoritative datasets used by RIVO:
  - GCC 2025 GIS (city boundary)
  - CUMTA GTFS (Chennai transit feeds)
  - PLFS 2025 (Periodic Labour Force Survey income data)
  - Chennai Health Infrastructure OGD (hospitals)
  - UDISE+ (schools)
  - OpenStreetMap (roads, pharmacies, POIs)
  - WorldPop 2025 (population densities)
  - CMRL Phase II (metro expansion corridors)
  - MTC / CMRL Fares (real official transit pricing)

---

## 📂 Component Structure

```text
frontend/
├── src/
│   ├── types/
│   │   └── api.ts                 # TypeScript schemas matching FastAPI Pydantic models
│   ├── services/
│   │   └── api.ts                 # Typed fetch client connecting to /api/v1 endpoints
│   ├── components/
│   │   ├── Header.tsx             # Warm minimalist top navigation & backend health badge
│   │   ├── RivoHome/
│   │   │   ├── HomeSearchForm.tsx # Stepped workplace, income, and family controls
│   │   │   ├── ListingCard.tsx    # Property card with route pill & explainability
│   │   │   ├── ListingDetailModal.tsx # Full multi-mode travel & H+T breakdown modal
│   │   │   └── RivoMap.tsx        # Leaflet Chennai map with custom pins & popups
│   │   ├── RivoCity/
│   │   │   └── CityPlanner.tsx    # Scenario evaluation engine (before vs after)
│   │   └── DataSources/
│   │       └── DataSourcesView.tsx # Data provenance and licensing registry
│   ├── App.tsx                    # Root application component
│   └── index.css                  # Tailwind v4 setup and warm color variables
├── index.html                     # Plus Jakarta Sans & Leaflet CSS includes
├── vite.config.ts                 # Tailwind plugin and /api proxy to localhost:8000
└── package.json
```

---

## 🛠️ Running Locally

1. **Ensure Backend is running**:
   ```bash
   cd ../backend
   source .venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start Frontend Dev Server**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) in your browser.

3. **Production Build**:
   ```bash
   npm run build
   ```
