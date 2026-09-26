#!/usr/bin/env python3
"""
Generate realistic rental listings anchored around real CMRL metro stations
from the downloaded GTFS stops feed (data/seed/gtfs/cmrl-gtfs/stops.txt).
"""
import csv
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STOPS_FILE = BASE_DIR.parent / "data" / "seed" / "gtfs" / "cmrl-gtfs" / "stops.txt"
OUTPUT_FILE = BASE_DIR / "data" / "seed" / "rental_seed.json"

# Locality rent tiers in Chennai (INR for 2 BHK)
RENT_TIERS = {
    "Central": 16000,
    "South": 14000,
    "North": 9000,
    "West": 11000,
    "Edge": 7500,
}

def determine_zone(lat: float, lon: float) -> str:
    if lat > 13.12:
        return "North"
    elif lat < 13.00:
        return "South"
    elif lon < 80.20:
        return "West"
    elif 13.04 <= lat <= 13.10 and 80.24 <= lon <= 80.29:
        return "Central"
    return "South"

def main():
    if not STOPS_FILE.exists():
        print(f"Stops file not found at {STOPS_FILE}")
        return

    listings = []
    with open(STOPS_FILE, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            stop_name = row.get("stop_name", "").strip()
            lat_str = row.get("stop_lat")
            lon_str = row.get("stop_lon")
            if not (stop_name and lat_str and lon_str):
                continue
            base_lat = float(lat_str)
            base_lon = float(lon_str)
            zone = determine_zone(base_lat, base_lon)
            base_rent = RENT_TIERS[zone]

            # Generate 2 realistic properties within walking distance (~200m - 600m) of each metro station
            for unit_idx, (bhk, area, mult) in enumerate([(1, 550, 0.7), (2, 880, 1.0)]):
                # slight coordinate offset (~300m)
                offset_lat = (random.random() - 0.5) * 0.005
                offset_lon = (random.random() - 0.5) * 0.005
                monthly_rent = int(round(base_rent * mult / 500) * 500)
                maint = 500 if bhk == 1 else 900

                listings.append({
                    "listing_id": f"CMRL-{idx+1:03d}-{bhk}BHK",
                    "locality_raw": stop_name,
                    "locality_normalized": stop_name.lower().replace(" ", ""),
                    "latitude": round(base_lat + offset_lat, 6),
                    "longitude": round(base_lon + offset_lon, 6),
                    "rent_monthly": monthly_rent,
                    "maintenance_monthly": maint,
                    "deposit": monthly_rent * 3,
                    "brokerage": monthly_rent,
                    "bhk": bhk,
                    "area_sqft": area,
                    "furnishing": "semi-furnished" if unit_idx == 1 else "unfurnished",
                    "property_type": "flat",
                    "bathrooms": 1 if bhk == 1 else 2,
                    "tenant_preference": "any",
                    "is_available": True,
                    "_anchor_metro_station": stop_name,
                    "_note": "Anchored to real CMRL GTFS transit station"
                })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)

    # Also mirror to data/seed/rental_seed.json
    mirror_file = BASE_DIR.parent / "data" / "seed" / "rental_seed.json"
    with open(mirror_file, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(listings)} rental listings anchored to {len(listings)//2} CMRL stations across Chennai.")

if __name__ == "__main__":
    main()
