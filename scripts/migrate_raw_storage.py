#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS, RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import (
    RAW_SCHEMAS,
    ManifestEntry,
    create_storage_backend,
    append_manifest,
    manifest_path,
    now_utc,
    validate_records,
)

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "trading_calendar", "fins_summary", "all")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)

    endpoint_names = list(ENDPOINT_PATHS) if args.endpoint == "all" else [args.endpoint]
    from_backend = create_storage_backend(args.from_format)
    to_backend = create_storage_backend(args.to_format)

    for endpoint_name in endpoint_names:
        base_path = paths.raw_data / RAW_COLLECTIONS[endpoint_name] / "data"
        source_path = from_backend.path_for(base_path)
        target_path = to_backend.path_for(base_path)
        records = from_backend.read_records(source_path)
        validation = validate_records(endpoint_name, records)
        print(
            f"{endpoint_name}: {args.from_format}->{args.to_format} "
            f"records={len(records)} schema_version={RAW_SCHEMAS[endpoint_name].schema_version} "
            f"source={source_path} target={target_path} validation={validation.status}"
        )
        if args.dry_run:
            continue

        to_backend.write_records(target_path, records)
        migrated_records = to_backend.read_records(target_path)
        if args.validate and len(records) != len(migrated_records):
            raise RuntimeError(f"Migration record_count mismatch for {endpoint_name}")

        append_manifest(
            manifest_path(paths.raw_data),
            ManifestEntry(
                fetched_at=now_utc(),
                endpoint=ENDPOINT_PATHS[endpoint_name],
                target_date=None,
                from_date=None,
                to_date=None,
                record_count=len(migrated_records),
                storage_format=args.to_format,
                storage_path=str(target_path),
                status="MIGRATED",
                validation_status=validation.status,
                schema_version=RAW_SCHEMAS[endpoint_name].schema_version,
                diff_summary={
                    "migration_from": args.from_format,
                    "migration_to": args.to_format,
                    "source_record_count": len(records),
                    "target_record_count": len(migrated_records),
                    "duplicate_key_count": validation.duplicate_key_count,
                },
                request_params={"event": "migration", "endpoint_name": endpoint_name, "validate": args.validate},
            ),
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate J-Quants raw storage files between formats.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="all")
    parser.add_argument("--from-format", choices=("jsonl", "parquet"), required=True)
    parser.add_argument("--to-format", choices=("jsonl", "parquet"), required=True)
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
