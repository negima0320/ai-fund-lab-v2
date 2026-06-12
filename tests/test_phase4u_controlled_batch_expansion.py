from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai import build_first_controlled_batch_summary
from scripts.audit_phase4t_post_batch_integrity import READY, build_post_batch_integrity_summary
from scripts.audit_phase4u_controlled_batch_expansion import run_audit
from scripts.build_candidate_features_controlled_batch_expansion import build_controlled_batch_expansion_summary
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_controlled_batch_expansion_skips_success_and_executes_missing(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=70,
        code_count=4,
        output_format="jsonl",
        report_dir=tmp_path / "prepare_reports",
    )
    phase4t_gate = _phase4t_gate_fixture(runtime_dir, report_dir)

    summary = build_controlled_batch_expansion_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=4,
        max_chunks_to_execute=4,
        data_source_type="mock",
        run_id="phase4u_test",
        phase4t_integrity_summary=phase4t_gate,
    )

    assert summary["status"] == "OK"
    assert summary["expansion_status"] == "CONTROLLED_BATCH_EXPANSION_COMPLETED"
    assert summary["integrity_gate_status"] == "READY"
    assert summary["max_chunks_to_execute"] == 4
    assert summary["stop_on_first_failure"] is True
    assert summary["max_failed_chunks_allowed"] == 0
    assert summary["planned_chunk_count"] == 4
    assert summary["existing_success_chunk_count"] == 2
    assert summary["skipped_success_chunk_count"] == 2
    assert summary["executed_chunk_count"] == 2
    assert summary["failed_chunk_count"] == 0
    assert summary["remaining_missing_chunk_count"] == 0
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["tmp_leftover_count"] == 0
    assert summary["duplicate_output_count"] == 0
    assert summary["duplicate_manifest_count"] == 0
    assert summary["orphan_output_count"] == 0
    assert summary["orphan_manifest_count"] == 0
    assert summary["feature_generation_executed"] is True
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    post = summary["post_expansion_integrity"]
    assert post["final_output_exists_count"] == post["success_manifest_count"]
    assert post["run_manifest_completed_chunk_count"] == post["success_manifest_count"]


def test_controlled_batch_expansion_blocks_without_ready_gate(tmp_path: Path) -> None:
    summary = build_controlled_batch_expansion_summary(
        runtime_dir=tmp_path / "runtime",
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        max_chunks_to_execute=4,
        run_id="phase4u_blocked",
        phase4t_integrity_summary={"integrity_status": "BLOCKED_BY_AUDIT_FAILURE"},
    )

    assert summary["status"] == "BLOCKED"
    assert summary["integrity_gate_status"] == "BLOCKED"
    assert summary["executed_chunk_count"] == 0
    assert summary["feature_generation_executed"] is False


def test_controlled_batch_expansion_requires_four_chunk_limit(tmp_path: Path) -> None:
    ready_gate = {
        "integrity_status": READY,
        "tmp_leftover_count": 0,
        "schema_validation_all_ok": True,
        "leakage_audit_all_ok": True,
        "resume_success_skip_ready": True,
        "duplicate_output_count": 0,
        "orphan_output_count": 0,
    }

    summary = build_controlled_batch_expansion_summary(
        runtime_dir=tmp_path / "runtime",
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        max_chunks_to_execute=5,
        run_id="phase4u_too_many",
        phase4t_integrity_summary=ready_gate,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["executed_chunk_count"] == 0
    assert "max_chunks_to_execute=4" in summary["stop_reason"]


def test_phase4u_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4u.json",
        markdown_report_path=tmp_path / "phase4u.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "phase4u.json").is_file()
    assert (tmp_path / "phase4u.md").is_file()


def test_phase4u_cli_scripts_run() -> None:
    build_result = subprocess.run(
        [sys.executable, "scripts/build_candidate_features_controlled_batch_expansion.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build_result.returncode == 0
    build_payload = json.loads(build_result.stdout)
    assert build_payload["max_chunks_to_execute"] == 4
    assert build_payload["status"] in {"OK", "BLOCKED", "SKIPPED"}
    assert build_payload["label_generation_executed"] is False

    audit_result = subprocess.run(
        [sys.executable, "scripts/audit_phase4u_controlled_batch_expansion.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert audit_result.returncode == 0
    assert json.loads(audit_result.stdout)["status"] == "complete"


def _phase4t_gate_fixture(runtime_dir: Path, report_dir: Path) -> dict[str, object]:
    phase4s = build_first_controlled_batch_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=4,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id="phase4u_gate_test",
    )
    gate = build_post_batch_integrity_summary(phase4s)
    assert gate["integrity_status"] == READY
    return gate
