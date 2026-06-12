from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    BATCH_READINESS_READY,
    build_first_controlled_batch_summary,
)
from scripts.audit_phase4s_first_controlled_batch import run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_first_controlled_batch_executes_two_chunks_after_ready_gate(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=tmp_path / "prepare_reports",
    )

    summary = build_first_controlled_batch_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=2,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id="phase4s_test",
    )

    assert summary["status"] == "OK"
    assert summary["batch_status"] == "FIRST_CONTROLLED_BATCH_COMPLETED"
    assert summary["gate_status"] == BATCH_READINESS_READY
    assert summary["max_chunks_to_execute"] == 2
    assert summary["stop_on_first_failure"] is True
    assert summary["max_failed_chunks_allowed"] == 0
    assert summary["executed_chunk_count"] == 2
    assert summary["completed_chunk_count"] == 2
    assert summary["failed_chunk_count"] == 0
    assert summary["feature_output_written_count"] == 2
    assert summary["tmp_to_final_atomic_move"] is True
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["stopped_on_failure"] is False
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert Path(summary["run_manifest_path"]).is_file()
    assert all(Path(path).is_file() for path in summary["chunk_manifest_paths"])


def test_first_controlled_batch_blocks_if_limit_is_not_two(tmp_path: Path) -> None:
    summary = build_first_controlled_batch_summary(
        runtime_dir=tmp_path / "runtime",
        report_dir=tmp_path / "reports",
        max_chunks_to_execute=3,
        run_id="phase4s_limit_block",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["executed_chunk_count"] == 0
    assert summary["feature_generation_executed"] is False
    assert summary["stop_reason"] == "Phase4-S requires max_chunks_to_execute=2"


def test_phase4s_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4s_cli_scripts_run() -> None:
    build_result = subprocess.run(
        [sys.executable, "scripts/build_candidate_features_first_controlled_batch.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build_result.returncode == 0
    payload = json.loads(build_result.stdout[build_result.stdout.find("{") :])
    assert payload["max_chunks_to_execute"] == 2
    assert payload["executed_chunk_count"] <= 2
    assert payload["label_generation_executed"] is False

    audit_result = subprocess.run(
        [sys.executable, "scripts/audit_phase4s_first_controlled_batch.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert audit_result.returncode == 0
    assert json.loads(audit_result.stdout)["status"] == "complete"
