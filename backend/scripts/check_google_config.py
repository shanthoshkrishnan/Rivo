"""
RIVO — Safe Environment Diagnostic
Outputs configuration status without exposing secrets.
"""
from pathlib import Path
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Check detected .env files
repo_root = backend_dir.parent
detected_env_files = []
for p in [backend_dir / ".env", repo_root / ".env"]:
    if p.exists():
        detected_env_files.append(str(p))

# Read direct from backend/.env manually for comparison
backend_env_path = backend_dir / ".env"
routes_in_file = False
places_in_file = False
routes_file_len = 0
places_file_len = 0

if backend_env_path.exists():
    with open(backend_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'").strip('"')
            if k == "GOOGLE_ROUTES_API_KEY":
                routes_in_file = bool(v)
                routes_file_len = len(v)
            elif k == "GOOGLE_PLACES_API_KEY":
                places_in_file = bool(v)
                places_file_len = len(v)

from app.core.config import get_settings

settings = get_settings()

routes_configured = bool(settings.GOOGLE_ROUTES_API_KEY.strip()) if settings.GOOGLE_ROUTES_API_KEY else False
places_configured = bool(settings.GOOGLE_PLACES_API_KEY.strip()) if settings.GOOGLE_PLACES_API_KEY else False

print("RIVO GOOGLE CONFIGURATION")
print("=========================")
print("")
print(f"Backend working directory:\n{os.getcwd()}")
print("")
print(f"Settings source:\n{backend_env_path if backend_env_path.exists() else 'defaults'}")
print("")
print(f"Google Routes:\n{'CONFIGURED' if routes_configured else 'NOT CONFIGURED'}")
print(f"configured={routes_configured}")
print(f"length={'0' if not routes_configured else f'{len(settings.GOOGLE_ROUTES_API_KEY)} (REDACTED KEY)'}")
print("")
print(f"Google Places:\n{'CONFIGURED' if places_configured else 'NOT CONFIGURED'}")
print(f"configured={places_configured}")
print(f"length={'0' if not places_configured else f'{len(settings.GOOGLE_PLACES_API_KEY)} (REDACTED KEY)'}")
print("")
print("Detected .env files:")
for f_path in detected_env_files:
    print(f_path)
if not detected_env_files:
    print("None")
print("")
print(f"Active environment:\n{settings.APP_ENV}")
print("")
print(f"Live API Mode (RIVO_LIVE_API_TESTS):\n{'ENABLED (true)' if settings.RIVO_LIVE_API_TESTS else 'DISABLED (false) — Quota Guard Active'}")
print(f"Budgets: Routes={settings.ROUTE_SEARCH_BUDGET}, Places={settings.PLACES_SEARCH_BUDGET}, DetailRoutes={settings.DETAILED_ROUTE_BUDGET}, DetailPlaces={settings.FAMILY_ROUTE_BUDGET}")
print("")
if routes_in_file and not routes_configured:
    print("DIAGNOSTIC NOTICE: GOOGLE_ROUTES_API_KEY is present in backend/.env file (length={}) but not loaded by Settings!".format(routes_file_len))
if places_in_file and not places_configured:
    print("DIAGNOSTIC NOTICE: GOOGLE_PLACES_API_KEY is present in backend/.env file (length={}) but not loaded by Settings!".format(places_file_len))
if not routes_in_file and not routes_configured:
    print("DIAGNOSTIC NOTICE: GOOGLE_ROUTES_API_KEY is empty in backend/.env file")
if not places_in_file and not places_configured:
    print("DIAGNOSTIC NOTICE: GOOGLE_PLACES_API_KEY is empty in backend/.env file")
