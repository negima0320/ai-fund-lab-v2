#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_quality.normalization import (
    DAILY_QUOTES_ENDPOINT,
    DAILY_QUOTES_NORMALIZED_ENDPOINT,
    NORMALIZED_SCHEMA_VERSION,
    RAW_SCHEMA_VERSION,
    normalize_daily_quotes,
    normalized_output_path,
    read_daily_quotes_raw,
    resolve_input_format,
    write_daily_quotes_normalized,
)
from ai_fund_lab_v2.data_store import append_manifest_record, manifest_path, now_utc, validate_records
from ai_fund_lab_v2.data_store.manifest import sanitize_request_params

ENDPOINT_CHOICES = ("daily_quotes",)
FORMAT_CHOICES = ("jsonl", "parquet")
INPUT_FORMAT_CHOICES = ("auto", "jsonl", "parquet")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    paths.ensure_base_dirs()

    input_format = resolve_input_format(paths, args.input_format)
    output_path = normalized_output_path(paths, args.output_format)
    print(
        "J-Quants raw normalization plan: "
        f"endpoint={args.endpoint} input_format={input_format} output_format={args.output_format} output_path={output_path}"
    )
    if args.dry_run:
        print("dry_run=True api_call=False save=False manifest=False")
        return 0

    raw_records, input_format, input_path = read_daily_quotes_raw(paths, args.input_format)
    normalized_records, report = normalize_daily_quotes(raw_records, limit_errors=args.limit_errors)
    validation = validate_records(DAILY_QUOTES_NORMALIZED_ENDPOINT, normalized_records)
    output_path = write_daily_quotes_normalized(paths, args.output_format, normalized_records)

    append_manifest_record(
        manifest_path(paths.raw_data),
        {
            "created_at": now_utc(),
            "event_type": "NORMALIZED",
            "status": "NORMALIZED",
            "endpoint": DAILY_QUOTES_ENDPOINT,
            "source_endpoint": DAILY_QUOTES_ENDPOINT,
            "normalized_endpoint": DAILY_QUOTES_NORMALIZED_ENDPOINT,
            "raw_schema_version": RAW_SCHEMA_VERSION,
            "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
            "input_storage_format": input_format,
            "output_storage_format": args.output_format,
            "input_record_count": len(raw_records),
            "output_record_count": len(normalized_records),
            "validation_status": validation.status,
            "normalization_report": report.to_dict(),
            "storage_path": str(output_path),
            "input_storage_path": str(input_path),
            "request_params": sanitize_request_params(
                {
                    "endpoint": args.endpoint,
                    "input_format": args.input_format,
                    "output_format": args.output_format,
                    "validate": args.validate,
                }
            ),
        },
    )

    print(
        "normalized "
        f"input_records={len(raw_records)} output_records={len(normalized_records)} "
        f"errors={report.error_count} warnings={report.warning_count} normalization_status={report.status} validation={validation.status}"
    )
    print(f"storage_path={output_path}")
    if args.validate:
        print("validation_summary=" + json.dumps(validation.to_dict(), ensure_ascii=False, sort_keys=True))
        if report.sample_errors:
            print("sample_errors=" + json.dumps(report.sample_errors, ensure_ascii=False))
        if report.sample_warnings:
            print("sample_warnings=" + json.dumps(report.sample_warnings, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize J-Quants raw data into raw_normalized storage.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, required=True)
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--input-format", choices=INPUT_FORMAT_CHOICES, default="auto")
    parser.add_argument("--output-format", choices=FORMAT_CHOICES, default="parquet")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--limit-errors", type=int, default=20)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
