#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend  # noqa: E402

PHASE4AA_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.md")

READY = "READY_FOR_NO_LIVE_FETCH_DRY_RUN_CLI"
BLOCKED_MISSING_AA = "BLOCKED_BY_MISSING_PHASE4AA_SUMMARY"
BLOCKED_MISSING_ISOLATED = "BLOCKED_BY_MISSING_ISOLATED_REAL_RUNTIME"
BLOCKED_PROVENANCE = "BLOCKED_BY_UNKNOWN_PROVENANCE"
BLOCKED_CALENDAR = "BLOCKED_BY_TRADING_CALENDAR"
BLOCKED_API_SAFETY = "BLOCKED_BY_API_SAFETY_RULE"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
REQUIRED_BUSINESS_DAYS = 60
ENDPOINT = "/v2/equities/bars/daily"


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    phase4aa_summary_path: Path = PHASE4AA_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_no_live_fetch_plan_summary(
        runtime_dir=runtime_dir,
        phase4aa_summary_path=phase4aa_summary_path,
        summary_path=summary_path,
    )
    checks = {
        "summary_exists": summary_path.is_file(),
        "api_call_not_performed": summary.get("api_call_performed") is False,
        "fetch_not_executed": summary.get("fetch_executed") is False,
        "promotion_not_performed": summary.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False,
        "feature_generation_not_executed": summary.get("feature_generation_executed") is False,
        "label_generation_not_executed": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_executed": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "isolated_real_runtime_detected": summary.get("isolated_real_runtime_detected") is True,
        "target_date_range_defined": bool(summary.get("target_start_date")) and bool(summary.get("target_end_date")),
        "target_business_day_list_defined": len(summary.get("target_business_day_list") or []) >= REQUIRED_BUSINESS_DAYS,
        "missing_business_day_list_defined": len(summary.get("missing_business_day_list") or []) == int(
            summary.get("missing_business_day_count") or 0
        ),
        "endpoint_request_plan_defined": summary.get("endpoint") == ENDPOINT
        and isinstance(summary.get("endpoint_params_template"), dict),
        "request_count_estimate_defined": int(summary.get("planned_request_count") or 0) >= 1,
        "pagination_policy_defined": bool(summary.get("pagination_policy")),
        "max_pages_policy_defined": bool(summary.get("max_pages_policy")),
        "rate_limit_policy_defined": bool(summary.get("rate_limit_policy")),
        "retry_policy_defined": bool(summary.get("retry_policy")),
        "output_paths_safe": summary.get("raw_output_path") == ".runtime/data/raw/jquants/equities_bars_daily/"
        and summary.get("isolated_normalized_output_path")
        == ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/"
        and summary.get("mock_path_will_be_unchanged") is True,
        "manifest_provenance_required": summary.get("manifest_provenance_required") is True,
        "api_credential_safety_defined": summary.get("api_credential_safety_defined") is True,
        "post_fetch_raw_audit_defined": summary.get("post_fetch_raw_audit_defined") is True,
        "post_normalize_coverage_audit_defined": summary.get("post_normalize_coverage_audit_defined") is True,
        "promotion_gate_defined": summary.get("promotion_gate_defined") is True,
        "reader_switch_gate_defined": summary.get("reader_switch_gate_defined") is True,
        "rollback_plan_defined": summary.get("rollback_plan_defined") is True,
        "readiness_status_ready": summary.get("readiness_status") == READY,
        "secret_terms_not_emitted": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-AB",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ab_no_live_real_runtime_fetch_plan.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_no_live_fetch_plan_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    phase4aa_summary_path: Path = PHASE4AA_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    phase4aa = _read_json_optional(phase4aa_summary_path)
    if not phase4aa:
        summary = _blocked_summary(BLOCKED_MISSING_AA)
        _write_json(summary_path, summary)
        return summary

    isolated_path = str(phase4aa.get("isolated_path") or "")
    isolated_detected = phase4aa.get("isolated_real_runtime_detected") is True and Path(isolated_path).is_file()
    if not isolated_detected:
        summary = _blocked_summary(BLOCKED_MISSING_ISOLATED, phase4aa=phase4aa)
        _write_json(summary_path, summary)
        return summary

    if phase4aa.get("readiness_status") != "READY_FOR_REAL_RUNTIME_HISTORY_FETCH_PLAN":
        summary = _blocked_summary(BLOCKED_PROVENANCE, phase4aa=phase4aa)
        _write_json(summary_path, summary)
        return summary

    output_paths_safe = _output_paths_are_safe()
    if not output_paths_safe:
        summary = _blocked_summary(BLOCKED_OUTPUT_PATH, phase4aa=phase4aa)
        _write_json(summary_path, summary)
        return summary

    business_days = _load_business_days(runtime_dir=runtime_dir, target_end_date=str(phase4aa.get("fetch_range_end") or ""))
    if len(business_days) < REQUIRED_BUSINESS_DAYS:
        summary = _blocked_summary(BLOCKED_CALENDAR, phase4aa=phase4aa)
        summary["calendar_business_day_count"] = len(business_days)
        _write_json(summary_path, summary)
        return summary

    target_business_day_list = business_days[-REQUIRED_BUSINESS_DAYS:]
    current_dates = {str(phase4aa.get("current_date_max") or phase4aa.get("date_max") or "")}
    missing_business_day_list = [day for day in target_business_day_list if day not in current_dates]
    target_start_date = target_business_day_list[0]
    target_end_date = target_business_day_list[-1]
    planned_request_count = len(missing_business_day_list)

    summary = {
        "status": "OK",
        "readiness_status": READY,
        "api_call_performed": False,
        "fetch_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "isolated_real_runtime_detected": True,
        "isolated_path": isolated_path,
        "current_row_count": int(phase4aa.get("row_count") or 0),
        "current_code_count": int(phase4aa.get("code_count") or 0),
        "current_date_min": phase4aa.get("date_min"),
        "current_date_max": phase4aa.get("date_max"),
        "current_business_day_count": int(phase4aa.get("business_day_count") or 0),
        "required_business_day_count": REQUIRED_BUSINESS_DAYS,
        "missing_business_day_count": len(missing_business_day_list),
        "target_start_date": target_start_date,
        "target_end_date": target_end_date,
        "target_business_day_list": target_business_day_list,
        "missing_business_day_list": missing_business_day_list,
        "planned_fetch_business_day_count": len(missing_business_day_list),
        "planned_request_count": planned_request_count,
        "endpoint": ENDPOINT,
        "endpoint_params_template": {
            "date": "<YYYY-MM-DD from missing_business_day_list>",
            "code": None,
            "pagination_key": "<optional next pagination key>",
        },
        "no_live_request_plan": [
            {"endpoint": ENDPOINT, "params": {"date": day, "code": None, "pagination_key": None}}
            for day in missing_business_day_list
        ],
        "pagination_policy": "For each date, request the first page and continue while the response returns a next pagination key.",
        "max_pages_policy": "Use a configurable max_pages guard; initial dry-run CLI default should be 1 and controlled live fetch must set an explicit cap.",
        "rate_limit_policy": "Respect J-Quants Light plan 60 req/min; schedule at most 1 request per second with no burst.",
        "retry_policy": "Retry only transient timeout/5xx/429 with bounded exponential backoff and sanitized errors; never retry auth failures blindly.",
        "raw_output_path": ".runtime/data/raw/jquants/equities_bars_daily/",
        "isolated_normalized_output_path": ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/",
        "mock_normalized_path": ".runtime/data/raw_normalized/jquants/equities_bars_daily/",
        "mock_path_will_be_unchanged": True,
        "manifest_provenance_required": True,
        "manifest_required_fields": [
            "data_source_type",
            "source_provider",
            "api_call_performed",
            "source_raw_path",
            "source_raw_manifest_path",
            "fetch_range_start",
            "fetch_range_end",
            "normalizer_version",
            "schema_version",
            "row_count",
            "code_count",
            "date_min",
            "date_max",
            "input_hash_optional",
            "output_hash_optional",
            "promotion_status",
        ],
        "api_credential_safety_defined": True,
        "api_credential_safety_rule": "Credentials must come from env or .env in a future fetch phase; Phase4-AB does not check or print them.",
        "post_fetch_raw_audit_defined": True,
        "post_fetch_raw_audit_condition": "Raw audit must confirm each missing business day has raw records or a documented market/calendar reason.",
        "post_normalize_coverage_audit_defined": True,
        "post_normalize_coverage_audit_condition": "Normalized audit must confirm business_day_count >= 60, schema validation OK, leakage audit OK, and provenance OK.",
        "promotion_gate_defined": True,
        "promotion_gate": "Keep promotion_status=not_promoted until coverage/schema/provenance audits pass and a human explicitly approves promotion.",
        "reader_switch_gate_defined": True,
        "reader_switch_gate": "Reader switch is forbidden until promotion_status=approved and Operation/Safety review accepts the source.",
        "rollback_plan_defined": True,
        "rollback_plan": "Before reader switch, delete or quarantine only isolated real_runtime outputs; mock normalized path remains intact.",
        "recommended_next_action": "Phase4-AC Real Runtime History Fetch Dry-run CLI: render this request plan without calling J-Quants.",
    }
    if not summary["api_credential_safety_defined"]:
        summary["readiness_status"] = BLOCKED_API_SAFETY
        summary["status"] = "BLOCKED"
    _write_json(summary_path, summary)
    return summary


def _blocked_summary(status: str, *, phase4aa: dict[str, Any] | None = None) -> dict[str, Any]:
    phase4aa = phase4aa or {}
    return {
        "status": "BLOCKED",
        "readiness_status": status,
        "api_call_performed": False,
        "fetch_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "isolated_real_runtime_detected": phase4aa.get("isolated_real_runtime_detected") is True,
        "isolated_path": phase4aa.get("isolated_path"),
        "current_row_count": int(phase4aa.get("row_count") or 0),
        "current_code_count": int(phase4aa.get("code_count") or 0),
        "current_date_min": phase4aa.get("date_min"),
        "current_date_max": phase4aa.get("date_max"),
        "current_business_day_count": int(phase4aa.get("business_day_count") or 0),
        "required_business_day_count": REQUIRED_BUSINESS_DAYS,
        "missing_business_day_count": int(phase4aa.get("missing_business_day_count") or 0),
        "target_start_date": None,
        "target_end_date": phase4aa.get("fetch_range_end"),
        "target_business_day_list": [],
        "missing_business_day_list": [],
        "planned_fetch_business_day_count": 0,
        "planned_request_count": 0,
        "endpoint": ENDPOINT,
        "endpoint_params_template": {},
        "pagination_policy": "",
        "max_pages_policy": "",
        "rate_limit_policy": "",
        "retry_policy": "",
        "raw_output_path": ".runtime/data/raw/jquants/equities_bars_daily/",
        "isolated_normalized_output_path": ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/",
        "mock_path_will_be_unchanged": True,
        "manifest_provenance_required": False,
        "api_credential_safety_defined": False,
        "post_fetch_raw_audit_defined": False,
        "post_normalize_coverage_audit_defined": False,
        "promotion_gate_defined": False,
        "reader_switch_gate_defined": False,
        "rollback_plan_defined": False,
        "recommended_next_action": "Resolve the blocking condition before Phase4-AC.",
    }


def _load_business_days(*, runtime_dir: Path | str, target_end_date: str) -> list[str]:
    base = Path(runtime_dir) / "data" / "raw" / "jquants" / "trading_calendar" / "data"
    records: list[dict[str, Any]] = []
    for storage_format in ("parquet", "jsonl"):
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base)
        if not path.exists():
            continue
        try:
            records = backend.read_records(path)
            break
        except (StorageBackendError, ImportError, RuntimeError):
            continue
    days = {
        str(record.get("Date") or record.get("target_date"))
        for record in records
        if str(record.get("HolDiv") or record.get("HolidayDivision") or "") == "1"
        and str(record.get("Date") or record.get("target_date") or "") <= target_end_date
    }
    return sorted(day for day in days if day)


def _output_paths_are_safe() -> bool:
    raw = ".runtime/data/raw/jquants/equities_bars_daily/"
    isolated = ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/"
    mock = ".runtime/data/raw_normalized/jquants/equities_bars_daily/"
    return raw != isolated and isolated != mock and "raw_normalized_real_runtime" in isolated


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "api_call_performed",
        "fetch_executed",
        "isolated_real_runtime_detected",
        "current_row_count",
        "current_code_count",
        "current_date_min",
        "current_date_max",
        "current_business_day_count",
        "required_business_day_count",
        "missing_business_day_count",
        "target_start_date",
        "target_end_date",
        "planned_fetch_business_day_count",
        "planned_request_count",
        "endpoint",
        "raw_output_path",
        "isolated_normalized_output_path",
        "mock_path_will_be_unchanged",
        "promotion_gate_defined",
        "reader_switch_gate_defined",
        "rollback_plan_defined",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AB No-live Real Runtime History Fetch Plan Audit",
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
            "- Phase4-AB is a no-live plan and audit only.",
            "- It does not call J-Quants APIs, execute fetches, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "secret", "http://", "https://")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
