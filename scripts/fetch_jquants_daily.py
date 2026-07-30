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
from ai_fund_lab_v2.data_quality import FetchPlanBuilder, TradingCalendarService
from ai_fund_lab_v2.data_quality.trading_calendar import CalendarDataNotFoundError
from ai_fund_lab_v2.data_quality.trading_calendar import iter_dates
from ai_fund_lab_v2.data_sources.jquants import ENDPOINT_PATHS, JQuantsClient, JQuantsRawIngestor
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import raw_output_path
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.logging import configure_runtime_logger

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "earnings_calendar", "trading_calendar", "fins_summary", "all")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    paths.ensure_base_dirs()
    store = MarketDataStore(paths, raw_storage_format=settings.raw_storage_format)

    try:
        plan_items = build_plan(args, store)
    except CalendarDataNotFoundError as exc:
        print(f"ERROR fetch plan unavailable: {exc}", file=sys.stderr)
        return 2
    if args.from_date and args.to_date and not plan_items:
        print(empty_plan_error_message(args, store), file=sys.stderr)
        return 2

    if args.dry_run:
        for item in plan_items:
            print(
                "DRY-RUN "
                f"endpoint={item.endpoint_name} "
                f"path={ENDPOINT_PATHS[item.endpoint_name]} "
                f"date={item.date} from_date={item.from_date} to_date={item.to_date} "
                f"reason={item.reason} "
                f"output={raw_output_path(paths, item.endpoint_name, settings.raw_storage_format)} "
                f"storage_format={settings.raw_storage_format} manifest={paths.raw_data / 'jquants' / 'manifest.jsonl'} "
                "validation=planned"
            )
        return 0

    logger = configure_runtime_logger("ai_fund_lab_v2.fetch_jquants_daily", paths.logs, "fetch_jquants_daily.log")
    log_skipped_non_business_days(args, plan_items, logger)
    client = JQuantsClient(settings=settings.jquants, paths=paths)
    ingestor = JQuantsRawIngestor(client=client, store=store, paths=paths)

    for item in plan_items:
        result = ingestor.fetch_and_store(
            item.endpoint_name,
            date=item.date,
            from_date=item.from_date,
            to_date=item.to_date,
            code=args.code,
            max_pages=args.max_pages,
        )
        logger.info(
            "J-Quants raw fetch completed endpoint=%s records_saved=%s output_path=%s",
            result.endpoint_name,
            result.records_saved,
            result.output_path,
        )
        print(f"{result.endpoint_name}: saved {result.records_saved} records to {result.output_path}")
        print(f"  validation={result.validation_status} diff={result.diff_summary}")
    return 0


def build_plan(args: argparse.Namespace, store: MarketDataStore):
    if args.from_date and args.to_date:
        builder = FetchPlanBuilder(TradingCalendarService(store))
        return builder.build_fetch_plan(args.endpoint, args.from_date, args.to_date)
    endpoint_names = list(ENDPOINT_PATHS) if args.endpoint == "all" else [args.endpoint]
    from ai_fund_lab_v2.data_quality import FetchPlanItem

    return [
        FetchPlanItem(endpoint_name, date=args.date, from_date=args.from_date, to_date=args.to_date, reason="explicit_args")
        for endpoint_name in endpoint_names
    ]


def empty_plan_error_message(args: argparse.Namespace, store: MarketDataStore) -> str:
    rows = store.read_raw_collection("jquants/trading_calendar")
    dates = sorted(str(row.get("target_date") or row.get("Date") or "") for row in rows if row.get("target_date") or row.get("Date"))
    coverage = f"trading_calendar_coverage={dates[0]}..{dates[-1]} rows={len(rows)}" if dates else "trading_calendar_coverage=missing"
    return (
        "ERROR fetch plan is empty: "
        f"endpoint={args.endpoint} from_date={args.from_date} to_date={args.to_date} {coverage}. "
        "No API request, storage write, or manifest append was performed. "
        "Materialize trading_calendar coverage for the requested range or choose a range with business days."
    )


def log_skipped_non_business_days(args: argparse.Namespace, plan_items, logger) -> None:
    if not args.from_date or not args.to_date:
        return
    planned = {(item.endpoint_name, item.date) for item in plan_items if item.date}
    for endpoint_name in ("daily_quotes", "fins_summary"):
        if args.endpoint not in (endpoint_name, "all"):
            continue
        for day in iter_dates(args.from_date, args.to_date):
            if (endpoint_name, day) not in planned:
                logger.info("skip non-business day endpoint=%s date=%s", endpoint_name, day)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch J-Quants V2 raw market data into runtime storage.")
    parser.add_argument("--date", help="Target date as YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--from-date", help="Start date as YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--to-date", help="End date as YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--code", help="Optional issue code.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="daily_quotes")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runtime-dir", type=Path)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
