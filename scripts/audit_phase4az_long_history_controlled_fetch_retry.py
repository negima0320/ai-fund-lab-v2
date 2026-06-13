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

from scripts.phase4az_long_history_controlled_fetch_retry import (  # noqa: E402
    PARTIAL_READY,
    READY,
    RAW_OUTPUT_DIR,
    SUMMARY_PATH,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4az_long_history_controlled_fetch_retry_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4az_long_history_controlled_fetch_retry_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    summary_path: Path = SUMMARY_PATH,
    raw_manifest_path: Path = RAW_OUTPUT_DIR / "manifest.json",
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = _read_json_optional(summary_path)
    raw_manifest = _read_json_optional(raw_manifest_path)
    checks = {
        "summary_exists": summary_path.is_file(),
        "phase4ay_summary_detected": summary.get("phase4ay_summary_detected") is True,
        "corrected_requests_detected": summary.get("corrected_requests_detected") is True,
        "corrected_fetch_start_date_ok": summary.get("corrected_fetch_start_date") == "2021-06-01",
        "pre_start_request_not_executed": summary.get("pre_start_request_executed") is False,
        "raw_manifest_exists": raw_manifest_path.is_file(),
        "raw_manifest_phase_ok": raw_manifest.get("phase") == "Phase4-AZ",
        "raw_output_path_ok": str(summary.get("raw_output_path") or "").endswith(".runtime/data/raw/jquants/equities_bars_daily/"),
        "normalized_not_written": summary.get("normalized_data_written") is False
        and summary.get("normalized_output_written") is False
        and summary.get("mock_path_written") is False
        and summary.get("isolated_normalized_path_written") is False,
        "no_downstream_execution": summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("dataset_rebuild_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_promotion_or_reader_switch": summary.get("promotion_performed") is False
        and summary.get("reader_switch_performed") is False,
        "secret_value_not_written": summary.get("secret_value_written") is False
        and raw_manifest.get("secret_value_written") is False,
        "secret_value_not_logged": summary.get("secret_value_logged") is False
        and raw_manifest.get("secret_value_logged") is False,
        "resume_supported": summary.get("resume_supported") is True,
        "partial_failure_supported": summary.get("partial_failure_supported") is True,
        "existing_raw_preserved": summary.get("existing_raw_preserved") is True,
        "rate_limit_policy_present": bool(summary.get("rate_limit_policy")),
        "request_counts_consistent": int(summary.get("completed_request_count") or 0)
        == int(summary.get("succeeded_request_count") or 0) + int(summary.get("skipped_request_count") or 0),
        "quarantine_count_present": int(summary.get("quarantined_failed_manifest_count") or 0) >= 0,
        "readiness_valid": summary.get("readiness_status") in {READY, PARTIAL_READY},
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(raw_manifest),
    }
    result = {
        "phase": "Phase4-AZ",
        "status": "complete" if all(checks.values()) else "incomplete",
        "readiness_status": summary.get("readiness_status"),
        "checks": checks,
        "summary_path": str(summary_path),
        "raw_manifest_path": str(raw_manifest_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4az_long_history_controlled_fetch_retry.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _no_secret_terms(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = ("jquants_api_key", "authorization", "x-api-key", "refresh token", "id token", "password", "cookie", "bearer")
    return not any(term in text for term in forbidden)


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AZ Long History Controlled Fetch Retry Audit",
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
