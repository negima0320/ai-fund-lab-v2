#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase4ac_real_runtime_history_fetch_dry_run import (  # noqa: E402
    READY,
    REQUESTS_PATH,
    SUMMARY_PATH,
    run_dry_run,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4ac_real_runtime_history_fetch_dry_run_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ac_real_runtime_history_fetch_dry_run_audit.md")


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
        "phase4ab_summary_detected": summary.get("phase4ab_summary_detected") is True,
        "phase4ab_ready": summary.get("phase4ab_readiness_status") == "READY_FOR_NO_LIVE_FETCH_DRY_RUN_CLI",
        "readiness_status_ready": summary.get("readiness_status") == READY,
        "planned_equals_generated": summary.get("planned_request_count") == summary.get("generated_request_count"),
        "artifact_count_matches_summary": len(requests) == int(summary.get("generated_request_count") or 0),
        "request_dates_match_range": _dates_match_range(requests, summary),
        "request_shape_valid": all(_request_shape_valid(request) for request in requests),
        "api_call_not_performed": summary.get("api_call_performed") is False
        and all(request.get("api_call_performed") is False for request in requests),
        "fetch_not_executed": summary.get("fetch_executed") is False
        and all(request.get("fetch_executed") is False for request in requests),
        "credential_not_read": summary.get("credential_read_performed") is False,
        "http_client_not_initialized": summary.get("http_client_initialized") is False,
        "raw_not_written": summary.get("raw_data_written") is False,
        "normalized_not_written": summary.get("normalized_data_written") is False,
        "promotion_not_performed": summary.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False,
        "feature_label_training_backtest_trading_not_executed": summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "mock_path_not_output_target": summary.get("mock_path_will_be_unchanged") is True
        and summary.get("isolated_normalized_output_path")
        == ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/",
        "gates_carried_forward": summary.get("manifest_provenance_plan_carried_forward") is True
        and summary.get("post_fetch_raw_audit_defined") is True
        and summary.get("post_normalize_coverage_audit_defined") is True
        and summary.get("promotion_gate_carried_forward") is True
        and summary.get("reader_switch_gate_carried_forward") is True
        and summary.get("rollback_plan_carried_forward") is True,
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(artifact),
    }
    result = {
        "phase": "Phase4-AC",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "requests_path": str(requests_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ac_real_runtime_history_fetch_dry_run.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _request_shape_valid(request: dict[str, Any]) -> bool:
    params = request.get("params")
    return (
        isinstance(params, dict)
        and isinstance(request.get("request_index"), int)
        and request.get("endpoint") == "/v2/equities/bars/daily"
        and request.get("method") == "GET"
        and request.get("date") == params.get("date")
        and params.get("code") is None
        and params.get("pagination_key") is None
        and request.get("no_live") is True
    )


def _dates_match_range(requests: list[dict[str, Any]], summary: dict[str, Any]) -> bool:
    if not requests:
        return False
    dates = [str(request.get("date")) for request in requests]
    return dates[0] == summary.get("target_start_date") and dates[-1] <= str(summary.get("target_end_date"))


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "api_call_performed",
        "fetch_executed",
        "credential_read_performed",
        "http_client_initialized",
        "raw_data_written",
        "normalized_data_written",
        "promotion_performed",
        "reader_switch_performed",
        "target_start_date",
        "target_end_date",
        "planned_request_count",
        "generated_request_count",
        "endpoint",
        "method",
        "raw_output_path",
        "isolated_normalized_output_path",
        "dry_run_requests_path",
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
        "# Phase4-AC Real Runtime History Fetch Dry-run Audit",
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
            "- Phase4-AC generates a dry-run request artifact only.",
            "- It does not initialize an API client, read credentials, perform HTTP requests, write raw data, write normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
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
