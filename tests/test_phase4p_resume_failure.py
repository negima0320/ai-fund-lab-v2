from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    CONTROLLED_EXECUTION_FAILED,
    ControlledExecutionFailureInjection,
    FullRangeChunkManifest,
    build_full_range_chunk_plan,
    check_resume_restart,
    execute_full_range_chunk_controlled,
    resolve_full_range_paths,
)
from scripts.audit_phase4p_resume_failure import run_audit
from scripts.check_candidate_features_full_range_resume_failure import run_resume_failure_check


def test_schema_validation_failure_does_not_write_final_output(tmp_path: Path) -> None:
    records = _records()
    plan = build_full_range_chunk_plan(records, run_id="schema_failure", data_source_type="mock", max_codes_per_chunk=2)[0]
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    result = execute_full_range_chunk_controlled(
        records,
        plan,
        paths=paths,
        failure_injection=ControlledExecutionFailureInjection(force_schema_validation_failure=True),
    )

    assert result.status == CONTROLLED_EXECUTION_FAILED
    assert result.schema_validation_status == "ERROR"
    assert result.final_output_path is None
    assert "validation failure" in str(result.error_message)
    manifest = json.loads(Path(result.chunk_manifest_path).read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["output_path"] is None


def test_leakage_failure_does_not_write_final_output(tmp_path: Path) -> None:
    records = _records()
    plan = build_full_range_chunk_plan(records, run_id="leakage_failure", data_source_type="mock", max_codes_per_chunk=2)[0]
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    result = execute_full_range_chunk_controlled(
        records,
        plan,
        paths=paths,
        failure_injection=ControlledExecutionFailureInjection(force_leakage_audit_failure=True),
    )

    assert result.status == CONTROLLED_EXECUTION_FAILED
    assert result.leakage_audit_status == "ERROR"
    assert result.final_output_path is None
    assert "leakage failure" in str(result.error_message)
    manifest = json.loads(Path(result.chunk_manifest_path).read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["output_path"] is None


def test_write_and_atomic_move_failures_keep_final_output_clean(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="write_failure", data_source_type="mock", max_codes_per_chunk=2)
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    write_result = execute_full_range_chunk_controlled(
        records,
        plans[0],
        paths=paths,
        failure_injection=ControlledExecutionFailureInjection(force_write_failure=True),
    )
    assert write_result.status == CONTROLLED_EXECUTION_FAILED
    assert write_result.tmp_output_path is None
    assert write_result.final_output_path is None
    assert "write failure" in str(write_result.error_message)

    atomic_plan = build_full_range_chunk_plan(records, run_id="atomic_failure", data_source_type="mock", max_codes_per_chunk=2)[0]
    atomic_result = execute_full_range_chunk_controlled(
        records,
        atomic_plan,
        paths=paths,
        failure_injection=ControlledExecutionFailureInjection(force_atomic_move_failure=True),
    )
    assert atomic_result.status == CONTROLLED_EXECUTION_FAILED
    assert atomic_result.final_output_path is None
    assert atomic_result.tmp_output_path is not None
    assert Path(atomic_result.tmp_output_path).is_file()
    assert "atomic move failure" in str(atomic_result.error_message)


def test_resume_restart_detects_skip_rerun_partial_missing_unknown_and_duplicate(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="resume", data_source_type="mock", max_codes_per_chunk=1)
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")
    paths.ensure_dirs()
    output_path = paths.feature_dir / "ok.json"
    audit_path = paths.audit_dir / "ok.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("{}", encoding="utf-8")
    audit_path.write_text("{}", encoding="utf-8")
    _write_manifest(paths.manifest_dir / "success_chunk_manifest.json", plans[0], "resume_success", "SUCCESS", output_path, audit_path)
    _write_manifest(paths.manifest_dir / "failed_chunk_manifest.json", plans[1], "resume_failed", "FAILED", None, None)
    _write_manifest(paths.manifest_dir / "missing_chunk_manifest.json", plans[2], "resume_missing", "SUCCESS", paths.feature_dir / "missing.json", audit_path)
    _write_manifest(paths.manifest_dir / "unknown_chunk_manifest.json", plans[3], "resume_unknown", "ODD", None, None)
    _write_manifest(paths.manifest_dir / "duplicate_a_chunk_manifest.json", plans[4], "resume_duplicate", "SUCCESS", output_path, audit_path)
    _write_manifest(paths.manifest_dir / "duplicate_b_chunk_manifest.json", plans[4], "resume_duplicate", "SUCCESS", output_path, audit_path)
    partial = paths.tmp_dir / "partial.tmp.json"
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text("{}", encoding="utf-8")

    summary = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)

    assert "resume_success" in summary.completed_chunk_ids
    assert "resume_failed" in summary.failed_chunk_ids
    assert summary.partial_tmp_paths
    assert any("missing_output_path:resume_missing" in item for item in summary.manifest_inconsistencies)
    assert any("unknown_status:resume_unknown" in item for item in summary.manifest_inconsistencies)
    assert any("duplicate_chunk_manifest:resume_duplicate" in item for item in summary.manifest_inconsistencies)


def test_phase4p_resume_failure_check_script_summary_is_ok() -> None:
    summary = run_resume_failure_check()

    assert summary["status"] == "OK"
    assert all(summary["checks"].values())
    assert summary["full_range_feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False


def test_phase4p_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4p.json",
        markdown_report_path=tmp_path / "phase4p.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "phase4p.json").is_file()
    assert (tmp_path / "phase4p.md").is_file()


def test_phase4p_cli_scripts_run() -> None:
    check_result = subprocess.run(
        [sys.executable, "scripts/check_candidate_features_full_range_resume_failure.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert check_result.returncode == 0
    assert json.loads(check_result.stdout)["status"] == "OK"

    audit_result = subprocess.run(
        [sys.executable, "scripts/audit_phase4p_resume_failure.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert audit_result.returncode == 0
    assert json.loads(audit_result.stdout)["status"] == "complete"


def _write_manifest(
    path: Path,
    plan,
    chunk_id: str,
    status: str,
    output_path: Path | None,
    audit_path: Path | None,
) -> None:
    manifest = FullRangeChunkManifest(
        run_id=plan.run_id,
        chunk_id=chunk_id,
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
        error_message=None,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def _records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day in range(1, 24):
        date = f"2026-03-{day:02d}"
        for code in ("11110", "22220", "33330", "44440", "55550"):
            records.append(
                {
                    "Date": date,
                    "Code": code,
                    "Open": 10 + day,
                    "High": 12 + day,
                    "Low": 9 + day,
                    "Close": 11 + day,
                    "Volume": 1000 + day,
                }
            )
    return records
