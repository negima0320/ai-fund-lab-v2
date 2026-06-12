#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS
from ai_fund_lab_v2.data_store import manifest_path, read_manifest

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "trading_calendar", "fins_summary", "all")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)

    rows = filter_entries(
        read_manifest(manifest_path(paths.raw_data)),
        args.endpoint,
        args.latest,
        validation_status=args.validation_status,
        storage_format=args.storage_format,
        status=args.status,
        since=args.since,
    )
    if args.needs_refetch:
        rows = needs_refetch(rows)
    if args.summary:
        rows = summary_rows(rows)

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print_table(rows, needs=args.needs_refetch, summary=args.summary)
    return 0


def filter_entries(
    entries: list[dict],
    endpoint_name: str,
    latest: bool,
    *,
    validation_status: str | None = None,
    storage_format: str | None = None,
    status: str | None = None,
    since: str | None = None,
) -> list[dict]:
    endpoint_path = None if endpoint_name == "all" else ENDPOINT_PATHS[endpoint_name]
    rows = [entry for entry in entries if endpoint_path is None or entry.get("endpoint") == endpoint_path]
    if validation_status:
        rows = [entry for entry in rows if entry.get("validation_status") == validation_status]
    if storage_format:
        rows = [entry for entry in rows if entry.get("storage_format") == storage_format]
    if status:
        rows = [entry for entry in rows if entry.get("status") == status]
    if since:
        rows = [entry for entry in rows if str(entry.get("fetched_at", ""))[:10] >= since]
    if not latest:
        return rows
    latest_by_endpoint: dict[str, dict] = {}
    for row in rows:
        latest_by_endpoint[row.get("endpoint", "")] = row
    return list(latest_by_endpoint.values())


def needs_refetch(entries: list[dict]) -> list[dict]:
    rows = []
    for entry in entries:
        if entry.get("event_type") == "NORMALIZED":
            continue
        reasons = []
        if entry.get("validation_status") != "OK":
            reasons.append("validation_status_not_ok")
        if entry.get("status") == "ERROR":
            reasons.append("status_error")
        if entry.get("record_count") == 0:
            reasons.append("record_count_zero")
        if entry.get("diff_summary", {}).get("missing_dates"):
            reasons.append("missing_dates")
        if reasons:
            rows.append(
                {
                    "endpoint": entry.get("endpoint"),
                    "target_date": entry.get("target_date"),
                    "from_date": entry.get("from_date"),
                    "to_date": entry.get("to_date"),
                    "reason": ",".join(reasons),
                }
            )
    return rows


def summary_rows(entries: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        if entry.get("event_type") == "NORMALIZED":
            continue
        grouped[entry.get("endpoint", "")].append(entry)
    rows = []
    for endpoint, endpoint_entries in grouped.items():
        latest = endpoint_entries[-1]
        rows.append(
            {
                "endpoint": endpoint,
                "manifest_count": len(endpoint_entries),
                "latest_storage_format": latest.get("storage_format"),
                "latest_validation_status": latest.get("validation_status"),
                "latest_record_count": latest.get("record_count"),
                "needs_refetch_count": len(needs_refetch(endpoint_entries)),
            }
        )
    return rows


def print_table(rows: list[dict], needs: bool = False, summary: bool = False) -> None:
    if summary:
        print("endpoint | manifest_count | latest_storage_format | latest_validation_status | latest_record_count | needs_refetch_count")
        for row in rows:
            print(
                f"{row.get('endpoint')} | {row.get('manifest_count')} | {row.get('latest_storage_format')} | "
                f"{row.get('latest_validation_status')} | {row.get('latest_record_count')} | {row.get('needs_refetch_count')}"
            )
        return
    if needs:
        print("endpoint | target_date | from_date | to_date | reason")
        for row in rows:
            print(f"{row.get('endpoint')} | {row.get('target_date')} | {row.get('from_date')} | {row.get('to_date')} | {row.get('reason')}")
        return

    print("fetched_at | endpoint | target_date | from_date | to_date | records | format | schema | validation | inserted | updated | unchanged | duplicates | status")
    for row in rows:
        diff = row.get("diff_summary", {})
        print(
            f"{row.get('fetched_at')} | {row.get('endpoint')} | {row.get('target_date')} | "
            f"{row.get('from_date')} | {row.get('to_date')} | {row.get('record_count')} | "
            f"{row.get('storage_format')} | {row.get('schema_version')} | {row.get('validation_status')} | "
            f"{diff.get('inserted_count', '')} | {diff.get('updated_count', '')} | "
            f"{diff.get('unchanged_count', '')} | {diff.get('duplicate_key_count', '')} | {row.get('status')}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show J-Quants raw fetch manifest.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="all")
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument("--needs-refetch", action="store_true")
    parser.add_argument("--validation-status", choices=("OK", "WARNING", "ERROR"))
    parser.add_argument("--storage-format", choices=("jsonl", "parquet"))
    parser.add_argument("--status")
    parser.add_argument("--since")
    parser.add_argument("--summary", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
