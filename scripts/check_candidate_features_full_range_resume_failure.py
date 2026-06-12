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

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    ControlledExecutionFailureInjection,
    FullRangeChunkManifest,
    build_full_range_chunk_plan,
    build_full_range_controlled_summary,
    check_resume_restart,
    resolve_full_range_paths,
)
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized  # noqa: E402
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history  # noqa: E402


SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4p_resume_failure_summary.json")


def main() -> int:
    summary = run_resume_failure_check()
    _write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "OK" else 1


def run_resume_failure_check() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="phase4p_resume_failure_") as temp_dir:
        root = Path(temp_dir)
        schema_failure = _run_controlled_failure(
            root,
            "phase4p_schema_failure",
            ControlledExecutionFailureInjection(force_schema_validation_failure=True),
        )
        leakage_failure = _run_controlled_failure(
            root,
            "phase4p_leakage_failure",
            ControlledExecutionFailureInjection(force_leakage_audit_failure=True),
        )
        write_failure = _run_controlled_failure(
            root,
            "phase4p_write_failure",
            ControlledExecutionFailureInjection(force_write_failure=True),
        )
        atomic_failure = _run_controlled_failure(
            root,
            "phase4p_atomic_failure",
            ControlledExecutionFailureInjection(force_atomic_move_failure=True),
        )

        resume_summary = _build_resume_fixture(root)
        checks = {
            "validation_failure_prevents_final_output": schema_failure["controlled_status"] == "CONTROLLED_EXECUTION_FAILED"
            and not schema_failure.get("feature_output_path")
            and schema_failure.get("schema_validation_status") == "ERROR"
            and "validation failure" in str(schema_failure.get("error_message") or ""),
            "leakage_failure_prevents_final_output": leakage_failure["controlled_status"] == "CONTROLLED_EXECUTION_FAILED"
            and not leakage_failure.get("feature_output_path")
            and leakage_failure.get("leakage_audit_status") == "ERROR"
            and "leakage failure" in str(leakage_failure.get("error_message") or ""),
            "write_failure_records_failed_manifest": write_failure["controlled_status"] == "CONTROLLED_EXECUTION_FAILED"
            and not write_failure.get("feature_output_path")
            and "write failure" in str(write_failure.get("error_message") or ""),
            "atomic_move_failure_keeps_final_clean": atomic_failure["controlled_status"] == "CONTROLLED_EXECUTION_FAILED"
            and not atomic_failure.get("feature_output_path")
            and atomic_failure.get("tmp_output_path")
            and Path(str(atomic_failure["tmp_output_path"])).is_file()
            and "atomic move failure" in str(atomic_failure.get("error_message") or ""),
            "failed_chunk_manifest_recorded": _manifest_status(schema_failure.get("chunk_manifest_path")) == "FAILED"
            and _manifest_status(leakage_failure.get("chunk_manifest_path")) == "FAILED",
            "success_chunk_skip_candidate": "resume_success" in resume_summary.completed_chunk_ids,
            "failed_chunk_rerun_candidate": "resume_failed" in resume_summary.failed_chunk_ids,
            "partial_tmp_warning": bool(resume_summary.partial_tmp_paths),
            "missing_final_output_inconsistency": any("missing_output_path:resume_missing_output" in item for item in resume_summary.manifest_inconsistencies),
            "unknown_status_inconsistency": any("unknown_status:resume_unknown" in item for item in resume_summary.manifest_inconsistencies),
            "duplicate_manifest_inconsistency": any("duplicate_chunk_manifest:resume_duplicate" in item for item in resume_summary.manifest_inconsistencies),
            "run_manifest_counts_updated": _run_manifest_counts_ok(schema_failure)
            and _run_manifest_counts_ok(leakage_failure)
            and _run_manifest_counts_ok(write_failure)
            and _run_manifest_counts_ok(atomic_failure),
        }
        return {
            "phase": "Phase4-P",
            "status": "OK" if all(checks.values()) else "ERROR",
            "mode": "fixture_controlled_execution_only",
            "full_range_feature_generation_executed": False,
            "label_generation_executed": False,
            "training_executed": False,
            "inference_executed": False,
            "backtest_executed": False,
            "trading_executed": False,
            "checks": checks,
            "schema_failure": _small_failure_summary(schema_failure),
            "leakage_failure": _small_failure_summary(leakage_failure),
            "write_failure": _small_failure_summary(write_failure),
            "atomic_move_failure": _small_failure_summary(atomic_failure),
            "resume_restart_summary": resume_summary.to_dict(),
            "summary_path": str(SUMMARY_PATH),
        }


def _run_controlled_failure(
    root: Path,
    run_id: str,
    failure_injection: ControlledExecutionFailureInjection,
) -> dict[str, Any]:
    runtime_dir = root / f"{run_id}_runtime"
    report_dir = root / f"{run_id}_reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=root / f"{run_id}_prepare_reports",
    )
    return build_full_range_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=4,
        run_id=run_id,
        failure_injection=failure_injection,
    )


def _build_resume_fixture(root: Path):
    runtime_dir = root / "resume_runtime"
    report_dir = root / "resume_reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=root / "resume_prepare_reports",
    )
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format="jsonl")
    if discovery.path is None or discovery.storage_format is None:
        raise RuntimeError("resume fixture normalized data was not found")
    records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    plans = build_full_range_chunk_plan(records, run_id="resume", data_source_type="mock", max_codes_per_chunk=1)
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    output_path = paths.feature_dir / "resume_success.json"
    audit_path = paths.audit_dir / "resume_success_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('{"rows":[]}\n', encoding="utf-8")
    audit_path.write_text('{"status":"OK"}\n', encoding="utf-8")
    _write_manifest(paths, plans[0], "resume_success", "SUCCESS", output_path=output_path, audit_path=audit_path)
    _write_manifest(paths, plans[1], "resume_failed", "FAILED")
    _write_manifest(paths, plans[2], "resume_missing_output", "SUCCESS", output_path=paths.feature_dir / "missing.json", audit_path=audit_path)
    _write_manifest(paths, plans[3], "resume_unknown", "ODD_STATUS")
    _write_manifest(paths, plans[0], "resume_duplicate", "SUCCESS", output_path=output_path, audit_path=audit_path, file_suffix="a")
    _write_manifest(paths, plans[0], "resume_duplicate", "SUCCESS", output_path=output_path, audit_path=audit_path, file_suffix="b")
    partial = paths.tmp_dir / "partial" / "chunk.tmp.json"
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text('{"partial":true}\n', encoding="utf-8")
    return check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)


def _write_manifest(
    paths,
    plan,
    chunk_id: str,
    status: str,
    *,
    output_path: Path | None = None,
    audit_path: Path | None = None,
    file_suffix: str | None = None,
) -> Path:
    suffix = f"_{file_suffix}" if file_suffix else ""
    path = paths.manifest_dir / f"{chunk_id}{suffix}_chunk_manifest.json"
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
        error_message=None if status == "SUCCESS" else f"{status} fixture",
    )
    _write_json(path, manifest.to_dict())
    return path


def _manifest_status(path: object) -> str | None:
    if not path:
        return None
    return json.loads(Path(str(path)).read_text(encoding="utf-8")).get("status")


def _run_manifest_counts_ok(summary: dict[str, Any]) -> bool:
    path = summary.get("run_manifest_path")
    if not path:
        return False
    payload = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    return payload.get("completed_chunk_count") == 0 and payload.get("failed_chunk_count") == 1


def _small_failure_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "controlled_status": summary.get("controlled_status"),
        "schema_validation_status": summary.get("schema_validation_status"),
        "leakage_audit_status": summary.get("leakage_audit_status"),
        "feature_output_path": summary.get("feature_output_path"),
        "tmp_output_path": summary.get("tmp_output_path"),
        "chunk_manifest_path": summary.get("chunk_manifest_path"),
        "run_manifest_path": summary.get("run_manifest_path"),
        "error_message": summary.get("error_message"),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
