#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PHASE4AB_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_summary.json")
REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_requests.json")

READY = "READY_FOR_CONTROLLED_REAL_RUNTIME_HISTORY_FETCH"
BLOCKED_MISSING_AB = "BLOCKED_BY_MISSING_PHASE4AB_SUMMARY"
BLOCKED_AB_NOT_READY = "BLOCKED_BY_PHASE4AB_NOT_READY"
BLOCKED_SEQUENCE_MISMATCH = "BLOCKED_BY_REQUEST_SEQUENCE_MISMATCH"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
BLOCKED_API_SAFETY = "BLOCKED_BY_API_SAFETY_RULE"
BLOCKED_ARTIFACT = "BLOCKED_BY_DRY_RUN_ARTIFACT"
ENDPOINT = "/v2/equities/bars/daily"
METHOD = "GET"
RATE_LIMIT_DELAY_SECONDS = 1


def main() -> int:
    summary = run_dry_run()
    _print_human_summary(summary)
    return 0 if summary["status"] == "OK" else 1


def run_dry_run(
    *,
    phase4ab_summary_path: Path = PHASE4AB_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    requests_path: Path = REQUESTS_PATH,
) -> dict[str, Any]:
    phase4ab = _read_json_optional(phase4ab_summary_path)
    if not phase4ab:
        summary = _blocked_summary(BLOCKED_MISSING_AB, phase4ab_summary_detected=False)
        _write_json(summary_path, summary)
        return summary
    if phase4ab.get("readiness_status") != "READY_FOR_NO_LIVE_FETCH_DRY_RUN_CLI":
        summary = _blocked_summary(
            BLOCKED_AB_NOT_READY,
            phase4ab_summary_detected=True,
            phase4ab=phase4ab,
        )
        _write_json(summary_path, summary)
        return summary
    if not _output_paths_safe(phase4ab):
        summary = _blocked_summary(
            BLOCKED_OUTPUT_PATH,
            phase4ab_summary_detected=True,
            phase4ab=phase4ab,
        )
        _write_json(summary_path, summary)
        return summary

    requests = _build_request_sequence(phase4ab)
    planned_request_count = int(phase4ab.get("planned_request_count") or 0)
    if len(requests) != planned_request_count:
        summary = _blocked_summary(
            BLOCKED_SEQUENCE_MISMATCH,
            phase4ab_summary_detected=True,
            phase4ab=phase4ab,
            generated_request_count=len(requests),
        )
        _write_json(summary_path, summary)
        return summary

    _write_json(requests_path, {"requests": requests, "pagination_placeholder": _pagination_placeholder(phase4ab)})
    if not requests_path.is_file():
        summary = _blocked_summary(
            BLOCKED_ARTIFACT,
            phase4ab_summary_detected=True,
            phase4ab=phase4ab,
            generated_request_count=len(requests),
        )
        _write_json(summary_path, summary)
        return summary

    summary = {
        "status": "OK",
        "readiness_status": READY,
        "api_call_performed": False,
        "fetch_executed": False,
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
        "phase4ab_summary_detected": True,
        "phase4ab_readiness_status": phase4ab.get("readiness_status"),
        "endpoint": phase4ab.get("endpoint") or ENDPOINT,
        "method": METHOD,
        "target_start_date": phase4ab.get("target_start_date"),
        "target_end_date": phase4ab.get("target_end_date"),
        "planned_request_count": planned_request_count,
        "generated_request_count": len(requests),
        "pagination_policy": phase4ab.get("pagination_policy"),
        "rate_limit_policy": phase4ab.get("rate_limit_policy"),
        "retry_policy": phase4ab.get("retry_policy"),
        "raw_output_path": phase4ab.get("raw_output_path"),
        "isolated_normalized_output_path": phase4ab.get("isolated_normalized_output_path"),
        "mock_path_will_be_unchanged": phase4ab.get("mock_path_will_be_unchanged") is True,
        "dry_run_requests_path": str(requests_path),
        "request_sequence_generated": True,
        "manifest_provenance_plan_carried_forward": phase4ab.get("manifest_provenance_required") is True,
        "post_fetch_raw_audit_defined": phase4ab.get("post_fetch_raw_audit_defined") is True,
        "post_normalize_coverage_audit_defined": phase4ab.get("post_normalize_coverage_audit_defined") is True,
        "promotion_gate_carried_forward": phase4ab.get("promotion_gate_defined") is True,
        "reader_switch_gate_carried_forward": phase4ab.get("reader_switch_gate_defined") is True,
        "rollback_plan_carried_forward": phase4ab.get("rollback_plan_defined") is True,
        "promotion_status": "not_promoted",
        "recommended_next_action": "Phase4-AD Controlled Real Runtime History Fetch may proceed only after explicit approval and sanitized live-fetch controls.",
    }
    if not _api_safety_ok(summary):
        summary["status"] = "BLOCKED"
        summary["readiness_status"] = BLOCKED_API_SAFETY
    _write_json(summary_path, summary)
    return summary


def _build_request_sequence(phase4ab: dict[str, Any]) -> list[dict[str, Any]]:
    dates = list(phase4ab.get("missing_business_day_list") or [])
    endpoint = str(phase4ab.get("endpoint") or ENDPOINT)
    raw_output_path = str(phase4ab.get("raw_output_path") or "")
    requests: list[dict[str, Any]] = []
    for index, target_date in enumerate(dates, start=1):
        params = {"date": str(target_date), "code": None, "pagination_key": None}
        requests.append(
            {
                "request_index": index,
                "endpoint": endpoint,
                "method": METHOD,
                "date": str(target_date),
                "code": None,
                "pagination_key": None,
                "params": params,
                "planned_raw_output_path": raw_output_path,
                "expected_rate_limit_delay_seconds": RATE_LIMIT_DELAY_SECONDS,
                "pagination_placeholder": "additional pages are discovered only during controlled fetch",
                "no_live": True,
                "api_call_performed": False,
                "fetch_executed": False,
            }
        )
    return requests


def _pagination_placeholder(phase4ab: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy": phase4ab.get("pagination_policy"),
        "initial_pagination_key": None,
        "additional_requests_known_in_dry_run": False,
        "max_pages_policy": phase4ab.get("max_pages_policy"),
    }


def _blocked_summary(
    readiness_status: str,
    *,
    phase4ab_summary_detected: bool,
    phase4ab: dict[str, Any] | None = None,
    generated_request_count: int = 0,
) -> dict[str, Any]:
    phase4ab = phase4ab or {}
    return {
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "fetch_executed": False,
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
        "phase4ab_summary_detected": phase4ab_summary_detected,
        "phase4ab_readiness_status": phase4ab.get("readiness_status"),
        "endpoint": phase4ab.get("endpoint") or ENDPOINT,
        "method": METHOD,
        "target_start_date": phase4ab.get("target_start_date"),
        "target_end_date": phase4ab.get("target_end_date"),
        "planned_request_count": int(phase4ab.get("planned_request_count") or 0),
        "generated_request_count": generated_request_count,
        "pagination_policy": phase4ab.get("pagination_policy"),
        "rate_limit_policy": phase4ab.get("rate_limit_policy"),
        "retry_policy": phase4ab.get("retry_policy"),
        "raw_output_path": phase4ab.get("raw_output_path"),
        "isolated_normalized_output_path": phase4ab.get("isolated_normalized_output_path"),
        "mock_path_will_be_unchanged": phase4ab.get("mock_path_will_be_unchanged") is True,
        "dry_run_requests_path": str(REQUESTS_PATH),
        "request_sequence_generated": False,
        "manifest_provenance_plan_carried_forward": False,
        "post_fetch_raw_audit_defined": False,
        "post_normalize_coverage_audit_defined": False,
        "promotion_gate_carried_forward": False,
        "reader_switch_gate_carried_forward": False,
        "rollback_plan_carried_forward": False,
        "promotion_status": "not_promoted",
        "recommended_next_action": "Resolve the blocking condition before Phase4-AD.",
    }


def _output_paths_safe(phase4ab: dict[str, Any]) -> bool:
    raw = phase4ab.get("raw_output_path")
    isolated = phase4ab.get("isolated_normalized_output_path")
    mock_unchanged = phase4ab.get("mock_path_will_be_unchanged") is True
    return (
        raw == ".runtime/data/raw/jquants/equities_bars_daily/"
        and isolated == ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/"
        and mock_unchanged
    )


def _api_safety_ok(summary: dict[str, Any]) -> bool:
    return (
        summary.get("api_call_performed") is False
        and summary.get("fetch_executed") is False
        and summary.get("credential_read_performed") is False
        and summary.get("http_client_initialized") is False
    )


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_human_summary(summary: dict[str, Any]) -> None:
    print("Phase4-AC no-live dry-run")
    print(f"status={summary.get('status')}")
    print(f"readiness_status={summary.get('readiness_status')}")
    print(f"target_date_range={summary.get('target_start_date')}..{summary.get('target_end_date')}")
    print(f"planned_request_count={summary.get('planned_request_count')}")
    print(f"generated_request_count={summary.get('generated_request_count')}")
    print(f"dry_run_requests_path={summary.get('dry_run_requests_path')}")
    print("api_call_performed=false")
    print("fetch_executed=false")


if __name__ == "__main__":
    raise SystemExit(main())
