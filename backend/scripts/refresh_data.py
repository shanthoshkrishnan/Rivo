#!/usr/bin/env python
"""
RIVO — Data Pipeline Refresh CLI (Task 8)
=========================================
Runs the data refresh workflow:
  python -m scripts.refresh_data
"""
import asyncio
import json
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.data_refresh_service import DataRefreshService


async def main() -> int:
    print("=" * 60)
    print("  RIVO DATA PIPELINE REFRESH (Task 8)")
    print("=" * 60)

    service = DataRefreshService(db=None)
    result = await service.refresh_all()

    print("\nResult:")
    print(json.dumps(result, indent=2))
    print("=" * 60)

    if result.get("status") in ("success", "partial_success"):
        print("Refresh completed successfully.")
        return 0
    else:
        print("Refresh failed.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
