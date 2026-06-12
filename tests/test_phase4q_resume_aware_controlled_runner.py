from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    FullRangeChunkManifest,
    build_full_range_chunk_plan,
    build_full_range_resume_controlled_summary,
    resolve_full_range_paths,
)
from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized
from ai_fund_lab_v2.data_store import create_storage_backend
from scripts.audit_phase4q_resume_aware_controlled_runner import run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_resume_aware_runner_skips_success_reruns_failed_and_runs_missing(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    run_id = "phase4q_test"
    plans, paths = _prepare_plans(runtime_dir, report_dir, run_id)
    output_path = paths.feature_dir / "done.json"
    audit_path = paths.audit_dir / "done_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('{"rows":[]}\n', encoding="utf-8")
    audit_path.write_text('{"status":"OK"}\n', encoding="utf-8")
    _write_manifest(paths.manifest_dir / "success_manifest.json", plans[0], "SUCCESS", output_path, audit_path)
    _write_manifest(paths.manifest_dir / "failed_manifest.json", plans[1], "FAILED", None, None)
    partial = paths.tmp_dir / run_id / "partial.tmp.json"
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text('{"partial":true}\n', encoding="utf-8")

    summary = build_full_range_resume_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=1,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id=run_id,
    )

    assert summary["status"] == "OK"
    assert summary["skipped_success_chunk_count"] == 1
    assert summary["rerun_failed_chunk_count"] == 1
    assert summary["run_missing_chunk_count"] >= 1
    assert summary["executed_chunk_count"] == 2
    assert summary["partial_tmp_warning_count"] == 1
    assert summary["tmp_to_final_atomic_move"] is True
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    run_manifest = json.loads(Path(summary["run_manifest_path"]).read_text(encoding="utf-8"))
    assert run_manifest["completed_chunk_count"] == 3
    assert run_manifest["failed_chunk_count"] == 0


def test_resume_aware_runner_blocks_on_manifest_inconsistency(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    run_id = "phase4q_block"
    plans, paths = _prepare_plans(runtime_dir, report_dir, run_id)
    _write_manifest(paths.manifest_dir / "missing_output_manifest.json", plans[0], "SUCCESS", paths.feature_dir / "missing.json", None)

    summary = build_full_range_resume_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=1,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id=run_id,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["blocked_inconsistency_count"] >= 1
    assert summary["executed_chunk_count"] == 0
    assert summary["feature_generation_executed"] is False


def test_resume_aware_runner_blocks_when_max_chunks_exceeds_two(tmp_path: Path) -> None:
    summary = build_full_range_resume_controlled_summary(
        runtime_dir=tmp_path / "runtime",
        report_dir=tmp_path / "reports",
        max_chunks_to_execute=3,
        run_id="too_many",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["executed_chunk_count"] == 0
    assert "max_chunks_to_execute <= 2" in summary["reason"]


def test_phase4q_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4q.json",
        markdown_report_path=tmp_path / "phase4q.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "phase4q.json").is_file()
    assert (tmp_path / "phase4q.md").is_file()


def test_phase4q_cli_scripts_run() -> None:
    build_result = subprocess.run(
        [
            sys.executable,
            "scripts/build_candidate_features_full_range_resume_controlled.py",
            "--max-chunks-to-execute",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build_result.returncode == 0
    build_payload = json.loads(build_result.stdout[build_result.stdout.find("{") :])
    assert build_payload["executed_chunk_count"] <= 2
    assert build_payload["label_generation_executed"] is False

    audit_result = subprocess.run(
        [sys.executable, "scripts/audit_phase4q_resume_aware_controlled_runner.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert audit_result.returncode == 0
    assert json.loads(audit_result.stdout)["status"] == "complete"


def _prepare_plans(runtime_dir: Path, report_dir: Path, run_id: str):
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=report_dir / "prepare",
    )
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format="jsonl")
    assert discovery.path is not None
    assert discovery.storage_format is not None
    records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type="mock", max_codes_per_chunk=1)
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    return plans, paths


def _write_manifest(path: Path, plan, status: str, output_path: Path | None, audit_path: Path | None) -> None:
    manifest = FullRangeChunkManifest(
        run_id=plan.run_id,
        chunk_id=plan.chunk_id,
        status=status,
        date_start=plan.date_start,
        date_end=plan.date_end,
        code_count=plan.code_count,
        row_count=1,
        eligible_count=1,
        excluded_count=0,
        schema_validation_status="OK",
        leakage_audit_status="OK",
        output_path=str(output_path) if output_path else None,
        manifest_path=str(path),
        audit_path=str(audit_path) if audit_path else None,
        error_message=None if status == "SUCCESS" else "fixture failed",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
