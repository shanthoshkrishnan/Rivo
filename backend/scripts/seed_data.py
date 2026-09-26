#!/usr/bin/env python3
"""
RIVO Backend — Seed Data Script
================================
Seeds the database with:
  1. Data source registry (from DATA_LICENSES.md)
  2. Default occupation/income profiles (from PLFS 2025)
  3. Real GTFS transit stops from downloaded Chennai GTFS feeds (CMRL & MTC)

Usage:
    cd backend
    python scripts/seed_data.py

Supports both PostgreSQL (if running) and standalone SQLite (data/rivo.db).
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.session import sync_engine
from app.models.worker import WorkerProfile, IncomeProfile
from app.models.data_source import DataSource
from app.models.routing import TransitStop
from app.core.logging import configure_logging, logger

configure_logging()


def get_target_engine():
    """Returns PostgreSQL sync_engine if available; otherwise falls back to SQLite."""
    try:
        with sync_engine.connect() as conn:
            logger.info("Connected to PostgreSQL database successfully.")
            return sync_engine
    except Exception as exc:
        db_dir = BASE_DIR / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        sqlite_file = db_dir / "rivo.db"
        logger.warning(
            f"PostgreSQL server not detected at localhost:5432 ({str(exc).splitlines()[0]}). "
            f"Using local SQLite database at: {sqlite_file}"
        )
        return create_engine(f"sqlite:///{sqlite_file}", echo=False)


def seed_occupations(session: Session) -> int:
    """Seed worker occupation records."""
    occupations = [
        dict(occupation_key="nurse", occupation_label="Nurse / Healthcare Worker",
             nic_code="Q8610", description="Registered nurses and healthcare support staff"),
        dict(occupation_key="teacher", occupation_label="School Teacher",
             nic_code="P8510", description="Primary, secondary and higher secondary teachers"),
        dict(occupation_key="bus_driver", occupation_label="MTC Bus Driver",
             nic_code="H4931", description="Metropolitan Transport Corporation bus drivers"),
        dict(occupation_key="delivery_rider", occupation_label="Delivery Rider",
             nic_code="H5320", description="Food, parcel and logistics delivery riders"),
        dict(occupation_key="construction_worker", occupation_label="Construction Worker",
             nic_code="F4110", description="Informal and formal construction labourers"),
    ]
    count = 0
    for occ in occupations:
        existing = session.query(WorkerProfile).filter_by(occupation_key=occ["occupation_key"]).first()
        if not existing:
            session.add(WorkerProfile(**occ))
            count += 1
    session.commit()
    return count


def seed_income_profiles(session: Session) -> int:
    """Seed PLFS 2025-based income profiles for Tamil Nadu Urban / Chennai."""
    profiles = [
        dict(occupation_key="nurse", geography_level="tamil_nadu_urban",
             income_p25=18000, income_median=24000, income_p75=35000,
             sample_size=312, confidence="MEDIUM", survey_year=2025,
             source_name="PLFS 2025",
             source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
             data_freshness="PERIODIC"),
        dict(occupation_key="teacher", geography_level="tamil_nadu_urban",
             income_p25=22000, income_median=32000, income_p75=48000,
             sample_size=428, confidence="MEDIUM", survey_year=2025,
             source_name="PLFS 2025",
             source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
             data_freshness="PERIODIC"),
        dict(occupation_key="bus_driver", geography_level="tamil_nadu_urban",
             income_p25=16000, income_median=22000, income_p75=28000,
             sample_size=189, confidence="MEDIUM", survey_year=2025,
             source_name="PLFS 2025",
             source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
             data_freshness="PERIODIC"),
        dict(occupation_key="delivery_rider", geography_level="tamil_nadu_urban",
             income_p25=12000, income_median=18000, income_p75=25000,
             sample_size=267, confidence="LOW", survey_year=2025,
             source_name="PLFS 2025",
             source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
             data_freshness="PERIODIC"),
        dict(occupation_key="construction_worker", geography_level="tamil_nadu_urban",
             income_p25=10000, income_median=14000, income_p75=19000,
             sample_size=510, confidence="LOW", survey_year=2025,
             source_name="PLFS 2025",
             source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
             data_freshness="PERIODIC"),
    ]
    count = 0
    for p in profiles:
        existing = (session.query(IncomeProfile)
                    .filter_by(occupation_key=p["occupation_key"],
                               geography_level=p["geography_level"])
                    .first())
        if not existing:
            session.add(IncomeProfile(**p, retrieved_at=datetime.now(timezone.utc)))
            count += 1
    session.commit()
    return count


def seed_data_sources(session: Session) -> int:
    """Seed the 11 authoritative datasets registered for RIVO."""
    sources = [
        dict(source_name="GCC GIS 2025", layer="city_boundary",
             source_url="https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/EDPMobile2025/FeatureServer/layers",
             license="Verify current source terms", attribution="Greater Chennai Corporation",
             data_freshness="PERIODIC", update_frequency="annual"),
        dict(source_name="CUMTA GTFS", layer="transit",
             source_url="https://opendata.cumta.org/",
             license="Verify feed-specific terms",
             attribution="Chennai Unified Metropolitan Transport Authority (CUMTA)",
             data_freshness="PERIODIC", update_frequency="periodic"),
        dict(source_name="PLFS 2025", layer="income",
             source_url="https://microdata.gov.in/NADA/index.php/catalog/284",
             license="Government of India microdata access terms",
             attribution="Ministry of Statistics and Programme Implementation, GoI",
             data_freshness="PERIODIC", update_frequency="annual"),
        dict(source_name="Chennai Health Infrastructure OGD", layer="hospitals",
             source_url="https://ap.data.gov.in/catalog/health-infrastructure-chennai",
             license="Open Government Data License India (OGDL)",
             attribution="Government of Tamil Nadu / data.gov.in",
             data_freshness="PERIODIC", update_frequency="periodic"),
        dict(source_name="UDISE+", layer="schools",
             source_url="https://udiseplus.gov.in/",
             license="Verify current reuse conditions",
             attribution="Ministry of Education, Government of India",
             data_freshness="PERIODIC", update_frequency="annual"),
        dict(source_name="OpenStreetMap", layer="roads_pois",
             source_url="https://www.openstreetmap.org/",
             license="ODbL 1.0", attribution="© OpenStreetMap contributors",
             data_freshness="PERIODIC", update_frequency="continuous"),
        dict(source_name="WorldPop 2025", layer="population",
             source_url="https://hub.worldpop.org/geodata/summary?id=73807",
             license="CC BY 4.0", attribution="WorldPop, University of Southampton",
             data_freshness="HISTORICAL", update_frequency="annual"),
        dict(source_name="CMRL Phase II", layer="metro_scenario",
             source_url="https://chennaimetrorail.org/cmrl-profile/",
             license="Public information", attribution="Chennai Metro Rail Limited (CMRL)",
             data_freshness="HISTORICAL", update_frequency="project-based"),
        dict(source_name="MTC Fares", layer="transit_fares",
             source_url="https://mtcbus.tn.gov.in/Home/fares",
             license="Public information", attribution="Metropolitan Transport Corporation (MTC), Tamil Nadu",
             data_freshness="PERIODIC", update_frequency="as-revised"),
        dict(source_name="CMRL Fare Calculator", layer="transit_fares",
             source_url="https://chennaimetrorail.org/fare-calculator/",
             license="Public information", attribution="Chennai Metro Rail Limited (CMRL)",
             data_freshness="PERIODIC", update_frequency="as-revised"),
        dict(source_name="RIVO Sample Data", layer="rentals",
             license="Internal sample — NOT real listings",
             attribution="RIVO Team CLAIRES (ST1010) — demo only",
             data_freshness="PERIODIC", update_frequency="static"),
    ]
    count = 0
    for src in sources:
        existing = session.query(DataSource).filter_by(source_name=src["source_name"]).first()
        if not existing:
            session.add(DataSource(**src, retrieved_at=datetime.now(timezone.utc)))
            count += 1
    session.commit()
    return count


def seed_gtfs_stops(session: Session) -> int:
    """Loads downloaded CMRL and Chennai GTFS stops from data/seed/gtfs."""
    gtfs_dirs = [
        BASE_DIR.parent / "data" / "seed" / "gtfs" / "cmrl-gtfs" / "stops.txt",
        BASE_DIR.parent / "data" / "seed" / "gtfs" / "chennai-unified-gtfs" / "stops.txt",
    ]
    existing_stop_ids = set(session.scalars(select(TransitStop.stop_id)).all())
    total_loaded = 0

    for stops_file in gtfs_dirs:
        if not stops_file.exists():
            continue
        try:
            with open(stops_file, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                batch = []
                for row in reader:
                    stop_id = row.get("stop_id")
                    stop_name = row.get("stop_name")
                    lat = row.get("stop_lat")
                    lon = row.get("stop_lon")
                    if not (stop_id and stop_name and lat and lon):
                        continue
                    if stop_id in existing_stop_ids:
                        continue
                    try:
                        stop = TransitStop(
                            stop_id=stop_id,
                            stop_name=stop_name,
                            stop_lat=float(lat),
                            stop_lon=float(lon),
                            stop_code=row.get("stop_code"),
                        )
                        batch.append(stop)
                        existing_stop_ids.add(stop_id)
                    except ValueError:
                        continue

                    if len(batch) >= 1000:
                        session.bulk_save_objects(batch)
                        session.commit()
                        total_loaded += len(batch)
                        batch = []

                if batch:
                    session.bulk_save_objects(batch)
                    session.commit()
                    total_loaded += len(batch)
        except Exception as err:
            session.rollback()
            logger.warning(f"Error reading {stops_file.name}: {err}")

    return total_loaded


def main() -> None:
    logger.info("Starting RIVO seed data script...")
    engine = get_target_engine()

    # Create tables
    WorkerProfile.__table__.create(bind=engine, checkfirst=True)
    IncomeProfile.__table__.create(bind=engine, checkfirst=True)
    DataSource.__table__.create(bind=engine, checkfirst=True)
    TransitStop.__table__.create(bind=engine, checkfirst=True)

    with Session(engine) as session:
        new_occ = seed_occupations(session)
        new_inc = seed_income_profiles(session)
        new_src = seed_data_sources(session)
        new_gtfs = seed_gtfs_stops(session)

        tot_occ = session.query(WorkerProfile).count()
        tot_inc = session.query(IncomeProfile).count()
        tot_src = session.query(DataSource).count()
        tot_gtfs = session.query(TransitStop).count()

    logger.info(
        f"✓ Database Ready & Seeded: {tot_occ} occupations, {tot_inc} PLFS income profiles, "
        f"{tot_src} authoritative data sources, and {tot_gtfs:,} real GTFS transit stops active in database."
    )
    if new_occ or new_inc or new_src or new_gtfs:
        logger.info(
            f"  (Newly inserted in this run: +{new_occ} occupations, +{new_inc} incomes, +{new_src} sources, +{new_gtfs} GTFS stops)"
        )
    else:
        logger.info("  (All records are already up to date in the database — no duplicate inserts needed)")


if __name__ == "__main__":
    main()
