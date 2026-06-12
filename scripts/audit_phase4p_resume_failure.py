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

from scripts.check_candidate_features_full_range_resume_failure import SUMMARY_PATH, run_resume_failure_check  # noqa: E402


JSON_REPORT_PATH = Path("reports/phase_reports/phase4p_resume_failure_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4p_resume_failure_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = run_resume_failure_check()
    _write_json(SUMMARY_PATH, summary)
    checks = {
        "failure_injection_exists": _source_contains("ControlledExecutionFailureInjection")
        and _source_contains("force_schema_validation_failure")
        and _source_contains("force_leakage_audit_failure")
        and _source_contains("force_write_failure")
        and _source_contains("force_atomic_move_failure"),
        "validation_failure_prevents_final_output": bool(summary["checks"].get("validation_failure_prevents_final_output")),
        "leakage_failure_prevents_final_output": bool(summary["checks"].get("leakage_failure_prevents_final_output")),
        "failed_chunk_manifest_recorded": bool(summary["checks"].get("failed_chunk_manifest_recorded")),
        "success_chunk_skip_candidate": bool(summary["checks"].get("success_chunk_skip_candidate")),
        "failed_chunk_rerun_candidate": bool(summary["checks"].get("failed_chunk_rerun_candidate")),
        "partial_tmp_warning": bool(summary["checks"].get("partial_tmp_warning")),
        "missing_final_output_inconsistency": bool(summary["checks"].get("missing_final_output_inconsistency")),
        "unknown_status_inconsistency": bool(summary["checks"].get("unknown_status_inconsistency")),
        "duplicate_manifest_inconsistency": bool(summary["checks"].get("duplicate_manifest_inconsistency")),
        "run_manifest_counts_updated": bool(summary["checks"].get("run_manifest_counts_updated")),
        "summary_json_exists": SUMMARY_PATH.is_file(),
        "full_range_generation_not_expanded": summary.get("full_range_feature_generation_executed") is False,
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-P",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "summary_path": str(SUMMARY_PATH),
        "pytest_hint": "python3 -m pytest tests/test_phase4p_resume_failure.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _source_contains(text: str) -> bool:
    source = Path("src/ai_fund_lab_v2/candidate_ai/full_range.py").read_text(encoding="utf-8")
    return text in source


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-P Controlled Execution Failure / Resume Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Checks",
        "",
    ]
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This audit is limited to controlled execution failure injection and resume/restart judgment.",
            "- It does not implement full-range generation, labels, dataset building, training, inference, backtest, broker API, orders, trading, or Portfolio auto-update.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
