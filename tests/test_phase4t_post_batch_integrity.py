from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import build_first_controlled_batch_summary
from scripts.audit_phase4t_post_batch_integrity import (
    BLOCKED_MISSING_OUTPUT,
    READY,
    build_post_batch_integrity_summary,
    run_audit,
)
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_post_batch_integrity_ready_for_clean_first_batch(tmp_path: Path) -> None:
    phase4s = _build_phase4s_fixture(tmp_path)

    summary = build_post_batch_integrity_summary(phase4s)

    assert summary["status"] == "READY"
    assert summary["integrity_status"] == READY
    assert summary["checked_chunk_count"] == 2
    assert summary["final_output_exists_count"] == 2
    assert summary["tmp_leftover_count"] == 0
    assert summary["chunk_manifest_count"] == 2
    assert summary["chunk_audit_count"] == 2
    assert summary["success_manifest_count"] == 2
    assert summary["failed_manifest_count"] == 0
    assert summary["run_manifest_completed_chunk_count"] == 2
    assert summary["run_manifest_failed_chunk_count"] == 0
    assert summary["row_count_match"] is True
    assert summary["eligible_excluded_count_match"] is True
    assert summary["schema_validation_all_ok"] is True
    assert summary["leakage_audit_all_ok"] is True
    assert summary["resume_success_skip_ready"] is True
    assert summary["duplicate_output_count"] == 0
    assert summary["duplicate_manifest_count"] == 0
    assert summary["orphan_output_count"] == 0
    assert summary["orphan_manifest_count"] == 0
    assert summary["data_source_type_consistent"] is True
    assert summary["feature_version_consistent"] is True
    assert summary["schema_version_consistent"] is True


def test_post_batch_integrity_blocks_missing_output(tmp_path: Path) -> None:
    phase4s = _build_phase4s_fixture(tmp_path)
    manifest = json.loads(Path(phase4s["chunk_manifest_paths"][0]).read_text(encoding="utf-8"))
    Path(manifest["output_path"]).unlink()

    summary = build_post_batch_integrity_summary(phase4s)

    assert summary["status"] == "BLOCKED"
    assert summary["integrity_status"] == BLOCKED_MISSING_OUTPUT
    assert summary["final_output_exists_count"] == 1


def test_phase4t_audit_completes(tmp_path: Path) -> None:
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


def test_phase4t_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4t_post_batch_integrity.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["post_batch_integrity_summary_exists"]


def _build_phase4s_fixture(tmp_path: Path) -> dict[str, object]:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=tmp_path / "prepare_reports",
    )
    return build_first_controlled_batch_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=2,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id="phase4t_test",
    )
