# RIVO — Quick Setup Guide

> **Worker Housing & Mobility Intelligence Platform for Chennai**  
> Team CLAIRES (ST1010) — Problem Statement PS-11-S3

---

## ⚡ Quick Start (Under 3 Minutes)

### 1. Prerequisites
- **Python:** 3.11+ (tested on Python 3.11 & 3.12)
- **Node.js:** v18.0.0+ or v20.0.0+ (with `npm`)
- **Git:** 2.30+
- **OS:** Windows, macOS, or Linux

---

## 🛠️ Step-by-Step Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/shanthoshkrishnan/Rivo.git
cd Rivo
```

---

### Step 2: Backend Setup (FastAPI + Python)

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Python dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Backend Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   *(The default `.env` is pre-configured to run out-of-the-box in local GTFS/mock mode without requiring any external paid API keys.)*

5. **Seed the Database:**
   ```bash
   # From the backend directory with active virtual environment:
   python -m scripts.seed_data
   ```
   *This seeds 240 calibrated Chennai demo listings, 5 frontline worker profiles (Nurses, Teachers, Sanitation Workers, Bus Drivers, Delivery Riders), and public transit reference stops into the database.*

6. **Start the Backend Server:**
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   * The API server will be live at: **`http://localhost:8000`**
   * Interactive Swagger Docs: **`http://localhost:8000/docs`**

---

### Step 3: Frontend Setup (React 19 + Vite + Tailwind CSS)

1. **Open a new terminal window and navigate to `frontend`:**
   ```bash
   cd frontend
   ```

2. **Install Node packages:**
   ```bash
   npm install
   ```

3. **Configure Frontend Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   *(Optional)* If you have a CARTO Basemaps API key or Google Maps key, paste it into `frontend/.env`:
   ```ini
   VITE_CARTO_API_KEY=your_carto_basemaps_api_key_here
   VITE_GOOGLE_MAPS_API_KEY=your_google_maps_javascript_api_key_here
   ```
   *Even without custom keys, the application automatically displays clean OpenStreetMap / Voyager tiles with full interactive routing.*

4. **Start the Frontend Dev Server:**
   ```bash
   npm run dev
   ```
   * Open your browser at: **`http://localhost:5173`**

---

## 🔍 Verification & Health Checks

Once both services are running, verify key endpoints:

| Endpoint | Description | Expected Status |
|---|---|---|
| [`GET http://localhost:8000/health`](http://localhost:8000/health) | API health check | `{"status": "healthy"}` |
| [`GET http://localhost:8000/api/v1/data-quality/rentals`](http://localhost:8000/api/v1/data-quality/rentals) | Rental data audit & realism metrics | 240 records, 15 localities, 0 duplicate coords |
| [`GET http://localhost:8000/api/v1/facilities/layers`](http://localhost:8000/api/v1/facilities/layers) | GeoJSON map layers (Schools, Hospitals, Transit) | GeoJSON FeatureCollection |
| [`POST http://localhost:8000/api/v1/recommendations/search`](http://localhost:8000/api/v1/recommendations/search) | Multimodal recommendation search | Filtered, ranked listings with travel breakdown |

---

## 🧭 Key Application Views

1. **RIVO Home (`http://localhost:5173/find`):**
   - Frontline worker housing discovery.
   - Interactive workplace selection (e.g., *Rajiv Gandhi Govt General Hospital, Park Town*).
   - Mode switching: **Transit (MTC/Metro)**, **Two-Wheeler**, **Drive**, or **Walk**.
   - Interactive map with layer toggles for **Homes**, **Workplace**, **Transit Stations**, **Schools**, and **Hospitals**.
   - Real door-to-door commute time, monthly travel expense calculation, and evidence bullets explaining why each property fits.
   - Non-matching properties visible under the "Properties Evaluated But Outside Criteria (Why Not?)" collapsible tray.

2. **RIVO City (`http://localhost:5173/planner`):**
   - Urban planner simulation suite.
   - Test transit interventions (e.g., CMRL Phase 2 Metro extensions) and affordable housing policies.
   - Visualizes demographic catchments, 800m transit walking buffers, and worker affordability shifts.

3. **Data Transparency (`http://localhost:5173/data-sources`):**
   - Full provenance dashboard of all Chennai datasets (GCC GIS, CUMTA GTFS, PLFS 2025, Health OGD, UDISE+).

---

## 🧪 Running Automated Tests

RIVO enforces strict safety rules: normal tests make **0 live external API calls**, protecting your quotas and preventing network flakiness.

```bash
cd backend
# Run full unit and regression test suite
pytest tests/unit/
```

To run the route realism and data quality test suite specifically:
```bash
pytest tests/unit/test_route_and_data_realism.py -v
```

---

## ❓ Troubleshooting

- **Port 8000 or 5173 already in use:**
  - Backend: `python -m uvicorn app.main:app --reload --port 8001` (update `VITE_API_URL` or proxy accordingly)
  - Frontend: Vite will automatically suggest an alternate port (e.g. 5174).
- **Backend module not found:**
  - Ensure your virtual environment is active: `(.venv)` should appear in your terminal prompt.
- **Map tiles showing watermark:**
  - Add a free CARTO Basemaps API key to `frontend/.env` as `VITE_CARTO_API_KEY=...` and restart `npm run dev`.
