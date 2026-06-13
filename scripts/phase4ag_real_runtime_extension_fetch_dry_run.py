#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PHASE4AF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4af_trading_calendar_correction_fetch_extension_plan_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_summary.json")
REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_requests.json")

READY = "READY_FOR_CONTROLLED_EXTENSION_FETCH"
BLOCKED_MISSING_AF = "BLOCKED_BY_MISSING_PHASE4AF_SUMMARY"
BLOCKED_AF_NOT_READY = "BLOCKED_BY_PHASE4AF_NOT_READY"
BLOCKED_EXTENSION_NOT_REQUIRED = "BLOCKED_BY_EXTENSION_NOT_REQUIRED"
BLOCKED_SEQUENCE_MISMATCH = "BLOCKED_BY_EXTENSION_REQUEST_SEQUENCE_MISMATCH"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
BLOCKED_API_SAFETY = "BLOCKED_BY_API_SAFETY_RULE"
BLOCKED_ARTIFACT = "BLOCKED_BY_DRY_RUN_ARTIFACT"

ENDPOINT = "/v2/equities/bars/daily"
METHOD = "GET"
RATE_LIMIT_DELAY_SECONDS = 1
RAW_OUTPUT_PATH = ".runtime/data/raw/jquants/equities_bars_daily/"


def main() -> int:
    summary = run_dry_run()
    _print_human_summary(summary)
    return 0 if summary["status"] == "OK" else 1


def run_dry_run(
    *,
    phase4af_summary_path: Path = PHASE4AF_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    requests_path: Path = REQUESTS_PATH,
) -> dict[str, Any]:
    phase4af = _read_json_optional(phase4af_summary_path)
    if not phase4af:
        summary = _blocked_summary(BLOCKED_MISSING_AF, phase4af_summary_detected=False)
        _write_json(summary_path, summary)
        return summary
    if phase4af.get("readiness_status") != "READY_FOR_EXTENSION_FETCH_DRY_RUN":
        summary = _blocked_summary(BLOCKED_AF_NOT_READY, phase4af_summary_detected=True, phase4af=phase4af)
        _write_json(summary_path, summary)
        return summary
    if phase4af.get("extension_fetch_required") is not True:
        summary = _blocked_summary(BLOCKED_EXTENSION_NOT_REQUIRED, phase4af_summary_detected=True, phase4af=phase4af)
        _write_json(summary_path, summary)
        return summary
    if not _output_paths_safe():
        summary = _blocked_summary(BLOCKED_OUTPUT_PATH, phase4af_summary_detected=True, phase4af=phase4af)
        _write_json(summary_path, summary)
        return summary

    requests = _build_request_sequence(phase4af)
    extension_request_count = int(phase4af.get("extension_request_count") or 0)
    if len(requests) != extension_request_count:
        summary = _blocked_summary(
            BLOCKED_SEQUENCE_MISMATCH,
            phase4af_summary_detected=True,
            phase4af=phase4af,
            generated_extension_request_count=len(requests),
        )
        _write_json(summary_path, summary)
        return summary

    artifact = {
        "phase": "Phase4-AG",
        "source_summary_path": str(phase4af_summary_path),
        "endpoint": ENDPOINT,
        "method": METHOD,
        "extension_fetch_start_date": phase4af.get("extension_fetch_start_date"),
        "extension_fetch_end_date": phase4af.get("extension_fetch_end_date"),
        "extension_request_count": extension_request_count,
        "requests": requests,
        "pagination_placeholder": {
            "initial_pagination_key": None,
            "additional_requests_known_in_dry_run": False,
            "policy": "Controlled extension fetch follows pagination keys returned by each live response with a bounded max_pages guard.",
        },
        "merge_policy": _merge_policy(),
    }
    _write_json(requests_path, artifact)
    if not requests_path.is_file():
        summary = _blocked_summary(
            BLOCKED_ARTIFACT,
            phase4af_summary_detected=True,
            phase4af=phase4af,
            generated_extension_request_count=len(requests),
        )
        _write_json(summary_path, summary)
        return summary

    summary = {
        "status": "OK",
        "readiness_status": READY,
        "api_call_performed": False,
        "extension_fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "raw_data_written": False,
        "raw_manifest_updated": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "phase4af_summary_detected": True,
        "phase4af_readiness_status": phase4af.get("readiness_status"),
        "extension_fetch_required": phase4af.get("extension_fetch_required") is True,
        "extension_fetch_start_date": phase4af.get("extension_fetch_start_date"),
        "extension_fetch_end_date": phase4af.get("extension_fetch_end_date"),
        "extension_requested_dates": list(phase4af.get("extension_requested_dates") or []),
        "extension_request_count": extension_request_count,
        "generated_extension_request_count": len(requests),
        "endpoint": ENDPOINT,
        "method": METHOD,
        "pagination_policy": artifact["pagination_placeholder"]["policy"],
        "rate_limit_policy": "Respect J-Quants Light plan 60 req/min; schedule at most one request per second with no burst.",
        "retry_policy": "Controlled extension fetch may retry transient timeout/5xx/429 with bounded sanitized handling; dry-run performs no retry.",
        "planned_raw_output_path": RAW_OUTPUT_PATH,
        "existing_raw_preserved": True,
        "existing_success_manifest_preserved": True,
        "merge_policy_defined": True,
        "merge_policy": _merge_policy(),
        "dry_run_requests_path": str(requests_path),
        "request_sequence_generated": True,
        "expected_non_empty_trading_day_count_after_extension": phase4af.get(
            "expected_non_empty_trading_day_count_after_extension"
        ),
        "recommended_next_action": "Phase4-AH Controlled Extension Fetch: fetch only the extension_requested_dates and preserve existing raw artifacts.",
    }
    if not _api_safety_ok(summary):
        summary["status"] = "BLOCKED"
        summary["readiness_status"] = BLOCKED_API_SAFETY
    _write_json(summary_path, summary)
    return summary


def _build_request_sequence(phase4af: dict[str, Any]) -> list[dict[str, Any]]:
    dates = [str(day) for day in phase4af.get("extension_requested_dates") or []]
    requests: list[dict[str, Any]] = []
    for index, target_date in enumerate(dates, start=1):
        params = {"date": target_date, "code": None, "pagination_key": None}
        requests.append(
            {
                "request_index": index,
                "extension_request_index": index,
                "endpoint": ENDPOINT,
                "method": METHOD,
                "date": target_date,
                "code": None,
                "pagination_key": None,
                "params": params,
                "planned_raw_output_path": RAW_OUTPUT_PATH,
                "expected_rate_limit_delay_seconds": RATE_LIMIT_DELAY_SECONDS,
                "merge_mode": "append_new_date_or_skip_existing_success",
                "existing_raw_preserved": True,
                "existing_success_manifest_preserved": True,
                "pagination_placeholder": "additional pages are discovered only during controlled extension fetch",
                "no_live": True,
                "api_call_performed": False,
                "fetch_executed": False,
                "credential_read_performed": False,
                "http_client_initialized": False,
                "raw_data_written": False,
            }
        )
    return requests


def _merge_policy() -> dict[str, Any]:
    return {
        "existing_raw_response_files_deleted": False,
        "existing_request_manifests_deleted": False,
        "existing_success_manifest_preserved": True,
        "extension_dates_only": True,
        "existing_success_same_date_action": "skip",
        "existing_failed_same_date_action": "rerun_candidate",
        "raw_manifest_update_phase": "Phase4-AH Controlled Extension Fetch",
        "normalized_rebuild_phase": "after post-extension raw audit",
    }


def _blocked_summary(
    readiness_status: str,
    *,
    phase4af_summary_detected: bool,
    phase4af: dict[str, Any] | None = None,
    generated_extension_request_count: int = 0,
) -> dict[str, Any]:
    phase4af = phase4af or {}
    return {
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "extension_fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "raw_data_written": False,
        "raw_manifest_updated": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "phase4af_summary_detected": phase4af_summary_detected,
        "phase4af_readiness_status": phase4af.get("readiness_status"),
        "extension_fetch_required": phase4af.get("extension_fetch_required") is True,
        "extension_fetch_start_date": phase4af.get("extension_fetch_start_date"),
        "extension_fetch_end_date": phase4af.get("extension_fetch_end_date"),
        "extension_requested_dates": list(phase4af.get("extension_requested_dates") or []),
        "extension_request_count": int(phase4af.get("extension_request_count") or 0),
        "generated_extension_request_count": generated_extension_request_count,
        "endpoint": ENDPOINT,
        "method": METHOD,
        "pagination_policy": None,
        "rate_limit_policy": None,
        "retry_policy": None,
        "planned_raw_output_path": RAW_OUTPUT_PATH,
        "existing_raw_preserved": True,
        "existing_success_manifest_preserved": True,
        "merge_policy_defined": False,
        "dry_run_requests_path": str(REQUESTS_PATH),
        "request_sequence_generated": False,
        "expected_non_empty_trading_day_count_after_extension": phase4af.get(
            "expected_non_empty_trading_day_count_after_extension"
        ),
        "recommended_next_action": "Resolve the blocking condition before Phase4-AH.",
    }


def _output_paths_safe() -> bool:
    return "raw/jquants/equities_bars_daily" in RAW_OUTPUT_PATH and "raw_normalized" not in RAW_OUTPUT_PATH


def _api_safety_ok(summary: dict[str, Any]) -> bool:
    return (
        summary.get("api_call_performed") is False
        and summary.get("extension_fetch_executed") is False
        and summary.get("credential_read_performed") is False
        and summary.get("http_client_initialized") is False
        and summary.get("raw_data_written") is False
        and summary.get("raw_manifest_updated") is False
    )


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_human_summary(summary: dict[str, Any]) -> None:
    print("Phase4-AG extension fetch no-live dry-run")
    print(f"status={summary.get('status')}")
    print(f"readiness_status={summary.get('readiness_status')}")
    print(f"extension_date_range={summary.get('extension_fetch_start_date')}..{summary.get('extension_fetch_end_date')}")
    print(f"extension_request_count={summary.get('extension_request_count')}")
    print(f"generated_extension_request_count={summary.get('generated_extension_request_count')}")
    print(f"dry_run_requests_path={summary.get('dry_run_requests_path')}")
    print("api_call_performed=false")
    print("extension_fetch_executed=false")
    print("credential_read_performed=false")
    print("raw_data_written=false")


if __name__ == "__main__":
    raise SystemExit(main())
