#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PHASE4AB_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json")
PHASE4AD_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ad_controlled_real_runtime_history_fetch_summary.json")
RAW_ROOT = Path(".runtime/data/raw/jquants/equities_bars_daily")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ae_post_fetch_raw_coverage_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4ae_post_fetch_raw_coverage_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ae_post_fetch_raw_coverage_audit.md")

READY = "READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD"
BLOCKED_MISSING_AD = "BLOCKED_BY_MISSING_PHASE4AD_SUMMARY"
BLOCKED_AD_NOT_READY = "BLOCKED_BY_PHASE4AD_NOT_READY"
BLOCKED_MISSING_MANIFEST = "BLOCKED_BY_MISSING_RAW_MANIFEST"
BLOCKED_MISSING_RESPONSES = "BLOCKED_BY_MISSING_RESPONSES"
BLOCKED_MANIFEST_MISMATCH = "BLOCKED_BY_REQUEST_MANIFEST_MISMATCH"
BLOCKED_SCHEMA = "BLOCKED_BY_RAW_SCHEMA"
BLOCKED_COVERAGE = "BLOCKED_BY_COVERAGE_GAP"
BLOCKED_SECRET = "BLOCKED_BY_SECRET_LEAK"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
REQUIRED_BUSINESS_DAYS = 60
REQUIRED_ROW_COLUMNS = {"Date", "Code"}


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    phase4ab_summary_path: Path = PHASE4AB_SUMMARY_PATH,
    phase4ad_summary_path: Path = PHASE4AD_SUMMARY_PATH,
    raw_root: Path = RAW_ROOT,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab_summary_path,
        phase4ad_summary_path=phase4ad_summary_path,
        raw_root=raw_root,
        summary_path=summary_path,
    )
    checks = {
        "summary_exists": summary_path.is_file(),
        "phase4ad_summary_detected": summary.get("phase4ad_summary_detected") is True,
        "raw_manifest_detected": summary.get("raw_manifest_detected") is True,
        "request_manifest_count_ok": summary.get("request_manifest_count") == summary.get("planned_request_count"),
        "response_file_count_ok": summary.get("raw_response_file_count") == summary.get("planned_request_count"),
        "completed_request_count_ok": summary.get("completed_request_count") == summary.get("planned_request_count"),
        "raw_schema_checked": summary.get("raw_schema_status") in {"OK", "ERROR"},
        "manifest_consistency_checked": summary.get("manifest_consistency_status") in {"OK", "ERROR"},
        "coverage_decision_produced": summary.get("readiness_status")
        in {
            READY,
            BLOCKED_MISSING_AD,
            BLOCKED_AD_NOT_READY,
            BLOCKED_MISSING_MANIFEST,
            BLOCKED_MISSING_RESPONSES,
            BLOCKED_MANIFEST_MISMATCH,
            BLOCKED_SCHEMA,
            BLOCKED_COVERAGE,
            BLOCKED_SECRET,
            BLOCKED_OUTPUT_PATH,
        },
        "normalized_not_executed": summary.get("normalized_data_written") is False
        and summary.get("normalized_output_written") is False
        and summary.get("isolated_normalized_path_written") is False,
        "mock_path_not_written": summary.get("mock_path_written") is False,
        "promotion_not_performed": summary.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False,
        "feature_label_training_backtest_trading_not_executed": summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_not_detected": summary.get("secret_value_detected_in_reports") is False
        and summary.get("secret_value_detected_in_manifests") is False,
    }
    result = {
        "phase": "Phase4-AE",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ae_post_fetch_raw_coverage.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_raw_coverage_summary(
    *,
    phase4ab_summary_path: Path = PHASE4AB_SUMMARY_PATH,
    phase4ad_summary_path: Path = PHASE4AD_SUMMARY_PATH,
    raw_root: Path = RAW_ROOT,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    phase4ab = _read_json_optional(phase4ab_summary_path)
    phase4ad = _read_json_optional(phase4ad_summary_path)
    if not phase4ad:
        return _write_summary(summary_path, _blocked_summary(BLOCKED_MISSING_AD))
    if phase4ad.get("readiness_status") != "READY_FOR_POST_FETCH_RAW_AUDIT":
        return _write_summary(summary_path, _blocked_summary(BLOCKED_AD_NOT_READY, phase4ad=phase4ad))
    if not _output_path_safe(raw_root):
        return _write_summary(summary_path, _blocked_summary(BLOCKED_OUTPUT_PATH, phase4ad=phase4ad))

    run_manifest_path = raw_root / "manifest.json"
    if not run_manifest_path.is_file():
        return _write_summary(summary_path, _blocked_summary(BLOCKED_MISSING_MANIFEST, phase4ad=phase4ad))
    response_paths = sorted((raw_root / "responses").glob("*.json"))
    if not response_paths:
        return _write_summary(summary_path, _blocked_summary(BLOCKED_MISSING_RESPONSES, phase4ad=phase4ad))

    run_manifest = _read_json_optional(run_manifest_path)
    request_manifests = _read_json_files(raw_root / "request_manifests")
    responses = [_read_json_optional(path) for path in response_paths]
    planned_request_count = int(phase4ad.get("planned_request_count") or run_manifest.get("planned_request_count") or 0)
    completed_request_count = int(phase4ad.get("completed_request_count") or 0)
    if completed_request_count == 0:
        completed_request_count = int(run_manifest.get("succeeded_request_count") or 0) + int(run_manifest.get("skipped_request_count") or 0)

    requested_dates = sorted(
        {
            str(record.get("target_date") or record.get("request_params", {}).get("date"))
            for record in request_manifests
            if record
        }
    )
    required_business_dates = list(phase4ab.get("target_business_day_list") or [])
    if not required_business_dates:
        required_business_dates = requested_dates

    rows: list[dict[str, Any]] = []
    empty_response_dates: list[str] = []
    response_dates: set[str] = set()
    raw_schema_errors: list[str] = []
    for response in responses:
        response_date = str(response.get("date") or response.get("params", {}).get("date") or "")
        if response_date:
            response_dates.add(response_date)
        payload = response.get("payload")
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raw_schema_errors.append(response_date or "unknown")
            continue
        if not data:
            empty_response_dates.append(response_date)
            continue
        for row in data:
            if not isinstance(row, dict):
                raw_schema_errors.append(response_date or "unknown")
                continue
            if not REQUIRED_ROW_COLUMNS.issubset(row.keys()):
                raw_schema_errors.append(str(row.get("Date") or response_date or "unknown"))
            rows.append(row)

    fetched_dates = sorted({str(row.get("Date")) for row in rows if row.get("Date")})
    fetched_codes = sorted({str(row.get("Code")) for row in rows if row.get("Code")})
    duplicate_date_code_count = _duplicate_count(rows)
    missing_requested_dates = sorted([date for date in requested_dates if date not in fetched_dates])
    missing_required_business_dates = sorted([date for date in required_business_dates if date not in fetched_dates])
    manifest_consistency_status = "OK"
    if len(request_manifests) != planned_request_count or len(response_paths) != planned_request_count:
        manifest_consistency_status = "ERROR"
    if completed_request_count != planned_request_count:
        manifest_consistency_status = "ERROR"

    raw_schema_status = "OK" if not raw_schema_errors else "ERROR"
    secret_in_manifests = _has_secret_terms({"run_manifest": run_manifest, "request_manifests": request_manifests})
    secret_in_reports = _has_secret_terms({"phase4ad": phase4ad})
    coverage_sufficient = len(fetched_dates) >= REQUIRED_BUSINESS_DAYS
    readiness_status = _readiness_status(
        secret_in_manifests=secret_in_manifests,
        secret_in_reports=secret_in_reports,
        manifest_consistency_status=manifest_consistency_status,
        raw_schema_status=raw_schema_status,
        coverage_sufficient=coverage_sufficient,
    )
    summary = {
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "fetch_executed": False,
        "additional_fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "raw_data_written": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ad_summary_detected": True,
        "phase4ad_readiness_status": phase4ad.get("readiness_status"),
        "raw_manifest_detected": True,
        "raw_response_file_count": len(response_paths),
        "request_manifest_count": len(request_manifests),
        "planned_request_count": planned_request_count,
        "completed_request_count": completed_request_count,
        "succeeded_request_count": int(run_manifest.get("succeeded_request_count") or phase4ad.get("succeeded_request_count") or 0),
        "failed_request_count": int(run_manifest.get("failed_request_count") or phase4ad.get("failed_request_count") or 0),
        "skipped_request_count": int(run_manifest.get("skipped_request_count") or phase4ad.get("skipped_request_count") or 0),
        "pagination_request_count": int(run_manifest.get("pagination_request_count") or phase4ad.get("pagination_request_count") or 0),
        "target_start_date": phase4ad.get("target_start_date"),
        "target_end_date": phase4ad.get("target_end_date"),
        "fetched_date_min": fetched_dates[0] if fetched_dates else None,
        "fetched_date_max": fetched_dates[-1] if fetched_dates else None,
        "fetched_date_count": len(fetched_dates),
        "fetched_business_day_count": len(fetched_dates),
        "required_business_day_count": REQUIRED_BUSINESS_DAYS,
        "coverage_sufficient_for_features": coverage_sufficient,
        "missing_business_day_count": max(0, REQUIRED_BUSINESS_DAYS - len(fetched_dates)),
        "empty_response_date_count": len(empty_response_dates),
        "empty_response_dates": empty_response_dates,
        "fetched_dates": fetched_dates,
        "missing_requested_dates": missing_requested_dates,
        "missing_required_business_dates": missing_required_business_dates,
        "required_business_dates": required_business_dates,
        "row_count": len(rows),
        "code_count": len(fetched_codes),
        "duplicate_date_code_count": duplicate_date_code_count,
        "raw_schema_status": raw_schema_status,
        "raw_schema_error_dates": sorted(set(raw_schema_errors)),
        "manifest_consistency_status": manifest_consistency_status,
        "secret_value_detected_in_reports": secret_in_reports,
        "secret_value_detected_in_manifests": secret_in_manifests,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "recommended_next_action": (
            "Phase4-AF Real Runtime Fetch Range Extension Plan: extend requested range until at least 60 fetched data dates are available."
            if not coverage_sufficient
            else "Phase4-AF Real Runtime Normalized Rebuild from Raw."
        ),
    }
    return _write_summary(summary_path, summary)


def _readiness_status(
    *,
    secret_in_manifests: bool,
    secret_in_reports: bool,
    manifest_consistency_status: str,
    raw_schema_status: str,
    coverage_sufficient: bool,
) -> str:
    if secret_in_manifests or secret_in_reports:
        return BLOCKED_SECRET
    if manifest_consistency_status != "OK":
        return BLOCKED_MANIFEST_MISMATCH
    if raw_schema_status != "OK":
        return BLOCKED_SCHEMA
    if not coverage_sufficient:
        return BLOCKED_COVERAGE
    return READY


def _blocked_summary(status: str, *, phase4ad: dict[str, Any] | None = None) -> dict[str, Any]:
    phase4ad = phase4ad or {}
    return {
        "status": "BLOCKED",
        "readiness_status": status,
        "api_call_performed": False,
        "fetch_executed": False,
        "additional_fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "raw_data_written": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ad_summary_detected": bool(phase4ad),
        "phase4ad_readiness_status": phase4ad.get("readiness_status"),
        "raw_manifest_detected": False,
        "raw_response_file_count": 0,
        "request_manifest_count": 0,
        "planned_request_count": int(phase4ad.get("planned_request_count") or 0),
        "completed_request_count": int(phase4ad.get("completed_request_count") or 0),
        "succeeded_request_count": int(phase4ad.get("succeeded_request_count") or 0),
        "failed_request_count": int(phase4ad.get("failed_request_count") or 0),
        "skipped_request_count": int(phase4ad.get("skipped_request_count") or 0),
        "pagination_request_count": int(phase4ad.get("pagination_request_count") or 0),
        "target_start_date": phase4ad.get("target_start_date"),
        "target_end_date": phase4ad.get("target_end_date"),
        "fetched_date_min": None,
        "fetched_date_max": None,
        "fetched_date_count": 0,
        "fetched_business_day_count": 0,
        "required_business_day_count": REQUIRED_BUSINESS_DAYS,
        "coverage_sufficient_for_features": False,
        "missing_business_day_count": REQUIRED_BUSINESS_DAYS,
        "empty_response_date_count": 0,
        "empty_response_dates": [],
        "fetched_dates": [],
        "missing_requested_dates": [],
        "required_business_dates": [],
        "row_count": 0,
        "code_count": 0,
        "duplicate_date_code_count": 0,
        "raw_schema_status": "UNKNOWN",
        "manifest_consistency_status": "UNKNOWN",
        "secret_value_detected_in_reports": False,
        "secret_value_detected_in_manifests": False,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "recommended_next_action": "Resolve the blocking condition before normalization.",
    }


def _duplicate_count(rows: list[dict[str, Any]]) -> int:
    counts = Counter((str(row.get("Date")), str(row.get("Code"))) for row in rows if row.get("Date") and row.get("Code"))
    return sum(count - 1 for count in counts.values() if count > 1)


def _output_path_safe(raw_root: Path) -> bool:
    text = str(raw_root)
    return "raw/jquants/equities_bars_daily" in text and "raw_normalized" not in text


def _has_secret_terms(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("Authorization", "x-api-key", "password", "cookie", "id_token", "refresh_token")
    return any(term in text for term in terms)


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_files(path: Path) -> list[dict[str, Any]]:
    if not path.is_dir():
        return []
    return [_read_json_optional(item) for item in sorted(path.glob("*.json"))]


def _write_summary(path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    _write_json(path, summary)
    return summary


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AE Post-fetch Raw Coverage Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Phase4-AE audits raw coverage only.",
            "- It does not call APIs, fetch, refetch, write normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "phase4ad_readiness_status",
        "planned_request_count",
        "completed_request_count",
        "raw_response_file_count",
        "request_manifest_count",
        "fetched_date_min",
        "fetched_date_max",
        "fetched_date_count",
        "fetched_business_day_count",
        "required_business_day_count",
        "coverage_sufficient_for_features",
        "missing_business_day_count",
        "empty_response_date_count",
        "row_count",
        "code_count",
        "duplicate_date_code_count",
        "raw_schema_status",
        "manifest_consistency_status",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


if __name__ == "__main__":
    raise SystemExit(main())
