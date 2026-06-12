#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_quality.validation_inspector import inspect_validation
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS
from ai_fund_lab_v2.data_store import MarketDataStore

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "trading_calendar", "fins_summary", "all")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    storage_format = settings.raw_storage_format if args.storage_format == "auto" else args.storage_format
    store = MarketDataStore(paths, raw_storage_format=storage_format)
    endpoint_names = list(ENDPOINT_PATHS) if args.endpoint == "all" else [args.endpoint]
    results = [inspect_validation(store, name, limit=args.limit, target_date=args.date).to_dict() for name in endpoint_names]

    if args.output == "json":
        rendered = json.dumps(results, ensure_ascii=False, indent=2)
    elif args.output == "markdown":
        rendered = render_markdown(results)
    else:
        rendered = render_table(results)
    print(rendered)

    if args.save_report:
        report_dir = paths.reports / "raw_validation_inspection"
        report_dir.mkdir(parents=True, exist_ok=True)
        suffix = "md" if args.output == "markdown" else "json" if args.output == "json" else "txt"
        path = report_dir / f"inspection_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.{suffix}"
        path.write_text(rendered, encoding="utf-8")
        print(f"report={path}")
    return 0


def render_table(results: list[dict]) -> str:
    lines = ["endpoint | schema | status | records | missing_required | missing_key | duplicates | type_warnings | suggested_fix"]
    for result in results:
        lines.append(
            f"{result['endpoint']} | {result['schema_version']} | {result['validation_status']} | "
            f"{result['record_count']} | {result['missing_required_fields']} | {result['missing_key_count']} | "
            f"{result['duplicate_key_count']} | {result['type_warning_count']} | {result['suggested_fix']}"
        )
    return "\n".join(lines)


def render_markdown(results: list[dict]) -> str:
    lines = ["# Raw Validation Inspection", ""]
    for result in results:
        lines.append(f"## {result['endpoint']}")
        lines.append(f"- schema_version: {result['schema_version']}")
        lines.append(f"- validation_status: {result['validation_status']}")
        lines.append(f"- missing_required_fields: {result['missing_required_fields']}")
        lines.append(f"- affected_dates: {', '.join(result['affected_dates']) or '(none)'}")
        lines.append(f"- affected_codes: {', '.join(result['affected_codes']) or '(none)'}")
        lines.append(f"- suggested_fix: {result['suggested_fix']}")
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect raw schema validation issues.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="all")
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--storage-format", choices=("jsonl", "parquet", "auto"), default="auto")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", choices=("table", "json", "markdown"), default="table")
    parser.add_argument("--save-report", action="store_true")
    parser.add_argument("--date")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
