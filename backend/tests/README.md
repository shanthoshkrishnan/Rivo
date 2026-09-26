# `tests/` — Test Suite

Two test categories, each runnable independently:

```
tests/
├── unit/              # Pure function tests — no DB, no HTTP, no Redis
│   ├── test_affordability.py
│   └── test_normalization.py
└── integration/       # API endpoint tests — mock providers only
    └── test_api_endpoints.py
```

---

## Running tests

```bash
cd backend

# Unit tests only (fast, no dependencies)
pytest tests/unit/ -v

# Integration tests (mock providers — no external services needed)
pytest tests/integration/ -v

# All tests with coverage report
pytest --cov=app --cov-report=term-missing tests/

# Run a specific test
pytest tests/unit/test_affordability.py::TestHardConstraints::test_rent_exceeds_budget -v
```

---

## `tests/unit/test_affordability.py`

Tests all pure functions in `app/services/algorithms/affordability.py`:

| Test class | What it covers |
|---|---|
| `TestAffordability` | §5 housing/transport/cash burden, §6 time tax |
| `TestTransitCost` | §9 monthly commute cost calculation |
| `TestFacilityFit` | §11 binary facility access |
| `TestHardConstraints` | §16 all hard constraint rejection cases |
| `TestScoring` | §15 individual component scores and weighted total |
| `TestConfidence` | §18 HIGH/MEDIUM/LOW confidence level |
| `TestExplainability` | Positive and negative reason generation |

---

## `tests/unit/test_normalization.py`

Tests `app/services/algorithms/normalization.py`:

| Test class | What it covers |
|---|---|
| `TestNormalization` | Furnishing, BHK, area, rent, locality, property type, URL hash |
| `TestDeduplication` | Same provider ID, URL hash, coordinate proximity |

---

## `tests/integration/test_api_endpoints.py`

Tests the full HTTP API using `httpx.AsyncClient` with `ASGITransport`.

No database, Redis, or external APIs are needed — all providers use mock mode.

| Test class | Endpoints tested |
|---|---|
| `TestHealthEndpoint` | `GET /health` |
| `TestRentalsEndpoint` | `GET /api/v1/rentals/search`, `GET /api/v1/rentals/{id}` |
| `TestRoutesEndpoint` | `POST /api/v1/routes/compare` |
| `TestWorkersEndpoint` | `GET /api/v1/workers/occupations`, `GET /api/v1/workers/income/{key}` |
| `TestDataSourcesEndpoint` | `GET /api/v1/data/sources` |
| `TestScenariosEndpoint` | `POST /api/v1/scenarios/evaluate` |

Key invariants verified:
- Hard rent constraint: no returned listing exceeds `max_rent_monthly`
- Hard BHK constraint: all returned listings match `bhk` if specified
- Every route result has `data_freshness`
- Every occupation has an income profile
- Data sources include attribution and freshness

---

## Test configuration

`pytest.ini` settings:
- `asyncio_mode = auto` — all async test functions run automatically
- `filterwarnings = error::DeprecationWarning` — deprecation warnings fail the test

---

## What is NOT tested here

- PostGIS spatial queries (requires live DB) — add to a future `tests/db/` suite
- OTP and Google route providers (require external services) — test with VCR cassettes or mocks
- ML rent model training — test in `scripts/` with a dataset fixture
