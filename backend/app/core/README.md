# `app/core/` — Application Core

This package contains application-wide configuration and logging setup.
Nothing in this package imports from other RIVO packages — it is a leaf dependency.

---

## Files

### `config.py`

Central settings using **Pydantic-Settings**.

| What it provides | Details |
|---|---|
| `Settings` class | All env vars validated and type-coerced at startup |
| `DataFreshness` enum | `LIVE / RECENT / PERIODIC / ESTIMATED / HISTORICAL / LOW_DATA` |
| `ConfidenceLevel` enum | `HIGH / MEDIUM / LOW` — never raw percentages |
| `RentalProviderName` enum | `mock / open_dataset / licensed / authorized_third_party` |
| `get_settings()` | Cached singleton — import this everywhere |

**Usage:**
```python
from app.core.config import get_settings, DataFreshness

settings = get_settings()
print(settings.RENTAL_PROVIDER)    # → "mock"
print(DataFreshness.LIVE)          # → "LIVE"
```

**Where settings come from (priority order):**
1. Environment variables (highest)
2. `.env` file in the working directory
3. Defaults defined in `Settings`

---

### `logging.py`

Configures **Loguru** as the application-wide logger.

Features:
- Coloured stderr output during development
- Rotating file sink (`logs/rivo_YYYY-MM-DD.log`, 14-day retention, gzip compressed)
- Async-safe (`enqueue=True`)
- Stack traces in non-production environments only

**Usage:**
```python
from app.core.logging import logger

logger.info("Something happened", key="value")
logger.error("Provider failed", provider="google", error=str(exc))
```

**Call once at startup:**
```python
from app.core.logging import configure_logging
configure_logging()   # called in app/main.py lifespan
```

---

## Rules

- Never import database models or services from this package.
- `DataFreshness` and `ConfidenceLevel` enums must be used for **all** freshness/confidence fields — never raw strings or floats.
- `get_settings()` is memoised — call it freely, no performance concern.
