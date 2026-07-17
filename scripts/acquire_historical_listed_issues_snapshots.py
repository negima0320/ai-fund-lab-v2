#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_sources.jquants import JQuantsClient
from ai_fund_lab_v2.runtime import RuntimePaths
from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    RETENTION_START_DATE,
    acquire_snapshots,
    rebuild_snapshot_index,
    resolve_listed_issues_snapshot,
)

DEFAULT_SNAPSHOT_ROOT = Path(".runtime/operations/jquants/historical_snapshots/listed_issues")
DEFAULT_CALENDAR_SOURCE = Path(".runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target_dates = resolve_target_dates(args)
    plan = build_plan(args, target_dates)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        if args.write_evidence:
            write_json(args.snapshot_root / "dry_run_plan.json", plan)
        return 0

    if args.validate_only:
        index = rebuild_snapshot_index(args.snapshot_root)
        validation = build_validation_payload(args, target_dates, index)
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        if args.write_evidence:
            write_json(args.snapshot_root / "validation_report.json", validation)
        return 0 if validation["status"] == "PASS" else 20

    settings = load_settings()
    settings.jquants.require_api_key()
    paths = replace(settings.runtime_paths, runtime_dir=args.snapshot_root / "_client_runtime")
    client = JQuantsClient(settings=settings.jquants, paths=paths)
    progress_records: list[dict[str, Any]] = []

    def progress(record: dict[str, Any]) -> None:
        progress_records.append(record)
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))

    result = acquire_snapshots(
        client=client,
        snapshot_root=args.snapshot_root,
        target_dates=target_dates,
        storage_format=args.storage_format,
        max_pages=args.max_pages,
        sleep_seconds=args.sleep_seconds,
        retry_count=args.retry_count,
        skip_verified_existing=args.skip_verified_existing,
        progress=progress,
    )
    result["plan"] = plan
    result["progress_records"] = progress_records
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.write_evidence:
        write_json(args.snapshot_root / "acquisition_result.json", result)
    return 0 if result.get("status") == "PASS" else 20


def resolve_target_dates(args: argparse.Namespace) -> list[str]:
    start = max(args.start_date, RETENTION_START_DATE)
    end = args.end_date
    records = read_calendar_records(args.calendar_source)
    target_dates = [
        str(record.get("Date"))
        for record in records
        if str(record.get("HolDiv") or record.get("HolidayDivision") or "") == "1"
        and start <= str(record.get("Date")) <= end
    ]
    return sorted(dict.fromkeys(target_dates))


def read_calendar_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(f"calendar source missing: {path}")
    if path.suffix == ".parquet":
        import pandas as pd

        frame = pd.read_parquet(path)
        return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    raise SystemExit(f"unsupported calendar source format: {path}")


def build_plan(args: argparse.Namespace, target_dates: list[str]) -> dict[str, Any]:
    existing = [day for day in target_dates if (args.snapshot_root / "snapshots" / day / "manifest.json").is_file()]
    pending = [day for day in target_dates if day not in set(existing)]
    calendar_records = read_calendar_records(args.calendar_source)
    calendar_dates = sorted({str(record.get("Date")) for record in calendar_records if record.get("Date")})
    effective_start = max(args.start_date, RETENTION_START_DATE)
    coverage_status = "PASS"
    coverage_reason = "calendar_covers_requested_window"
    if not calendar_dates:
        coverage_status = "HALT"
        coverage_reason = "calendar_empty"
    elif calendar_dates[0] > effective_start:
        coverage_status = "REVIEW_REQUIRED"
        coverage_reason = "calendar_starts_after_effective_start_date"
    elif calendar_dates[-1] < args.end_date:
        coverage_status = "REVIEW_REQUIRED"
        coverage_reason = "calendar_ends_before_requested_end_date"
    return {
        "schema_version": "historical_listed_issues_acquisition_plan_v1",
        "generated_at": now_utc(),
        "snapshot_root": str(args.snapshot_root),
        "calendar_source": str(args.calendar_source),
        "start_date": args.start_date,
        "effective_start_date": effective_start,
        "end_date": args.end_date,
        "retention_start_date": RETENTION_START_DATE,
        "calendar_coverage_status": coverage_status,
        "calendar_coverage_reason": coverage_reason,
        "calendar_min_date": calendar_dates[0] if calendar_dates else "",
        "calendar_max_date": calendar_dates[-1] if calendar_dates else "",
        "target_business_day_count": len(target_dates),
        "existing_verified_candidate_count": len(existing),
        "pending_request_count": len(pending),
        "estimated_api_requests": len(pending) if args.skip_verified_existing else len(target_dates),
        "max_pages": args.max_pages,
        "sleep_seconds": args.sleep_seconds,
        "retry_count": args.retry_count,
        "skip_verified_existing": args.skip_verified_existing,
        "storage_format": args.storage_format,
        "dry_run_only": args.dry_run,
        "target_dates_sample": target_dates[:10],
        "target_dates_tail": target_dates[-10:],
        "operator_command": operator_command(args),
        "forbidden_during_dry_run": ["jquants_api_fetch", "runtime_test", "broker_write", "order_submit"],
    }


def build_validation_payload(args: argparse.Namespace, target_dates: list[str], index: dict[str, Any]) -> dict[str, Any]:
    snapshots = {str(item.get("snapshot_date")) for item in index.get("snapshots") or []}
    gaps = [day for day in target_dates if day not in snapshots]
    samples = {
        day: resolve_listed_issues_snapshot(snapshot_root=args.snapshot_root, business_date=day).to_payload()
        for day in [target_dates[0], "2022-01-04", "2026-06-29", "2026-07-06", target_dates[-1]]
        if target_dates and target_dates[0] <= day <= target_dates[-1]
    }
    return {
        "schema_version": "historical_listed_issues_store_validation_v1",
        "generated_at": now_utc(),
        "status": "PASS" if index.get("status") == "PASS" and not gaps else "HALT",
        "snapshot_root": str(args.snapshot_root),
        "target_count": len(target_dates),
        "snapshot_count": len(snapshots),
        "coverage_ratio": (len(snapshots & set(target_dates)) / len(target_dates)) if target_dates else 0.0,
        "gap_count": len(gaps),
        "gaps": gaps,
        "index": index,
        "resolver_sample_matrix": samples,
    }


def operator_command(args: argparse.Namespace) -> str:
    parts = [
        "PYTHONPATH=src",
        "python3",
        "scripts/acquire_historical_listed_issues_snapshots.py",
        "--snapshot-root",
        str(args.snapshot_root),
        "--start-date",
        args.start_date,
        "--end-date",
        args.end_date,
        "--calendar-source",
        str(args.calendar_source),
        "--storage-format",
        args.storage_format,
        "--max-pages",
        str(args.max_pages),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--retry-count",
        str(args.retry_count),
        "--resume",
        "--skip-verified-existing",
        "--write-evidence",
    ]
    return " ".join(parts)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_end_date() -> str:
    # Operator may override. Default stays conservative: previous calendar day.
    today = date.today()
    return today.isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire append-only historical J-Quants Listed Issues snapshots.")
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--start-date", default=RETENTION_START_DATE)
    parser.add_argument("--end-date", default=default_end_date())
    parser.add_argument("--calendar-source", type=Path, default=DEFAULT_CALENDAR_SOURCE)
    parser.add_argument("--storage-format", choices=("parquet",), default="parquet")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--retry-count", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-verified-existing", action="store_true")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
