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
from ai_fund_lab_v2.data_quality import FetchPlanBuilder, RawQualityChecker, TradingCalendarService
from ai_fund_lab_v2.data_quality.refetch_plan import build_refetch_plan
from ai_fund_lab_v2.data_store import MarketDataStore

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "trading_calendar", "fins_summary", "all")
REASON_CHOICES = ("validation_error", "missing", "empty", "all")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    store = MarketDataStore(paths, raw_storage_format=settings.raw_storage_format)
    checker = RawQualityChecker(store, paths, FetchPlanBuilder(TradingCalendarService(store)))
    items = build_refetch_plan(checker, args.endpoint, args.from_date, args.to_date, args.reason)
    rows = [item.to_dict() for item in items]
    rendered = json.dumps(rows, ensure_ascii=False, indent=2) if args.output == "json" else render_markdown(rows)
    print(rendered)
    report_dir = paths.reports / "jquants_refetch_plan"
    report_dir.mkdir(parents=True, exist_ok=True)
    suffix = "json" if args.output == "json" else "md"
    report_path = report_dir / f"refetch_plan_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.{suffix}"
    report_path.write_text(rendered, encoding="utf-8")
    print(f"report={report_path}")
    return 0


def render_markdown(rows: list[dict]) -> str:
    lines = ["# J-Quants Refetch Plan", ""]
    lines.append("| endpoint | target_date | reason | priority | status | validation | command |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        lines.append(
            f"| {row['endpoint_name']} | {row.get('target_date')} | {row['reason']} | {row['priority']} | "
            f"{row['current_status']} | {row['validation_status']} | `{row['suggested_command']}` |"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a J-Quants refetch plan from manifest and quality data.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="all")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--reason", choices=REASON_CHOICES, default="all")
    parser.add_argument("--output", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--dry-run", action="store_true", help="Kept explicit: this CLI never calls the API or writes raw data.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
