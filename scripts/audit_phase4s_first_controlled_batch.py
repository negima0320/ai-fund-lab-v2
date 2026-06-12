#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import build_first_controlled_batch_summary  # noqa: E402
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history  # noqa: E402


SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4s_first_controlled_batch_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4s_first_controlled_batch_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4s_first_controlled_batch_audit.md")


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
    with tempfile.TemporaryDirectory(prefix="phase4s_first_batch_") as temp_dir:
        root = Path(temp_dir)
        runtime_dir = root / "runtime"
        report_dir = root / "reports"
        prepare_mock_normalized_history(
            runtime_dir=runtime_dir,
            business_days=65,
            code_count=4,
            output_format="jsonl",
            report_dir=root / "prepare_reports",
        )
        summary = build_first_controlled_batch_summary(
            runtime_dir=runtime_dir,
            report_dir=report_dir,
            input_format="jsonl",
            max_codes_per_chunk=2,
            max_chunks_to_execute=2,
            data_source_type="mock",
            run_id="phase4s_audit",
        )
    _write_json(summary_path, summary)
    executions = summary.get("runner_summary", {}).get("executions", [])
    checks = {
        "first_controlled_batch_cli_exists": Path("scripts/build_candidate_features_first_controlled_batch.py").is_file(),
        "readiness_gate_checked": summary.get("gate_status") == "READY_FOR_CONTROLLED_BATCH_EXECUTION",
        "max_chunks_to_execute_two": summary.get("max_chunks_to_execute") == 2,
        "stop_on_first_failure_true": summary.get("stop_on_first_failure") is True,
        "max_failed_chunks_allowed_zero": summary.get("max_failed_chunks_allowed") == 0,
        "executed_chunk_count_limited": 0 < int(summary.get("executed_chunk_count") or 0) <= 2,
        "tmp_to_final_atomic_move_used": summary.get("tmp_to_final_atomic_move") is True,
        "chunk_manifest_recorded": all(item.get("chunk_manifest_path") for item in executions) and bool(executions),
        "run_manifest_updated": bool(summary.get("run_manifest_path")),
        "schema_validation_ok": summary.get("schema_validation_status") == "OK",
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK",
        "summary_json_exists": summary_path.is_file(),
        "full_all_chunk_generation_not_executed": int(summary.get("executed_chunk_count") or 0) <= 2,
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-S",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "batch_status": summary.get("batch_status"),
        "gate_status": summary.get("gate_status"),
        "executed_chunk_count": summary.get("executed_chunk_count"),
        "completed_chunk_count": summary.get("completed_chunk_count"),
        "failed_chunk_count": summary.get("failed_chunk_count"),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4s_first_controlled_batch.py && python3 -m pytest -q",
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
        "# Phase4-S First Controlled Batch Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- gate_status: `{summary.get('gate_status')}`",
        f"- batch_status: `{summary.get('batch_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Batch Summary",
        "",
        f"- max_chunks_to_execute: {summary.get('max_chunks_to_execute')}",
        f"- stop_on_first_failure: {summary.get('stop_on_first_failure')}",
        f"- max_failed_chunks_allowed: {summary.get('max_failed_chunks_allowed')}",
        f"- planned_chunk_count: {summary.get('planned_chunk_count')}",
        f"- executed_chunk_count: {summary.get('executed_chunk_count')}",
        f"- completed_chunk_count: {summary.get('completed_chunk_count')}",
        f"- failed_chunk_count: {summary.get('failed_chunk_count')}",
        f"- skipped_chunk_count: {summary.get('skipped_chunk_count')}",
        f"- feature_output_written_count: {summary.get('feature_output_written_count')}",
        f"- schema_validation_status: {summary.get('schema_validation_status')}",
        f"- leakage_audit_status: {summary.get('leakage_audit_status')}",
        f"- stopped_on_failure: {summary.get('stopped_on_failure')}",
        f"- stop_reason: {summary.get('stop_reason')}",
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
            "- This phase executes at most two controlled chunks.",
            "- It does not implement all-chunk generation, labels, dataset building, training, inference, backtest, broker API, orders, trading, or Portfolio auto-update.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
