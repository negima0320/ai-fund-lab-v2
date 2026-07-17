#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data.jquants_fetch_policy import endpoint_capability_manifest
from ai_fund_lab_v2.data_sources.jquants import JQuantsClient
from ai_fund_lab_v2.data_sources.jquants.client import JQUANTS_TRADING_CALENDAR_ENDPOINT
from ai_fund_lab_v2.runtime_v2.historical_support.trading_calendar_snapshots import (
    acquire_calendar,
    build_index,
    data_path,
    list_trading_days,
    validate_calendar_store,
)

DEFAULT_CALENDAR_ROOT = Path(".runtime/operations/jquants/historical_snapshots/trading_calendar")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(args)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        if args.write_evidence:
            write_json(args.calendar_root / "dry_run_plan.json", plan)
        return 0

    if args.validate_only:
        index = build_index(args.calendar_root)
        validation = validate_calendar_store(
            calendar_root=args.calendar_root,
            required_start_date=args.start_date,
            required_end_date=args.end_date,
        ).to_payload()
        payload = {"index": index, "validation": validation}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        if args.write_evidence:
            write_json(args.calendar_root / "validation.json", validation)
        return 0 if validation.get("status") == "PASS" else 20

    settings = load_settings()
    settings.jquants.require_api_key()
    paths = replace(settings.runtime_paths, runtime_dir=args.calendar_root / "_client_runtime")
    client = JQuantsClient(settings=settings.jquants, paths=paths)
    progress_records: list[dict[str, Any]] = []

    def progress(record: dict[str, Any]) -> None:
        safe_record = json_safe_payload(record)
        progress_records.append(safe_record)
        print(json.dumps(safe_record, ensure_ascii=False, sort_keys=True))

    result = acquire_calendar(
        client=client,
        calendar_root=args.calendar_root,
        start_date=args.start_date,
        end_date=args.end_date,
        max_pages=args.max_pages,
        retry_count=args.retry_count,
        sleep_seconds=args.sleep_seconds,
        skip_verified_existing=args.skip_verified_existing,
        progress=progress,
    )
    result["plan"] = plan
    result["progress_records"] = progress_records
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.write_evidence:
        write_json(args.calendar_root / "acquisition_result.json", result)
    return 0 if result.get("status") in {"PASS", "SKIPPED"} else 20


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    current = inspect_current_calendar(args.current_operational_calendar)
    historical = inspect_historical_calendar(args.calendar_root)
    return {
        "schema_version": "historical_trading_calendar_acquisition_plan_v1",
        "generated_at": now_utc(),
        "endpoint": JQUANTS_TRADING_CALENDAR_ENDPOINT,
        "endpoint_capability": endpoint_capability_manifest(JQUANTS_TRADING_CALENDAR_ENDPOINT),
        "calendar_root": str(args.calendar_root),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "storage_format": args.storage_format,
        "max_pages": args.max_pages,
        "retry_count": args.retry_count,
        "sleep_seconds": args.sleep_seconds,
        "resume": args.resume,
        "skip_verified_existing": args.skip_verified_existing,
        "current_operational_calendar": current,
        "historical_calendar": historical,
        "request_classification": "RANGE_FETCH_PLANNED",
        "dry_run_only": args.dry_run,
        "operator_command": operator_command(args),
        "forbidden_during_dry_run": ["jquants_api_fetch", "listed_issues_bulk_fetch", "runtime_test", "broker_write"],
    }


def inspect_current_calendar(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False}
    import pandas as pd

    frame = pd.read_parquet(path)
    dates = sorted(str(value) for value in frame["Date"].dropna().unique()) if "Date" in frame else []
    holdiv_counts = {str(k): int(v) for k, v in frame["HolDiv"].astype(str).value_counts().items()} if "HolDiv" in frame else {}
    return {
        "path": str(path),
        "exists": True,
        "row_count": int(len(frame)),
        "min_date": dates[0] if dates else "",
        "max_date": dates[-1] if dates else "",
        "holdiv_counts": holdiv_counts,
    }


def inspect_historical_calendar(root: Path) -> dict[str, Any]:
    dpath = data_path(root)
    if not dpath.is_file():
        return {"calendar_root": str(root), "exists": False}
    validation = validate_calendar_store(calendar_root=root).to_payload()
    return {"calendar_root": str(root), "exists": True, "validation": validation}


def operator_command(args: argparse.Namespace) -> str:
    parts = [
        "PYTHONPATH=src",
        "python3",
        "scripts/acquire_historical_trading_calendar.py",
        "--calendar-root",
        str(args.calendar_root),
        "--start-date",
        args.start_date,
        "--end-date",
        args.end_date,
        "--storage-format",
        args.storage_format,
        "--max-pages",
        str(args.max_pages),
        "--retry-count",
        str(args.retry_count),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--resume",
        "--skip-verified-existing",
        "--write-evidence",
    ]
    return " ".join(parts)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe_payload(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire formal historical J-Quants Trading Calendar authority.")
    parser.add_argument("--calendar-root", type=Path, default=DEFAULT_CALENDAR_ROOT)
    parser.add_argument("--start-date", default="2021-07-16")
    parser.add_argument("--end-date", default="2026-07-15")
    parser.add_argument("--storage-format", choices=("parquet",), default="parquet")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--retry-count", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-verified-existing", action="store_true")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--current-operational-calendar",
        type=Path,
        default=Path(".runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet"),
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
