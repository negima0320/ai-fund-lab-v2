from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_phase4v_post_expansion_readiness import (
    READY_FULL,
    build_post_expansion_readiness_summary,
    run_audit,
)
from scripts.build_candidate_features_controlled_batch_expansion import build_controlled_batch_expansion_summary
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_post_expansion_readiness_ready_for_mock_full_controlled_generation(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    phase4u = _build_phase4u_fixture(runtime_dir, report_dir)

    summary = build_post_expansion_readiness_summary(
        phase4u_summary=phase4u,
        runtime_dir=runtime_dir,
        report_dir=report_dir,
    )

    assert summary["status"] == "READY"
    assert summary["readiness_status"] == READY_FULL
    assert summary["data_source_type"] == "mock"
    assert summary["completed_chunk_count"] == 4
    assert summary["failed_chunk_count"] == 0
    assert summary["remaining_missing_chunk_count"] == 0
    assert summary["final_output_count"] == 4
    assert summary["chunk_manifest_count"] == 4
    assert summary["chunk_audit_count"] == 4
    assert summary["run_manifest_completed_count"] == 4
    assert summary["tmp_leftover_count"] == 0
    assert summary["duplicate_output_count"] == 0
    assert summary["orphan_output_count"] == 0
    assert summary["total_feature_rows"] > 0
    assert summary["eligible_count"] > 0
    assert summary["excluded_count"] == 0
    assert summary["code_count"] == 4
    assert summary["date_min"] <= summary["date_max"]
    assert summary["feature_columns"]
    assert isinstance(summary["null_count_by_feature"], dict)
    assert isinstance(summary["excluded_reason_counts"], dict)
    assert summary["schema_validation_all_ok"] is True
    assert summary["leakage_audit_all_ok"] is True
    assert summary["forbidden_feature_detected"] is False
    assert summary["future_column_detected"] is False
    assert summary["label_column_detected"] is False
    assert summary["runtime_free_space_sufficient"] is True
    assert summary["resume_ready"] is True
    assert summary["manifest_consistent"] is True
    assert summary["artifact_integrity_ok"] is True
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_post_expansion_readiness_blocks_missing_output(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    phase4u = _build_phase4u_fixture(runtime_dir, report_dir)
    manifest_path = next(
        path
        for path in (runtime_dir / "candidate_ai" / "manifests" / "full_range").glob(f"{phase4u['run_id']}_*manifest.json")
        if not path.name.endswith("_run_manifest.json")
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(manifest["output_path"]).unlink()

    summary = build_post_expansion_readiness_summary(
        phase4u_summary=phase4u,
        runtime_dir=runtime_dir,
        report_dir=report_dir,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_ARTIFACT_INTEGRITY"
    assert summary["artifact_integrity_ok"] is False


def test_phase4v_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "phase4v.json",
        markdown_report_path=tmp_path / "phase4v.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "phase4v.json").is_file()
    assert (tmp_path / "phase4v.md").is_file()


def test_phase4v_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4v_post_expansion_readiness.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["post_expansion_readiness_summary_exists"]
    assert payload["checks"]["label_generation_not_implemented"]


def _build_phase4u_fixture(runtime_dir: Path, report_dir: Path) -> dict[str, object]:
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=70,
        code_count=4,
        output_format="jsonl",
        report_dir=report_dir / "prepare",
    )
    ready_gate = {
        "integrity_status": "READY_FOR_CONTROLLED_BATCH_EXPANSION",
        "tmp_leftover_count": 0,
        "schema_validation_all_ok": True,
        "leakage_audit_all_ok": True,
        "resume_success_skip_ready": True,
        "duplicate_output_count": 0,
        "orphan_output_count": 0,
    }
    return build_controlled_batch_expansion_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=4,
        max_chunks_to_execute=4,
        data_source_type="mock",
        run_id="phase4v_fixture",
        phase4t_integrity_summary=ready_gate,
    )
