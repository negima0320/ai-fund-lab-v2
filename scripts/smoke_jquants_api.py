#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_sources.jquants import ENDPOINT_PATHS, JQuantsClient, JQuantsRawIngestor
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import raw_output_path
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.logging import configure_runtime_logger
from ai_fund_lab_v2.runtime import RuntimePaths

ENDPOINT_CHOICES = ("daily_quotes", "listed_issues", "earnings_calendar", "trading_calendar", "fins_summary", "all")
IngestorFactory = Callable[[RuntimePaths], JQuantsRawIngestor]


def main(argv: list[str] | None = None, ingestor_factory: IngestorFactory | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    paths.ensure_base_dirs()

    endpoint_names = list(ENDPOINT_PATHS) if args.endpoint == "all" else [args.endpoint]

    if args.dry_run:
        for endpoint_name in endpoint_names:
            print(plan_line(endpoint_name, args, paths, settings.jquants.rate_limit_per_minute, settings.raw_storage_format))
        return 0

    logger = configure_runtime_logger("ai_fund_lab_v2.smoke_jquants_api", paths.logs, "smoke_jquants_api.log")
    ingestor = ingestor_factory(paths) if ingestor_factory else build_live_ingestor(paths)

    for endpoint_name in endpoint_names:
        result = ingestor.fetch_and_store(
            endpoint_name,
            date=args.date,
            from_date=args.from_date,
            to_date=args.to_date,
            max_pages=args.max_pages,
        )
        logger.info(
            "J-Quants smoke fetch completed endpoint=%s records_saved=%s output_path=%s max_pages=%s",
            result.endpoint_name,
            result.records_saved,
            result.output_path,
            args.max_pages,
        )
        print(
            f"{result.endpoint_name}: fetched={result.records_saved} "
            f"saved_to={result.output_path} max_pages={args.max_pages}"
        )
    return 0


def build_live_ingestor(paths: RuntimePaths) -> JQuantsRawIngestor:
    settings = load_settings()
    client = JQuantsClient(settings=settings.jquants, paths=paths)
    return JQuantsRawIngestor(client=client, store=MarketDataStore(paths, raw_storage_format=settings.raw_storage_format), paths=paths)


def plan_line(endpoint_name: str, args: argparse.Namespace, paths: RuntimePaths, rate_limit: int, storage_format: str) -> str:
    return (
        "DRY-RUN "
        f"endpoint={endpoint_name} "
        f"path={ENDPOINT_PATHS[endpoint_name]} "
        f"date={args.date} from_date={args.from_date} to_date={args.to_date} "
        f"output={raw_output_path(paths, endpoint_name, storage_format)} "
        f"rate_limit_per_minute={rate_limit} max_pages={args.max_pages}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual live smoke test for J-Quants V2 API.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, default="daily_quotes")
    parser.add_argument("--date", help="Target date as YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--from-date", help="Start date as YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--to-date", help="End date as YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--runtime-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=1)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
