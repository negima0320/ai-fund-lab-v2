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
from ai_fund_lab_v2.data_quality import FetchPlanBuilder, RawQualityChecker, TradingCalendarService
from ai_fund_lab_v2.data_store import MarketDataStore

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "earnings_calendar", "trading_calendar", "fins_summary", "all")
OUTPUT_CHOICES = ("markdown", "json", "both")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    paths.ensure_base_dirs()

    store = MarketDataStore(paths, raw_storage_format=settings.raw_storage_format)
    checker = RawQualityChecker(
        store=store,
        paths=paths,
        fetch_plan_builder=FetchPlanBuilder(TradingCalendarService(store)),
    )
    reports = checker.check_many(args.endpoint, args.from_date, args.to_date)
    json_path, markdown_path = checker.save_reports(reports, args.output)

    summary = ", ".join(f"{report.endpoint_name}:{report.status}" for report in reports)
    print(f"J-Quants raw quality summary: {summary}")
    if json_path:
        print(f"json_report={json_path}")
    if markdown_path:
        print(f"markdown_report={markdown_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check J-Quants raw data completeness under runtime storage.")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="all")
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--output", choices=OUTPUT_CHOICES, default="both")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
