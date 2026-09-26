# `app/services/providers/` — Provider Adapters

This package implements the **Provider Architecture** defined in `AGENTS.md`.

All providers are pluggable — the rest of the application depends only on the abstract base classes in `base.py`, never on a specific implementation.

---

## Architecture

```
base.py              ← Abstract interfaces (contracts)
    RentalProvider
    RouteProvider
    PlacesProvider
    FacilityProvider
    FuelPriceProvider

rental_mock.py       ← Mock rental provider (always works, sample data)
route_mock.py        ← Mock route provider (Haversine estimates)
route_google.py      ← Google Routes API v2 provider
route_otp.py         ← OpenTripPlanner 2.10 GraphQL provider
registry.py          ← Factory + CompositeRouteProvider (fallback chain)
```

---

## Provider selection

### Rental

Set via `RENTAL_PROVIDER` env var:

| Value | Provider | Notes |
|---|---|---|
| `mock` | `MockRentalProvider` | Always works; sample data; **default** |
| `open_dataset` | `OpenDatasetRentalProvider` | From openly licensed dataset file |
| `licensed` | `LicensedRentalProvider` | Requires `LICENSED_RENTAL_API_KEY` |

If the configured provider is unavailable, falls back to mock.

### Routing (CompositeRouteProvider)

Priority chain:
1. **Google Routes API** — if `GOOGLE_ROUTES_API_KEY` is set
2. **OpenTripPlanner** — open/reproducible; requires local OTP instance
3. **Mock** — always available; ESTIMATED freshness

The chain is tried in order. Each failure is logged. The first success wins.

---

## `base.py` — Abstract interfaces

### `RentalProvider`

```python
class RentalProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def search(self, params: RentalSearchParams) -> List[RentalListingCreate]: ...

    @abstractmethod
    async def get_listing(self, listing_id: str) -> Optional[RentalListingCreate]: ...

    @abstractmethod
    def is_available(self) -> bool: ...
```

**Rule**: Implementations MUST apply hard constraints (rent, BHK, type) before returning. Never return unavailable listings.

### `RouteProvider`

```python
class RouteProvider(ABC):
    @abstractmethod
    async def compute_route(self, request: RouteRequest) -> List[RouteResult]: ...

    @abstractmethod
    def supports_mode(self, mode: str) -> bool: ...
```

**Rule**: Never call this for more than ~200 listings per request.

---

## `rental_mock.py` — MockRentalProvider

- Returns sample Chennai listings from `data/seed/rental_seed.json` (or hardcoded fixture if file absent)
- Every listing tagged `data_freshness=PERIODIC`, `source_name="RIVO Sample Data"`
- Hard filters (rent, BHK, property_type, availability) applied before returning
- **⚠ Must display "SAMPLE DATA" warning in UI**

---

## `route_mock.py` — MockRouteProvider

- Uses Haversine (straight-line × route factor) + mode-specific speed/fare parameters
- Chennai-calibrated defaults: walk 4.5 km/h, transit 22 km/h, two-wheeler 28 km/h, drive 22 km/h
- Computes fuel cost using petrol price from settings
- Assigns `is_fastest`, `is_cheapest`, `is_fewest_transfers` badges
- All results tagged `data_freshness=ESTIMATED`

---

## `route_google.py` — GoogleRouteProvider

- Calls Google Routes API v2 (`/directions/v2:computeRoutes`)
- **Caches** every result in Redis before returning (TTL = `ROUTE_CACHE_TTL`)
- Rounds departure time to 30-minute buckets to maximise cache hit rate
- 3 retries with exponential backoff on HTTP errors
- Raises `ProviderUnavailableError` on failure → triggers OTP or mock fallback
- **ToS compliance**: cached results respect TTL; no offline map rendering

---

## `route_otp.py` — OTPRouteProvider

- Calls OpenTripPlanner 2.10 GraphQL endpoint (`/routers/default/index/graphql`)
- Requires OTP running with CUMTA GTFS + OSM road network loaded
- Same Redis cache strategy as GoogleRouteProvider
- Returns partial results on per-mode errors (does not abort the whole request)

---

## `registry.py` — Factory functions

```python
# Get configured rental provider (singleton)
from app.services.providers.registry import get_rental_provider
provider = get_rental_provider()

# Get composite route provider (Google → OTP → Mock)
from app.services.providers.registry import get_route_provider
route = get_route_provider()
```

---

## Adding a new provider

1. Create `rental_my_provider.py` (or `route_my_provider.py`)
2. Subclass `RentalProvider` (or `RouteProvider`) from `base.py`
3. Implement all abstract methods
4. Add to `registry.py` factory
5. Add new enum value to `RentalProviderName` in `config.py`
6. Write unit tests verifying hard constraints and freshness labels
