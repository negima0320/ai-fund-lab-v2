from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    build_candidate_features_mock_with_audit,
    read_daily_quotes_normalized_small_range,
    write_candidate_feature_outputs_with_prefix,
)


def run_real_feature_dry_run(
    *,
    runtime_dir: Path | str = ".runtime",
    as_of_date: str | None = None,
    lookback_business_days: int = 60,
    max_codes: int = 10,
    max_rows: int = 1000,
    input_format: str = "auto",
    report_dir: Path | str = "reports/candidate_ai",
) -> dict[str, Any]:
    loader_result = read_daily_quotes_normalized_small_range(
        runtime_dir=runtime_dir,
        as_of_date=as_of_date,
        lookback_business_days=lookback_business_days,
        max_codes=max_codes,
        max_rows=max_rows,
        input_format=input_format,
    )
    if loader_result.status == "SKIPPED" or not loader_result.rows_path:
        summary = _summary_from_skipped_loader(loader_result)
        summary["summary_path"] = str(_write_summary(summary, report_dir))
        return summary

    loader_rows = _read_rows(Path(loader_result.rows_path))
    build_result = build_candidate_features_mock_with_audit(
        loader_rows,
        as_of_date=str(loader_result.normalized_as_of_date),
        source_snapshot_id=f"real_normalized_dry_run:{loader_result.normalized_as_of_date}",
    )
    output_paths = write_candidate_feature_outputs_with_prefix(
        build_result.rows,
        audit=build_result.audit,
        runtime_dir=runtime_dir,
        filename_prefix="candidate_features_real_dry_run",
        input_sources=("daily_quotes_normalized",),
        extra_manifest={
            "loader_manifest_path": loader_result.manifest_path,
            "loader_audit_path": loader_result.audit_path,
            "input_path": loader_result.input_path,
            "storage_format": loader_result.storage_format,
            "dropped_future_row_count": loader_result.dropped_future_row_count,
            "window_start_date": loader_result.window_start_date,
            "normalized_as_of_date": loader_result.normalized_as_of_date,
            "max_codes": max_codes,
            "max_rows": max_rows,
            "lookback_business_days": lookback_business_days,
        },
        extra_audit={
            "loader_status": loader_result.status,
            "loader_audit_path": loader_result.audit_path,
            "dropped_future_row_count": loader_result.dropped_future_row_count,
            "window_start_date": loader_result.window_start_date,
            "normalized_as_of_date": loader_result.normalized_as_of_date,
            "max_codes": max_codes,
            "max_rows": max_rows,
            "lookback_business_days": lookback_business_days,
        },
    )
    status = "OK" if build_result.validation.is_valid and build_result.audit.status == "OK" else "ERROR"
    summary = {
        "status": status,
        "requested_as_of_date": loader_result.requested_as_of_date,
        "normalized_as_of_date": loader_result.normalized_as_of_date,
        "window_start_date": loader_result.window_start_date,
        "input_row_count": loader_result.input_row_count,
        "filtered_row_count": loader_result.filtered_row_count,
        "dropped_future_row_count": loader_result.dropped_future_row_count,
        "code_count": loader_result.code_count,
        "feature_row_count": build_result.audit.row_count,
        "eligible_count": build_result.audit.eligible_count,
        "excluded_count": build_result.audit.excluded_count,
        "schema_validation_status": "OK" if build_result.validation.is_valid else "ERROR",
        "leakage_audit_status": build_result.audit.status,
        "features_path": str(output_paths["features"]),
        "manifest_path": str(output_paths["manifest"]),
        "audit_path": str(output_paths["audit"]),
        "loader_manifest_path": loader_result.manifest_path,
        "loader_audit_path": loader_result.audit_path,
        "storage_format": loader_result.storage_format,
    }
    summary["summary_path"] = str(_write_summary(summary, report_dir))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-H real normalized Candidate features dry-run.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory.")
    parser.add_argument("--as-of-date", default=None, help="Requested as_of_date. Defaults to latest normalized date.")
    parser.add_argument("--lookback-business-days", type=int, default=60, help="Business-day lookback window.")
    parser.add_argument("--max-codes", type=int, default=10, help="Maximum codes to include.")
    parser.add_argument("--max-rows", type=int, default=1000, help="Maximum normalized source rows.")
    parser.add_argument("--input-format", default="auto", choices=("auto", "jsonl", "parquet"), help="Input format.")
    parser.add_argument("--report-dir", default="reports/candidate_ai", help="Summary report directory.")
    args = parser.parse_args(argv)

    summary = run_real_feature_dry_run(
        runtime_dir=args.runtime_dir,
        as_of_date=args.as_of_date,
        lookback_business_days=args.lookback_business_days,
        max_codes=args.max_codes,
        max_rows=args.max_rows,
        input_format=args.input_format,
        report_dir=args.report_dir,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"OK", "SKIPPED"} else 1


def _summary_from_skipped_loader(loader_result: Any) -> dict[str, Any]:
    return {
        "status": "SKIPPED",
        "reason": loader_result.message,
        "requested_as_of_date": loader_result.requested_as_of_date,
        "normalized_as_of_date": loader_result.normalized_as_of_date,
        "window_start_date": loader_result.window_start_date,
        "input_row_count": loader_result.input_row_count,
        "filtered_row_count": loader_result.filtered_row_count,
        "dropped_future_row_count": loader_result.dropped_future_row_count,
        "code_count": loader_result.code_count,
        "feature_row_count": 0,
        "eligible_count": 0,
        "excluded_count": 0,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "features_path": None,
        "manifest_path": loader_result.manifest_path,
        "audit_path": loader_result.audit_path,
        "loader_manifest_path": loader_result.manifest_path,
        "loader_audit_path": loader_result.audit_path,
        "storage_format": loader_result.storage_format,
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(row) for row in payload.get("rows", [])]


def _write_summary(summary: dict[str, Any], report_dir: Path | str) -> Path:
    path = Path(report_dir) / "phase4h_real_feature_dry_run_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
