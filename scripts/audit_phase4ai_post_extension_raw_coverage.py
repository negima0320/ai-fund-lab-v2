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

PHASE4AH_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ah_controlled_extension_fetch_summary.json")
RAW_ROOT = Path(".runtime/data/raw/jquants/equities_bars_daily")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ai_post_extension_raw_coverage_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4ai_post_extension_raw_coverage_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ai_post_extension_raw_coverage_audit.md")

READY = "READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD"
BLOCKED_COVERAGE = "BLOCKED_BY_COVERAGE_GAP"
BLOCKED_INTEGRITY = "BLOCKED_BY_RAW_INTEGRITY"
BLOCKED_SECRET = "BLOCKED_BY_SECRET_LEAK"
REQUIRED_NON_EMPTY_TRADING_DAYS = 60
REQUIRED_ROW_COLUMNS = {"Date", "Code"}
SECRET_MARKERS = ("Authorization", "x-api-key", "password", "cookie", "id_token", "refresh_token")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    phase4ah_summary_path: Path = PHASE4AH_SUMMARY_PATH,
    raw_root: Path = RAW_ROOT,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah_summary_path,
        raw_root=raw_root,
        summary_path=summary_path,
    )
    checks = {
        "summary_exists": summary_path.is_file(),
        "phase4ah_summary_detected": summary.get("phase4ah_summary_detected") is True,
        "phase4ah_ready": summary.get("phase4ah_readiness_status") == "READY_FOR_POST_EXTENSION_RAW_COVERAGE_AUDIT",
        "coverage_decision_produced": summary.get("readiness_status") in {READY, BLOCKED_COVERAGE, BLOCKED_INTEGRITY, BLOCKED_SECRET},
        "raw_schema_checked": summary.get("raw_schema_status") in {"OK", "ERROR"},
        "manifest_consistency_checked": summary.get("manifest_consistency_status") in {"OK", "ERROR"},
        "coverage_sufficient_when_ready": (
            summary.get("readiness_status") != READY
            or summary.get("coverage_sufficient_for_features") is True
        ),
        "normalized_not_executed": summary.get("normalized_data_written") is False
        and summary.get("normalized_output_written") is False
        and summary.get("isolated_normalized_path_written") is False,
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
        "phase": "Phase4-AI",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ai_post_extension_raw_coverage.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_post_extension_raw_coverage_summary(
    *,
    phase4ah_summary_path: Path = PHASE4AH_SUMMARY_PATH,
    raw_root: Path = RAW_ROOT,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    phase4ah = _read_json_optional(phase4ah_summary_path)
    run_manifest_path = raw_root / "manifest.json"
    response_paths = sorted((raw_root / "responses").glob("*.json"))
    request_manifests = _read_json_files(raw_root / "request_manifests")
    run_manifest = _read_json_optional(run_manifest_path)

    rows: list[dict[str, Any]] = []
    empty_response_dates: list[str] = []
    response_dates: set[str] = set()
    raw_schema_errors: list[str] = []
    for response_path in response_paths:
        response = _read_json_optional(response_path)
        response_date = str(response.get("date") or response.get("params", {}).get("date") or response_path.name.split("_page_")[0])
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
    request_manifest_dates = {
        str(record.get("target_date") or record.get("request_params", {}).get("date"))
        for record in request_manifests
        if record
    }
    success_manifest_dates = {
        str(record.get("target_date") or record.get("request_params", {}).get("date"))
        for record in request_manifests
        if record.get("status") == "SUCCESS"
    }
    failed_manifest_dates = sorted(
        str(record.get("target_date") or record.get("request_params", {}).get("date"))
        for record in request_manifests
        if record.get("status") == "FAILED"
    )

    raw_schema_status = "OK" if not raw_schema_errors else "ERROR"
    manifest_consistency_status = "OK"
    manifest_warnings: list[str] = []
    if not run_manifest_path.is_file() or not response_paths or not request_manifests:
        manifest_consistency_status = "ERROR"
    if request_manifest_dates != response_dates:
        manifest_consistency_status = "ERROR"
        manifest_warnings.append("request_manifest_dates and response_dates differ")
    if success_manifest_dates != request_manifest_dates:
        manifest_consistency_status = "ERROR"
        manifest_warnings.append("not all request manifests are SUCCESS")
    completed_count = int(run_manifest.get("completed_request_count") or 0)
    if completed_count and completed_count != len(request_manifests):
        manifest_consistency_status = "ERROR"
        manifest_warnings.append("run manifest completed_request_count differs from request manifest count")
    planned_count = int(run_manifest.get("planned_request_count") or 0)
    if planned_count and planned_count != len(request_manifests):
        manifest_warnings.append("run manifest planned_request_count includes historical attempts and differs from current file count")

    secret_in_manifests = _has_secret_terms({"run_manifest": run_manifest, "request_manifests": request_manifests})
    secret_in_reports = _has_secret_terms({"phase4ah": phase4ah})
    coverage_sufficient = len(fetched_dates) >= REQUIRED_NON_EMPTY_TRADING_DAYS
    readiness_status = _readiness_status(
        secret_detected=secret_in_manifests or secret_in_reports,
        manifest_consistency_status=manifest_consistency_status,
        raw_schema_status=raw_schema_status,
        coverage_sufficient=coverage_sufficient,
    )
    summary = {
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ah_summary_detected": bool(phase4ah),
        "phase4ah_readiness_status": phase4ah.get("readiness_status"),
        "raw_manifest_detected": run_manifest_path.is_file(),
        "raw_manifest_path": str(run_manifest_path),
        "request_manifest_count": len(request_manifests),
        "raw_response_file_count": len(response_paths),
        "run_manifest_planned_request_count": planned_count,
        "run_manifest_completed_request_count": completed_count,
        "failed_manifest_dates": failed_manifest_dates,
        "fetched_non_empty_trading_day_count": len(fetched_dates),
        "required_non_empty_trading_day_count": REQUIRED_NON_EMPTY_TRADING_DAYS,
        "coverage_sufficient_for_features": coverage_sufficient,
        "missing_non_empty_trading_day_count": max(0, REQUIRED_NON_EMPTY_TRADING_DAYS - len(fetched_dates)),
        "date_min": fetched_dates[0] if fetched_dates else None,
        "date_max": fetched_dates[-1] if fetched_dates else None,
        "row_count": len(rows),
        "code_count": len(fetched_codes),
        "duplicate_date_code_count": duplicate_date_code_count,
        "empty_response_date_count": len(empty_response_dates),
        "empty_response_dates": sorted(empty_response_dates),
        "raw_schema_status": raw_schema_status,
        "raw_schema_error_dates": sorted(set(raw_schema_errors)),
        "manifest_consistency_status": manifest_consistency_status,
        "manifest_warnings": manifest_warnings,
        "secret_value_detected_in_reports": secret_in_reports,
        "secret_value_detected_in_manifests": secret_in_manifests,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "recommended_next_action": (
            "Phase4-AJ Real Runtime Normalized Rebuild from Raw."
            if readiness_status == READY
            else "Resolve raw coverage or integrity blocking condition before Phase4-AJ."
        ),
    }
    return _write_summary(summary_path, summary)


def _readiness_status(
    *,
    secret_detected: bool,
    manifest_consistency_status: str,
    raw_schema_status: str,
    coverage_sufficient: bool,
) -> str:
    if secret_detected:
        return BLOCKED_SECRET
    if manifest_consistency_status != "OK" or raw_schema_status != "OK":
        return BLOCKED_INTEGRITY
    if not coverage_sufficient:
        return BLOCKED_COVERAGE
    return READY


def _duplicate_count(rows: list[dict[str, Any]]) -> int:
    counts = Counter((str(row.get("Date")), str(row.get("Code"))) for row in rows if row.get("Date") and row.get("Code"))
    return sum(count - 1 for count in counts.values() if count > 1)


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "phase4ah_readiness_status",
        "fetched_non_empty_trading_day_count",
        "required_non_empty_trading_day_count",
        "coverage_sufficient_for_features",
        "row_count",
        "code_count",
        "date_min",
        "date_max",
        "duplicate_date_code_count",
        "raw_schema_status",
        "manifest_consistency_status",
        "request_manifest_count",
        "raw_response_file_count",
        "run_manifest_planned_request_count",
        "run_manifest_completed_request_count",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


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
        "# Phase4-AI Post-extension Raw Coverage Audit",
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
            "- Phase4-AI is post-extension raw coverage audit only.",
            "- It does not call APIs, fetch, rebuild normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _has_secret_terms(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return any(marker in text for marker in SECRET_MARKERS)


if __name__ == "__main__":
    raise SystemExit(main())
