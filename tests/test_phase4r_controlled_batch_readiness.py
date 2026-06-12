from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    BATCH_READINESS_BLOCKED_BY_MANIFEST_INCONSISTENCY,
    BATCH_READINESS_READY,
    FullRangeChunkManifest,
    build_controlled_batch_readiness_summary,
    build_full_range_chunk_plan,
    resolve_full_range_paths,
)
from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized
from ai_fund_lab_v2.data_store import create_storage_backend
from scripts.audit_phase4r_controlled_batch_readiness import run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_batch_readiness_summary_is_ready_for_clean_mock_history(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=tmp_path / "prepare_reports",
    )

    summary = build_controlled_batch_readiness_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=2,
        data_source_type="mock",
        run_id="phase4r_ready",
    )

    assert summary["status"] == "READY"
    assert summary["gate_status"] == BATCH_READINESS_READY
    assert summary["chunk_count"] > 0
    assert summary["date_chunk_count"] > 0
    assert summary["code_chunk_count"] > 0
    assert summary["input_row_count"] > 0
    assert summary["estimated_feature_row_count"] > 0
    assert summary["estimated_output_size_bytes"] > 0
    assert summary["runtime_free_space_check"]["status"] in {"OK", "UNKNOWN"}
    assert summary["runtime_free_space_sufficient"] is True
    assert summary["resume_state_consistent"] is True
    assert summary["manifest_inconsistency_count"] == 0
    assert summary["feature_version_consistent"] is True
    assert summary["schema_version_consistent"] is True
    assert summary["data_source_type_consistent"] is True
    assert summary["preflight_schema_validation_status"] == "OK"
    assert summary["preflight_leakage_audit_status"] == "OK"
    assert summary["stop_on_first_failure"] is True
    assert summary["max_failed_chunks_allowed"] == 0
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False


def test_batch_readiness_blocks_manifest_inconsistency(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    run_id = "phase4r_block"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=tmp_path / "prepare_reports",
    )
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format="jsonl")
    assert discovery.path is not None
    assert discovery.storage_format is not None
    records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type="mock", max_codes_per_chunk=2)
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    _write_manifest(paths.manifest_dir / "missing_output_manifest.json", plans[0], paths.feature_dir / "missing.json")

    summary = build_controlled_batch_readiness_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=2,
        data_source_type="mock",
        run_id=run_id,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["gate_status"] == BATCH_READINESS_BLOCKED_BY_MANIFEST_INCONSISTENCY
    assert summary["manifest_inconsistency_count"] >= 1
    assert summary["feature_generation_executed"] is False


def test_phase4r_audit_completes(tmp_path: Path) -> None:
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


def test_phase4r_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4r_controlled_batch_readiness.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout[result.stdout.find("{") :])
    assert payload["status"] == "complete"
    assert payload["checks"]["batch_readiness_summary_exists"]


def _write_manifest(path: Path, plan, output_path: Path) -> None:
    manifest = FullRangeChunkManifest(
        run_id=plan.run_id,
        chunk_id=plan.chunk_id,
        status="SUCCESS",
        date_start=plan.date_start,
        date_end=plan.date_end,
        code_count=plan.code_count,
        row_count=1,
        eligible_count=1,
        excluded_count=0,
        schema_validation_status="OK",
        leakage_audit_status="OK",
        output_path=str(output_path),
        manifest_path=str(path),
        audit_path=None,
        error_message=None,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
