#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase4ag_real_runtime_extension_fetch_dry_run import (  # noqa: E402
    READY,
    REQUESTS_PATH,
    SUMMARY_PATH,
    run_dry_run,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4ag_real_runtime_extension_fetch_dry_run_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ag_real_runtime_extension_fetch_dry_run_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    summary_path: Path = SUMMARY_PATH,
    requests_path: Path = REQUESTS_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = _read_json_optional(summary_path)
    if not summary or not requests_path.is_file():
        summary = run_dry_run(summary_path=summary_path, requests_path=requests_path)
    artifact = _read_json_optional(requests_path)
    requests = artifact.get("requests") if isinstance(artifact.get("requests"), list) else []
    checks = {
        "summary_exists": summary_path.is_file(),
        "request_artifact_exists": requests_path.is_file(),
        "phase4af_summary_detected": summary.get("phase4af_summary_detected") is True,
        "phase4af_ready": summary.get("phase4af_readiness_status") == "READY_FOR_EXTENSION_FETCH_DRY_RUN",
        "readiness_status_ready": summary.get("readiness_status") == READY,
        "extension_required": summary.get("extension_fetch_required") is True,
        "extension_count_matches": summary.get("extension_request_count") == summary.get("generated_extension_request_count"),
        "artifact_count_matches_summary": len(requests) == int(summary.get("generated_extension_request_count") or 0),
        "artifact_dates_match_summary": [request.get("date") for request in requests]
        == list(summary.get("extension_requested_dates") or []),
        "extension_range_matches_summary": _range_matches(requests, summary),
        "request_shape_valid": all(_request_shape_valid(request) for request in requests),
        "api_call_not_performed": summary.get("api_call_performed") is False
        and all(request.get("api_call_performed") is False for request in requests),
        "extension_fetch_not_executed": summary.get("extension_fetch_executed") is False
        and all(request.get("fetch_executed") is False for request in requests),
        "credential_not_read": summary.get("credential_read_performed") is False
        and all(request.get("credential_read_performed") is False for request in requests),
        "http_client_not_initialized": summary.get("http_client_initialized") is False
        and all(request.get("http_client_initialized") is False for request in requests),
        "raw_not_written": summary.get("raw_data_written") is False
        and summary.get("raw_manifest_updated") is False
        and all(request.get("raw_data_written") is False for request in requests),
        "normalized_not_written": summary.get("normalized_data_written") is False
        and summary.get("mock_path_written") is False
        and summary.get("isolated_normalized_path_written") is False,
        "promotion_not_performed": summary.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False,
        "feature_label_training_backtest_trading_not_executed": summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "merge_policy_defined": summary.get("merge_policy_defined") is True
        and summary.get("existing_raw_preserved") is True
        and summary.get("existing_success_manifest_preserved") is True
        and artifact.get("merge_policy", {}).get("existing_success_same_date_action") == "skip",
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(artifact),
    }
    result = {
        "phase": "Phase4-AG",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "requests_path": str(requests_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ag_real_runtime_extension_fetch_dry_run.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _request_shape_valid(request: dict[str, Any]) -> bool:
    params = request.get("params")
    return (
        isinstance(params, dict)
        and isinstance(request.get("request_index"), int)
        and isinstance(request.get("extension_request_index"), int)
        and request.get("endpoint") == "/v2/equities/bars/daily"
        and request.get("method") == "GET"
        and request.get("date") == params.get("date")
        and request.get("code") is None
        and request.get("pagination_key") is None
        and params.get("code") is None
        and params.get("pagination_key") is None
        and request.get("merge_mode") == "append_new_date_or_skip_existing_success"
        and request.get("existing_raw_preserved") is True
        and request.get("existing_success_manifest_preserved") is True
        and request.get("no_live") is True
    )


def _range_matches(requests: list[dict[str, Any]], summary: dict[str, Any]) -> bool:
    if not requests:
        return False
    return (
        requests[0].get("date") == summary.get("extension_fetch_start_date")
        and requests[-1].get("date") == summary.get("extension_fetch_end_date")
    )


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "api_call_performed",
        "extension_fetch_executed",
        "credential_read_performed",
        "http_client_initialized",
        "raw_data_written",
        "raw_manifest_updated",
        "normalized_data_written",
        "promotion_performed",
        "reader_switch_performed",
        "extension_fetch_start_date",
        "extension_fetch_end_date",
        "extension_request_count",
        "generated_extension_request_count",
        "extension_requested_dates",
        "endpoint",
        "method",
        "planned_raw_output_path",
        "dry_run_requests_path",
        "existing_raw_preserved",
        "existing_success_manifest_preserved",
        "merge_policy_defined",
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
        "# Phase4-AG Real Runtime Extension Fetch Dry-run Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        f"- requests: `{result['requests_path']}`",
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
            "- Phase4-AG generates an extension dry-run request artifact only.",
            "- It does not read credentials, initialize HTTP, call APIs, fetch, write raw responses, update raw manifests, write normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "secret", "token", "http://", "https://")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
