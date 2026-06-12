from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    build_candidate_features_mock_with_audit,
    discover_daily_quotes_normalized,
    read_daily_quotes_normalized_small_range,
    write_candidate_feature_outputs_with_prefix,
)
from ai_fund_lab_v2.candidate_ai.feature_builder import MIN_LOOKBACK_ROWS  # noqa: E402
from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend  # noqa: E402


DEFAULT_LOOKBACK_BUSINESS_DAYS = 60
DEFAULT_MAX_CODES = 30
DEFAULT_MAX_ROWS = DEFAULT_LOOKBACK_BUSINESS_DAYS * DEFAULT_MAX_CODES


def run_prepared_real_feature_dry_run(
    *,
    runtime_dir: Path | str = ".runtime",
    as_of_date: str | None = None,
    lookback_business_days: int = DEFAULT_LOOKBACK_BUSINESS_DAYS,
    max_codes: int = DEFAULT_MAX_CODES,
    max_rows: int = DEFAULT_MAX_ROWS,
    input_format: str = "auto",
    report_dir: Path | str = "reports/candidate_ai",
) -> dict[str, Any]:
    records_result = _read_normalized_records(runtime_dir=runtime_dir, input_format=input_format)
    if records_result["status"] != "OK":
        summary = _blocked_summary(
            readiness_status="BLOCKED_BY_RUNTIME_OUTPUT",
            reason=records_result["message"],
            as_of_date=as_of_date,
            lookback_business_days=lookback_business_days,
            max_codes=max_codes,
            max_rows=max_rows,
        )
        summary["summary_path"] = str(_write_summary(summary, report_dir))
        return summary

    records = records_result["records"]
    selected_as_of = as_of_date or select_prepared_as_of_date(records, min_lookback_rows=MIN_LOOKBACK_ROWS)
    loader_result = read_daily_quotes_normalized_small_range(
        runtime_dir=runtime_dir,
        as_of_date=selected_as_of,
        lookback_business_days=lookback_business_days,
        max_codes=max_codes,
        max_rows=max_rows,
        input_format=input_format,
    )
    if loader_result.status == "SKIPPED" or not loader_result.rows_path:
        summary = _blocked_summary(
            readiness_status="BLOCKED_BY_RUNTIME_OUTPUT",
            reason=loader_result.message,
            as_of_date=selected_as_of,
            lookback_business_days=lookback_business_days,
            max_codes=max_codes,
            max_rows=max_rows,
            loader_result=loader_result,
        )
        summary["summary_path"] = str(_write_summary(summary, report_dir))
        return summary

    loader_rows = _read_rows(Path(loader_result.rows_path))
    per_code_stats = compute_per_code_lookback_stats(loader_rows, min_lookback_rows=lookback_business_days)
    build_result = build_candidate_features_mock_with_audit(
        loader_rows,
        as_of_date=str(loader_result.normalized_as_of_date),
        source_snapshot_id=f"real_prepared_dry_run:{loader_result.normalized_as_of_date}",
    )
    output_paths = write_candidate_feature_outputs_with_prefix(
        build_result.rows,
        audit=build_result.audit,
        runtime_dir=runtime_dir,
        filename_prefix="candidate_features_real_prepared_dry_run",
        input_sources=("daily_quotes_normalized",),
        extra_manifest={
            "loader_manifest_path": loader_result.manifest_path,
            "loader_audit_path": loader_result.audit_path,
            "input_path": loader_result.input_path,
            "storage_format": loader_result.storage_format,
            "dropped_future_row_count": loader_result.dropped_future_row_count,
            "window_start_date": loader_result.window_start_date,
            "normalized_as_of_date": loader_result.normalized_as_of_date,
            "selected_as_of_date": selected_as_of,
            "lookback_business_days": lookback_business_days,
            "max_codes": max_codes,
            "max_rows": max_rows,
            **per_code_stats,
        },
        extra_audit={
            "loader_status": loader_result.status,
            "loader_audit_path": loader_result.audit_path,
            "dropped_future_row_count": loader_result.dropped_future_row_count,
            "window_start_date": loader_result.window_start_date,
            "normalized_as_of_date": loader_result.normalized_as_of_date,
            "selected_as_of_date": selected_as_of,
            "lookback_business_days": lookback_business_days,
            "max_codes": max_codes,
            "max_rows": max_rows,
            **per_code_stats,
        },
    )
    readiness_status = _readiness_status(
        schema_ok=build_result.validation.is_valid,
        leakage_ok=build_result.audit.status == "OK",
        eligible_count=build_result.audit.eligible_count,
        feature_row_count=build_result.audit.row_count,
    )
    summary = {
        "status": "OK" if readiness_status in {"READY_FOR_FULL_RANGE_FEATURE_DRY_RUN", "BLOCKED_BY_DATA_WINDOW"} else "ERROR",
        "readiness_status": readiness_status,
        "selected_as_of_date": selected_as_of,
        "requested_as_of_date": loader_result.requested_as_of_date,
        "normalized_as_of_date": loader_result.normalized_as_of_date,
        "window_start_date": loader_result.window_start_date,
        "lookback_business_days": lookback_business_days,
        "max_codes": max_codes,
        "max_rows": max_rows,
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
        **per_code_stats,
    }
    summary["summary_path"] = str(_write_summary(summary, report_dir))
    return summary


def select_prepared_as_of_date(records: list[dict[str, Any]], *, min_lookback_rows: int = MIN_LOOKBACK_ROWS) -> str | None:
    by_code: dict[str, list[str]] = {}
    for record in records:
        code = str(record.get("Code") or "")
        date = str(record.get("Date") or "")
        if not code or not date:
            continue
        by_code.setdefault(code, []).append(date)
    candidate_dates = sorted({date for dates in by_code.values() for date in dates})
    for candidate in reversed(candidate_dates):
        if any(len([date for date in dates if date <= candidate]) >= min_lookback_rows for dates in by_code.values()):
            return candidate
    return candidate_dates[-1] if candidate_dates else None


def compute_per_code_lookback_stats(rows: list[dict[str, Any]], *, min_lookback_rows: int = MIN_LOOKBACK_ROWS) -> dict[str, Any]:
    counts = Counter(str(row.get("code")) for row in rows if row.get("code"))
    values = list(counts.values())
    sufficient = sum(1 for value in values if value >= min_lookback_rows)
    insufficient = sum(1 for value in values if value < min_lookback_rows)
    return {
        "per_code_row_count_min": min(values) if values else 0,
        "per_code_row_count_max": max(values) if values else 0,
        "per_code_row_count_mean": round(mean(values), 4) if values else 0,
        "codes_with_sufficient_lookback": sufficient,
        "codes_with_insufficient_lookback": insufficient,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-J prepared real Candidate features dry-run.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory.")
    parser.add_argument("--as-of-date", default=None, help="Optional requested as_of_date. Defaults to auto-selection.")
    parser.add_argument("--lookback-business-days", type=int, default=DEFAULT_LOOKBACK_BUSINESS_DAYS)
    parser.add_argument("--max-codes", type=int, default=DEFAULT_MAX_CODES)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--input-format", default="auto", choices=("auto", "jsonl", "parquet"))
    parser.add_argument("--report-dir", default="reports/candidate_ai")
    args = parser.parse_args(argv)
    summary = run_prepared_real_feature_dry_run(
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


def _read_normalized_records(*, runtime_dir: Path | str, input_format: str) -> dict[str, Any]:
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        return {"status": "SKIPPED", "message": discovery.message, "records": []}
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        return {"status": "SKIPPED", "message": f"could not read normalized data: {type(exc).__name__}", "records": []}
    if not records:
        return {"status": "SKIPPED", "message": "daily_quotes_normalized data is empty", "records": []}
    return {"status": "OK", "message": "OK", "records": records}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(row) for row in payload.get("rows", [])]


def _readiness_status(*, schema_ok: bool, leakage_ok: bool, eligible_count: int, feature_row_count: int) -> str:
    if feature_row_count <= 0:
        return "BLOCKED_BY_RUNTIME_OUTPUT"
    if not schema_ok:
        return "BLOCKED_BY_SCHEMA"
    if not leakage_ok:
        return "BLOCKED_BY_LEAKAGE"
    if eligible_count <= 0:
        return "BLOCKED_BY_DATA_WINDOW"
    return "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    as_of_date: str | None,
    lookback_business_days: int,
    max_codes: int,
    max_rows: int,
    loader_result: Any | None = None,
) -> dict[str, Any]:
    return {
        "status": "OK",
        "readiness_status": readiness_status,
        "reason": reason,
        "selected_as_of_date": as_of_date,
        "requested_as_of_date": getattr(loader_result, "requested_as_of_date", as_of_date),
        "normalized_as_of_date": getattr(loader_result, "normalized_as_of_date", None),
        "window_start_date": getattr(loader_result, "window_start_date", None),
        "lookback_business_days": lookback_business_days,
        "max_codes": max_codes,
        "max_rows": max_rows,
        "input_row_count": getattr(loader_result, "input_row_count", 0),
        "filtered_row_count": getattr(loader_result, "filtered_row_count", 0),
        "dropped_future_row_count": getattr(loader_result, "dropped_future_row_count", 0),
        "code_count": getattr(loader_result, "code_count", 0),
        "feature_row_count": 0,
        "eligible_count": 0,
        "excluded_count": 0,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "features_path": None,
        "manifest_path": getattr(loader_result, "manifest_path", None),
        "audit_path": getattr(loader_result, "audit_path", None),
        "loader_manifest_path": getattr(loader_result, "manifest_path", None),
        "loader_audit_path": getattr(loader_result, "audit_path", None),
        "storage_format": getattr(loader_result, "storage_format", None),
        "per_code_row_count_min": 0,
        "per_code_row_count_max": 0,
        "per_code_row_count_mean": 0,
        "codes_with_sufficient_lookback": 0,
        "codes_with_insufficient_lookback": 0,
    }


def _write_summary(summary: dict[str, Any], report_dir: Path | str) -> Path:
    path = Path(report_dir) / "phase4j_real_feature_prepared_dry_run_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
