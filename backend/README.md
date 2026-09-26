# RIVO Backend

> Chennai-first housing + mobility intelligence platform — backend API.
> Team CLAIRES (ST1010) · PS-11-S3 "Can the People Who Run the City Afford to Live In It?"

---

## What this is

The RIVO backend is a **FastAPI** application that powers two product modes:

| Mode | What it does |
|---|---|
| **RIVO Home** | Finds currently available rental homes that fit income, household, transport and family needs |
| **RIVO City** | Lets planners study worker affordability and compare housing/transit scenarios |

---

## Quick start (without a database)

The application runs in **mock mode** by default — no PostgreSQL, Redis or external APIs required.

```bash
cd backend

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env

# 4. Start the API
uvicorn app.main:app --reload --port 8000
```

Visit:
- **API root** → http://localhost:8000/
- **Swagger docs** → http://localhost:8000/docs
- **Health check** → http://localhost:8000/health

---

## Full stack (with PostgreSQL + Redis)

```bash
# Start PostgreSQL + PostGIS + Redis
docker compose up -d

# Run database migrations
alembic upgrade head

# Seed reference data
python scripts/seed_data.py

# Start backend
uvicorn app.main:app --reload --port 8000
```

---

## Project structure

```
backend/
├── app/
│   ├── api/v1/endpoints/   # FastAPI route handlers
│   ├── core/               # Config, logging
│   ├── db/                 # SQLAlchemy session, Redis cache
│   ├── models/             # ORM models (PostgreSQL + PostGIS)
│   ├── schemas/            # Pydantic request/response schemas
│   ├── scrapers/           # Safe web scrapers (robots.txt + rate-limit)
│   ├── services/
│   │   ├── algorithms/     # Pure-function math (affordability, scoring)
│   │   └── providers/      # Pluggable external service adapters
│   └── utils/              # Spatial helpers (H3, Haversine)
├── alembic/                # Database migrations
├── data/seed/              # Sample data (clearly labelled NOT real)
├── scripts/                # Seed and utility scripts
├── tests/
│   ├── unit/               # Pure function tests (no DB/HTTP)
│   └── integration/        # API endpoint tests with mock providers
├── .env.example            # Environment variable template
├── docker-compose.yml      # PostgreSQL + Redis for local dev
└── requirements.txt        # Python dependencies
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/rentals/search` | Search listings with hard constraints |
| `GET` | `/api/v1/rentals/{id}` | Get single listing |
| `POST` | `/api/v1/routes/compare` | Compare routes for all modes |
| `GET` | `/api/v1/facilities/nearby` | Nearby schools / hospitals / pharmacies |
| `POST` | `/api/v1/recommendations/search` | Full RIVO Home pipeline |
| `GET` | `/api/v1/workers/occupations` | List supported occupations |
| `GET` | `/api/v1/workers/income/{key}` | PLFS income profile |
| `POST` | `/api/v1/scenarios/evaluate` | RIVO City scenario engine |
| `GET` | `/api/v1/data/sources` | Data source registry |
| `GET` | `/health` | Health check |

---

## Running tests

```bash
# Unit tests (no external dependencies)
pytest tests/unit/

# Integration tests (no DB/Redis required — uses mock providers)
pytest tests/integration/

# All tests with coverage
pytest --cov=app tests/
```

---

## Environment variables

See [`.env.example`](.env.example) for all configurable settings.  Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `RENTAL_PROVIDER` | `mock` | `mock` / `open_dataset` / `licensed` |
| `GOOGLE_ROUTES_API_KEY` | _(blank)_ | Leave blank to use OTP + mock routing |
| `OTP_BASE_URL` | `http://localhost:8080/otp` | OpenTripPlanner endpoint |
| `DATABASE_URL` | postgresql+asyncpg://… | Async PostgreSQL URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache URL |

---

## Data freshness labels

Every API response includes a `data_freshness` field:

| Label | Meaning |
|---|---|
| `LIVE` | Returned directly from a live provider right now |
| `RECENT` | From Redis cache within TTL window |
| `PERIODIC` | Batch-refreshed (e.g. daily GTFS, annual PLFS) |
| `ESTIMATED` | Model-derived, not a direct observation |
| `HISTORICAL` | Dataset not regularly updated |
| `LOW_DATA` | Very few observations — low confidence |

**The UI must display this label for every data point.**

---

## Non-negotiable rules

- Never manufacture data.
- Never scrape a site without explicit ToS permission (see `app/scrapers/base.py`).
- Never route more than 200 listings per request.
- Never hide provider failures — surface them via `data_freshness` and error fields.
- Keep hard constraints (rent, BHK, commute) separate from soft preferences.
- Cache expensive routing requests (Redis TTL = 1 hour by default).
