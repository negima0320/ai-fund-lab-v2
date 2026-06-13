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

from scripts.phase4aw_long_history_fetch_dry_run import (  # noqa: E402
    READY,
    REQUESTS_PATH,
    SUMMARY_PATH,
    run_phase4aw_long_history_fetch_dry_run,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4aw_long_history_fetch_dry_run_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4aw_long_history_fetch_dry_run_audit.md")


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
    if not summary_path.is_file() or not requests_path.is_file():
        run_phase4aw_long_history_fetch_dry_run(summary_path=summary_path, requests_path=requests_path)
    summary = _read_json_optional(summary_path)
    requests_artifact = _read_json_optional(requests_path)
    requests = requests_artifact.get("requests") if isinstance(requests_artifact.get("requests"), list) else []
    checks = {
        "summary_exists": summary_path.is_file(),
        "requests_artifact_exists": requests_path.is_file(),
        "dry_run_executed": summary.get("dry_run_executed") is True,
        "api_not_called": summary.get("api_call_performed") is False,
        "credential_not_read": summary.get("credential_read_performed") is False,
        "http_client_not_initialized": summary.get("http_client_initialized") is False,
        "fetch_not_executed": summary.get("fetch_executed") is False,
        "raw_normalized_not_modified": summary.get("raw_data_modified") is False
        and summary.get("normalized_data_modified") is False,
        "mock_path_unchanged": summary.get("mock_path_unchanged") is True,
        "request_sequence_generated": summary.get("request_sequence_generated") is True and bool(requests),
        "request_count_matches_summary": len(requests) == int(summary.get("request_count") or -1),
        "request_count_matches_plan": summary.get("request_count_match") is True,
        "request_schema_ok": _request_schema_ok(requests),
        "endpoint_ok": summary.get("endpoint") == "/v2/equities/bars/daily",
        "method_ok": summary.get("method") == "GET",
        "rate_limit_policy_defined": bool(summary.get("rate_limit_policy")),
        "resume_policy_defined": bool(summary.get("resume_policy")),
        "manifest_policy_defined": bool(summary.get("manifest_policy")),
        "storage_estimate_present": float(summary.get("storage_estimate_mb") or 0.0) > 0,
        "no_downstream_execution": summary.get("normalized_rebuild_executed") is False
        and summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("dataset_rebuild_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "readiness_ready": summary.get("readiness_status") == READY,
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(requests_artifact),
    }
    result = {
        "phase": "Phase4-AW",
        "status": "complete" if all(checks.values()) else "incomplete",
        "readiness_status": summary.get("readiness_status"),
        "checks": checks,
        "summary_path": str(summary_path),
        "requests_path": str(requests_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4aw_long_history_fetch_dry_run.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _request_schema_ok(requests: list[dict[str, Any]]) -> bool:
    if not requests:
        return False
    sample = requests[:5] + requests[-5:]
    for request in sample:
        params = request.get("params")
        if request.get("endpoint") != "/v2/equities/bars/daily":
            return False
        if request.get("method") != "GET":
            return False
        if not isinstance(params, dict):
            return False
        if not params.get("date"):
            return False
        if params.get("code") is not None:
            return False
        if params.get("pagination_key") is not None:
            return False
    return True


def _no_secret_terms(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = ("jquants_api_key", "authorization", "x-api-key", "refresh token", "id token", "password", "cookie")
    return not any(term in text for term in forbidden)


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AW Long History Fetch Dry-run Audit",
        "",
        f"- status: `{result['status']}`",
        f"- readiness_status: `{result.get('readiness_status')}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- {key}: `{value}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
