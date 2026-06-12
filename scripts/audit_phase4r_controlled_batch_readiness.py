#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import build_controlled_batch_readiness_summary  # noqa: E402


SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4r_controlled_batch_readiness_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4r_controlled_batch_readiness_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4r_controlled_batch_readiness_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_controlled_batch_readiness_summary()
    _write_json(summary_path, summary)
    checks = {
        "batch_readiness_summary_exists": summary_path.is_file(),
        "gate_status_produced": summary.get("gate_status") in {
            "READY_FOR_CONTROLLED_BATCH_EXECUTION",
            "BLOCKED_BY_CHUNK_PLAN",
            "BLOCKED_BY_RESUME_STATE",
            "BLOCKED_BY_MANIFEST_INCONSISTENCY",
            "BLOCKED_BY_STORAGE",
            "BLOCKED_BY_SCHEMA",
            "BLOCKED_BY_LEAKAGE",
            "SKIPPED_NO_DATA",
        },
        "chunk_count_checked": isinstance(summary.get("chunk_count"), int),
        "estimated_output_size_produced": isinstance(summary.get("estimated_output_size_bytes"), int),
        "runtime_storage_guard_present": isinstance(summary.get("runtime_free_space_check"), dict)
        and "runtime_free_space_sufficient" in summary,
        "resume_state_checked": "resume_state_consistent" in summary
        and "completed_chunk_count" in summary
        and "failed_chunk_count" in summary
        and "missing_chunk_count" in summary,
        "manifest_consistency_checked": "manifest_inconsistency_count" in summary,
        "version_consistency_checked": "feature_version_consistent" in summary
        and "schema_version_consistent" in summary
        and "data_source_type_consistent" in summary,
        "stop_on_first_failure_true": summary.get("stop_on_first_failure") is True,
        "max_failed_chunks_allowed_zero": summary.get("max_failed_chunks_allowed") == 0,
        "recommended_next_action_present": bool(summary.get("recommended_next_action")),
        "ready_or_clear_blocked_or_skipped": summary.get("status") in {"READY", "BLOCKED", "SKIPPED"},
        "full_range_generation_not_executed": summary.get("feature_generation_executed") is False,
        "label_training_inference_backtest_trading_not_implemented": summary.get("label_generation_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-R",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "gate_status": summary.get("gate_status"),
        "recommended_next_action": summary.get("recommended_next_action"),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4r_controlled_batch_readiness.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result, summary)
    return result


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any], summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-R Controlled Batch Readiness Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- gate_status: `{summary.get('gate_status')}`",
        f"- recommended_next_action: {summary.get('recommended_next_action')}",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Batch Readiness Summary",
        "",
        f"- chunk_count: {summary.get('chunk_count')}",
        f"- date_chunk_count: {summary.get('date_chunk_count')}",
        f"- code_chunk_count: {summary.get('code_chunk_count')}",
        f"- input_row_count: {summary.get('input_row_count')}",
        f"- estimated_feature_row_count: {summary.get('estimated_feature_row_count')}",
        f"- estimated_output_size_bytes: {summary.get('estimated_output_size_bytes')}",
        f"- runtime_free_space_sufficient: {summary.get('runtime_free_space_sufficient')}",
        f"- completed_chunk_count: {summary.get('completed_chunk_count')}",
        f"- failed_chunk_count: {summary.get('failed_chunk_count')}",
        f"- missing_chunk_count: {summary.get('missing_chunk_count')}",
        f"- partial_tmp_warning_count: {summary.get('partial_tmp_warning_count')}",
        f"- manifest_inconsistency_count: {summary.get('manifest_inconsistency_count')}",
        "",
        "## Stop And Resume Policy",
        "",
        "- stop_on_first_failure: true",
        "- max_failed_chunks_allowed: 0",
        "- If one chunk fails, batch execution must stop.",
        "- Successful final outputs remain, failed chunks are recorded by manifest and become rerun targets.",
        "- SUCCESS chunks are skipped, FAILED chunks are rerun, missing chunks are run.",
        "- Partial tmp outputs require review/isolation; manifest inconsistency blocks execution.",
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
            "- This is a readiness audit only.",
            "- It does not execute all chunks, generate labels, build datasets, train, infer, backtest, connect to broker APIs, place orders, trade, or update Portfolio automatically.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
