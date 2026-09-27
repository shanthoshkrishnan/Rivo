"""
RIVO — Bulk Rental Observation Importer
========================================
Usage:
    python -m scripts.import_rental_observations <file> [options]

Supports:
    - CSV files (with headers)
    - JSON files (array of objects)
    - NDJSON files (one JSON object per line)

Mandatory columns/fields:
    listing_id, locality, bhk, rent_monthly, observed_at, source

Optional fields (all others from BulkObservationRow schema):
    area_sqft, furnishing, property_type, latitude, longitude,
    availability_status, is_periodic, is_live

NON-NEGOTIABLE SAFEGUARDS:
    - Records with is_synthetic=true are ALWAYS rejected.
    - Records with is_demo=true are ALWAYS rejected.
    - The import script NEVER fabricates observations.
    - Dry-run mode (--dry-run) shows what would be imported without writing.

Examples:
    # Import from CSV (dry run first):
    python -m scripts.import_rental_observations data/observations.csv --dry-run
    python -m scripts.import_rental_observations data/observations.csv

    # Import from JSON array:
    python -m scripts.import_rental_observations data/observations.json

    # Import only certain sources:
    python -m scripts.import_rental_observations data/obs.csv --source-filter owner_interview

    # Show data quality after import:
    python -m scripts.import_rental_observations data/obs.csv --report
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _load_json(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        return json.loads(text)
    # NDJSON
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _coerce_booleans(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize string 'true'/'false'/'1'/'0' to Python bools for boolean fields."""
    bool_fields = ["is_synthetic", "is_demo", "is_periodic", "is_live"]
    true_vals = {"true", "1", "yes"}
    for row in rows:
        for field in bool_fields:
            v = row.get(field)
            if isinstance(v, str):
                row[field] = v.lower().strip() in true_vals
            elif v is None:
                row[field] = False
    return rows


def _coerce_numerics(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert numeric strings to float/int for CSV imports."""
    float_fields = ["rent_monthly", "area_sqft", "latitude", "longitude"]
    int_fields = ["bhk"]
    for row in rows:
        for f in float_fields:
            v = row.get(f)
            if isinstance(v, str) and v.strip():
                try:
                    row[f] = float(v)
                except ValueError:
                    pass
        for f in int_fields:
            v = row.get(f)
            if isinstance(v, str) and v.strip():
                try:
                    row[f] = int(float(v))
                except ValueError:
                    pass
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="RIVO Bulk Rental Observation Importer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file", type=Path, help="CSV, JSON, or NDJSON file to import")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate rows and print summary without writing observations",
    )
    parser.add_argument(
        "--source-filter",
        metavar="SOURCE",
        help="Only import rows whose 'source' field matches this value",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print data quality report after import",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any rows are rejected",
    )
    args = parser.parse_args()

    # ── Load file ─────────────────────────────────────────────────────────────
    if not args.file.exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        return 2

    suffix = args.file.suffix.lower()
    if suffix == ".csv":
        raw_rows = _load_csv(args.file)
    elif suffix in (".json", ".ndjson", ".jsonl"):
        raw_rows = _load_json(args.file)
    else:
        print(
            f"ERROR: Unsupported file format '{suffix}'. Use .csv, .json, .ndjson, or .jsonl",
            file=sys.stderr,
        )
        return 2

    raw_rows = _coerce_booleans(raw_rows)
    raw_rows = _coerce_numerics(raw_rows)

    # ── Optional source filter ────────────────────────────────────────────────
    if args.source_filter:
        before = len(raw_rows)
        raw_rows = [r for r in raw_rows if r.get("source") == args.source_filter]
        print(f"Source filter '{args.source_filter}': kept {len(raw_rows)}/{before} rows")

    if not raw_rows:
        print("No rows to import after filtering.")
        return 0

    # ── Validate with Pydantic ────────────────────────────────────────────────
    from app.schemas.observation import BulkObservationRow

    validated: List[BulkObservationRow] = []
    parse_errors: List[str] = []

    for i, row in enumerate(raw_rows):
        try:
            validated.append(BulkObservationRow.model_validate(row))
        except Exception as exc:
            parse_errors.append(f"Row {i+1}: {exc}")

    if parse_errors:
        print(f"\n⚠  Parse errors ({len(parse_errors)} rows):")
        for e in parse_errors[:20]:
            print(f"   {e}")
        if len(parse_errors) > 20:
            print(f"   ... and {len(parse_errors)-20} more")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Loaded {len(raw_rows)} raw rows → {len(validated)} valid")

    if args.dry_run:
        # Summarize without writing
        synthetic = sum(1 for r in validated if r.is_synthetic)
        demo = sum(1 for r in validated if r.is_demo)
        would_accept = len(validated) - synthetic - demo
        print(f"\nDRY RUN SUMMARY")
        print(f"  Would reject (is_synthetic=True): {synthetic}")
        print(f"  Would reject (is_demo=True):      {demo}")
        print(f"  Would accept:                     {would_accept}")
        sources = sorted({r.source for r in validated})
        localities = sorted({r.locality for r in validated})
        print(f"  Sources:    {sources}")
        print(f"  Localities: {localities}")
        print(f"\nRe-run without --dry-run to write observations.")
        return 0

    # ── Import ────────────────────────────────────────────────────────────────
    from app.services.observation_service import observation_service

    result = observation_service.bulk_import(validated)

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\nIMPORT RESULT")
    print(f"  Total rows:              {result.total_rows}")
    print(f"  Accepted:                {result.accepted}")
    print(f"  Rejected (synthetic):    {result.rejected_synthetic}")
    print(f"  Rejected (demo):         {result.rejected_demo}")
    print(f"  Rejected (parse error):  {result.rejected_validation_error}")
    print(f"  Eligible for model:      {result.eligible_for_model}")
    print(f"  Sources:                 {result.sources}")
    print(f"  Localities:              {result.localities}")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for e in result.errors[:20]:
            print(f"    {e}")

    if args.report:
        dq = observation_service.data_quality_report()
        print(f"\nDATA QUALITY REPORT")
        print(f"  Total observations:      {dq.total_observations}")
        print(f"  Real observations:       {dq.real_observations}")
        print(f"  Demo observations:       {dq.demo_observations}")
        print(f"  Eligible for model:      {dq.eligible_for_model}")
        print(f"  Unique properties:       {dq.unique_properties}")
        print(f"  Unique localities:       {len(dq.unique_localities)}")
        print(f"  Unique sources:          {len(dq.unique_sources)}")
        print(f"  Temporal span (days):    {dq.temporal_span_days}")
        print(f"  Model status:            {dq.model_eligibility_status}")
        print(f"  Observations needed:     {dq.observations_needed}")
        if dq.model_ready:
            print(f"  🎉 MODEL ELIGIBLE — run: python -m scripts.train_rent_model")
        else:
            print(f"  ⏳ Not yet eligible. {dq.observations_needed} more needed.")

    rejected_any = (
        result.rejected_synthetic + result.rejected_demo + result.rejected_validation_error
        + len(parse_errors)
    )
    if args.strict and rejected_any > 0:
        print(f"\n[--strict] Exiting non-zero: {rejected_any} rows were rejected.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
