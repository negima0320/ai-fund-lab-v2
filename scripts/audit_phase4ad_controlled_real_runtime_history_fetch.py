#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase4ad_controlled_real_runtime_history_fetch import (  # noqa: E402
    READY,
    RAW_OUTPUT_DIR,
    RUN_MANIFEST_PATH,
    SUMMARY_PATH,
    run_controlled_fetch,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4ad_controlled_real_runtime_history_fetch_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ad_controlled_real_runtime_history_fetch_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    summary_path: Path = SUMMARY_PATH,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = _read_json_optional(summary_path)
    if not summary:
        summary = run_controlled_fetch(summary_path=summary_path, raw_output_dir=raw_output_dir)
    run_manifest_path = raw_output_dir / "manifest.json"
    run_manifest = _read_json_optional(run_manifest_path)
    request_manifests = _read_json_files(raw_output_dir / "request_manifests")
    response_files = sorted((raw_output_dir / "responses").glob("*.json"))
    checks = {
        "summary_exists": summary_path.is_file(),
        "phase4ac_summary_detected": summary.get("phase4ac_summary_detected") is True
        or summary.get("readiness_status") == "BLOCKED_BY_MISSING_CREDENTIAL",
        "credential_safety_recorded": "secret_present" in summary
        and summary.get("secret_value_logged") is False
        and summary.get("secret_value_written") is False,
        "api_call_status_consistent": isinstance(summary.get("api_call_performed"), bool),
        "fetch_status_consistent": isinstance(summary.get("fetch_executed"), bool),
        "raw_manifest_exists_when_fetch_attempted": (
            not summary.get("fetch_executed") or run_manifest_path.is_file()
        ),
        "request_manifests_exist_when_success_or_failure": (
            not summary.get("fetch_executed")
            or bool(request_manifests)
            or int(summary.get("skipped_request_count") or 0) == int(summary.get("planned_request_count") or 0)
        ),
        "responses_exist_when_success": (
            int(summary.get("succeeded_request_count") or 0) == 0 or bool(response_files)
        ),
        "resume_supported": summary.get("resume_supported") is True,
        "partial_failure_supported": summary.get("partial_failure_supported") is True,
        "normalized_not_written": summary.get("normalized_data_written") is False
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
        "rate_limit_policy_recorded": bool(summary.get("rate_limit_policy")),
        "raw_output_path_safe": str(summary.get("raw_output_path") or "").endswith(
            ".runtime/data/raw/jquants/equities_bars_daily/"
        )
        or "raw/jquants/equities_bars_daily" in str(summary.get("raw_output_path") or ""),
        "readiness_status_valid": summary.get("readiness_status")
        in {
            READY,
            "BLOCKED_BY_MISSING_PHASE4AC_SUMMARY",
            "BLOCKED_BY_PHASE4AC_NOT_READY",
            "BLOCKED_BY_MISSING_DRY_RUN_REQUESTS",
            "BLOCKED_BY_MISSING_CREDENTIAL",
            "BLOCKED_BY_SECRET_SAFETY",
            "BLOCKED_BY_RATE_LIMIT_SAFETY",
            "BLOCKED_BY_FETCH_FAILURE",
            "BLOCKED_BY_RAW_WRITE_FAILURE",
            "BLOCKED_BY_MANIFEST_FAILURE",
            "BLOCKED_BY_OUTPUT_PATH_SAFETY",
        },
        "secret_terms_not_emitted": _no_disallowed_secret_terms(summary, run_manifest, request_manifests),
    }
    result = {
        "phase": "Phase4-AD",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "raw_manifest_path": str(run_manifest_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ad_controlled_real_runtime_history_fetch.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


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
        "executed_request_count",
        "succeeded_request_count",
        "failed_request_count",
        "skipped_request_count",
        "completed_request_count",
        "pagination_request_count",
        "fetched_date_min",
        "fetched_date_max",
        "fetched_business_day_count",
        "fetched_row_count",
        "fetched_code_count",
        "post_fetch_raw_audit_status",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_files(path: Path) -> list[dict[str, Any]]:
    if not path.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        records.append(_read_json_optional(item))
    return records


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AD Controlled Real Runtime History Fetch Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        f"- raw_manifest: `{result['raw_manifest_path']}`",
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
            "- Phase4-AD is raw fetch only.",
            "- It does not write normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_disallowed_secret_terms(
    summary: dict[str, Any],
    run_manifest: dict[str, Any],
    request_manifests: list[dict[str, Any]],
) -> bool:
    text = json.dumps(
        {"summary": summary, "run_manifest": run_manifest, "request_manifests": request_manifests},
        ensure_ascii=True,
    )
    disallowed = ("Authorization", "x-api-key", "password", "cookie", "id_token", "refresh_token")
    return not any(term in text for term in disallowed)


if __name__ == "__main__":
    raise SystemExit(main())
