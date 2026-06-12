#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import MarketDataStore, append_manifest_record, manifest_path, validate_records  # noqa: E402
from ai_fund_lab_v2.data_store.manifest import sanitize_request_params  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402


DEFAULT_START_DATE = "2026-03-02"
DEFAULT_BUSINESS_DAYS = 66
DEFAULT_CODE_COUNT = 30
DEFAULT_OUTPUT_FORMAT = "parquet"


def prepare_mock_normalized_history(
    *,
    runtime_dir: Path | str = ".runtime",
    start_date: str = DEFAULT_START_DATE,
    business_days: int = DEFAULT_BUSINESS_DAYS,
    code_count: int = DEFAULT_CODE_COUNT,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    report_dir: Path | str = "reports/candidate_ai",
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    paths.ensure_base_dirs()
    raw_records = build_mock_daily_quote_raw_records(
        start_date=start_date,
        business_days=business_days,
        code_count=code_count,
    )
    normalized_records, normalization_report = normalize_daily_quotes(raw_records)
    output_path = write_daily_quotes_normalized(paths, output_format, normalized_records)
    validation = validate_records("daily_quotes_normalized", normalized_records)
    calendar_records = [{"Date": value, "HolDiv": "1"} for value in _business_dates(start_date, business_days)]
    calendar_path = MarketDataStore(paths, raw_storage_format=output_format).save_raw(
        calendar_records,
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary = {
        "status": "OK" if validation.status in {"OK", "WARNING"} and normalized_records else "ERROR",
        "data_source_type": "mock",
        "mock_data_notice": "Phase4-K generated mock normalized history because live J-Quants API access is not required for this phase.",
        "api_call": False,
        "runtime_dir": str(paths.runtime_dir),
        "storage_format": output_format,
        "normalized_storage_path": str(output_path),
        "trading_calendar_storage_path": str(calendar_path),
        "date_min": normalized_records[0]["Date"] if normalized_records else None,
        "date_max": normalized_records[-1]["Date"] if normalized_records else None,
        "business_day_count": business_days,
        "code_count": code_count,
        "row_count": len(normalized_records),
        "normalization_status": normalization_report.status,
        "validation_status": validation.status,
        "created_at": created_at,
    }
    append_manifest_record(
        manifest_path(paths.raw_data),
        {
            "created_at": created_at,
            "event_type": "PHASE4K_MOCK_NORMALIZED_HISTORY",
            "status": summary["status"],
            "endpoint": "daily_quotes_normalized",
            "source_endpoint": "mock_daily_quotes",
            "normalized_endpoint": "daily_quotes_normalized",
            "data_source_type": "mock",
            "api_call": False,
            "output_storage_format": output_format,
            "output_record_count": len(normalized_records),
            "validation_status": validation.status,
            "storage_path": str(output_path),
            "request_params": sanitize_request_params(
                {
                    "phase": "Phase4-K",
                    "start_date": start_date,
                    "business_days": business_days,
                    "code_count": code_count,
                    "output_format": output_format,
                }
            ),
        },
    )
    _write_summary(Path(report_dir) / "phase4k_mock_normalized_history_manifest.json", summary)
    _write_summary(paths.reports / "candidate_ai" / "phase4k_mock_normalized_history_manifest.json", summary)
    return summary


def build_mock_daily_quote_raw_records(*, start_date: str, business_days: int, code_count: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    business_dates = _business_dates(start_date, business_days)
    codes = [f"{1000 + index:04d}0" for index in range(1, code_count + 1)]
    for day_index, value in enumerate(business_dates):
        for code_index, code in enumerate(codes, start=1):
            base = 80.0 + code_index * 1.7 + day_index * (0.35 + code_index * 0.002)
            close = round(base, 3)
            records.append(
                {
                    "Date": value,
                    "Code": code,
                    "O": round(close - 0.6, 3),
                    "H": round(close + 1.1, 3),
                    "L": round(close - 1.3, 3),
                    "C": close,
                    "Vo": int(120_000 + code_index * 700 + day_index * 230),
                }
            )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase4-K mock daily_quotes_normalized history.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--business-days", type=int, default=DEFAULT_BUSINESS_DAYS)
    parser.add_argument("--code-count", type=int, default=DEFAULT_CODE_COUNT)
    parser.add_argument("--output-format", choices=("jsonl", "parquet"), default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--report-dir", default="reports/candidate_ai")
    args = parser.parse_args(argv)
    summary = prepare_mock_normalized_history(
        runtime_dir=args.runtime_dir,
        start_date=args.start_date,
        business_days=args.business_days,
        code_count=args.code_count,
        output_format=args.output_format,
        report_dir=args.report_dir,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "OK" else 1


def _business_dates(start_date: str, business_days: int) -> list[str]:
    if business_days <= 0:
        raise ValueError("business_days must be positive")
    current = date.fromisoformat(start_date)
    output: list[str] = []
    while len(output) < business_days:
        if current.weekday() < 5:
            output.append(current.isoformat())
        current += timedelta(days=1)
    return output


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
