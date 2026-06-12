#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    build_first_controlled_batch_summary,
    build_full_range_resume_controlled_summary,
    resolve_full_range_paths,
)

PHASE4T_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4t_post_batch_integrity_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4u_controlled_batch_expansion_summary.json")
READY_FOR_EXPANSION = "READY_FOR_CONTROLLED_BATCH_EXPANSION"
EXPANSION_COMPLETED = "CONTROLLED_BATCH_EXPANSION_COMPLETED"
EXPANSION_BLOCKED = "CONTROLLED_BATCH_EXPANSION_BLOCKED"
EXPANSION_FAILED = "CONTROLLED_BATCH_EXPANSION_FAILED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute the Phase4-U controlled Candidate feature batch expansion.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("auto", "jsonl", "parquet"), default="auto")
    parser.add_argument("--max-codes-per-chunk", type=int, default=30)
    parser.add_argument("--max-chunks-to-execute", type=int, default=4)
    parser.add_argument("--data-source-type", choices=("mock", "real_runtime", "skipped"), default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = build_controlled_batch_expansion_summary(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        max_codes_per_chunk=args.max_codes_per_chunk,
        max_chunks_to_execute=args.max_chunks_to_execute,
        data_source_type=args.data_source_type,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"OK", "BLOCKED", "SKIPPED"} else 1


def build_controlled_batch_expansion_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = 30,
    max_chunks_to_execute: int = 4,
    data_source_type: str | None = None,
    run_id: str | None = None,
    phase4t_integrity_summary: dict[str, Any] | None = None,
    phase4t_summary_path: Path | str = PHASE4T_SUMMARY_PATH,
) -> dict[str, Any]:
    run_id = run_id or f"phase4u_expansion_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    summary_path = Path(report_dir) / SUMMARY_PATH.name
    phase4t_gate = phase4t_integrity_summary or _read_json_optional(Path(phase4t_summary_path))
    gate_status = _evaluate_phase4t_gate(phase4t_gate)
    if gate_status != "READY":
        summary = _base_summary(
            status="BLOCKED",
            expansion_status=EXPANSION_BLOCKED,
            integrity_gate_status=gate_status,
            run_id=run_id,
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary["stop_reason"] = "Phase4-T integrity gate is not READY"
        _write_json(summary_path, summary)
        return summary

    if max_chunks_to_execute != 4:
        summary = _base_summary(
            status="BLOCKED",
            expansion_status=EXPANSION_BLOCKED,
            integrity_gate_status=gate_status,
            run_id=run_id,
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary["stop_reason"] = "Phase4-U requires max_chunks_to_execute=4"
        _write_json(summary_path, summary)
        return summary

    first_batch = build_first_controlled_batch_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format=input_format,
        max_codes_per_chunk=max_codes_per_chunk,
        max_chunks_to_execute=2,
        data_source_type=data_source_type,
        run_id=run_id,
    )
    if first_batch.get("status") != "OK":
        summary = _base_summary(
            status="BLOCKED",
            expansion_status=EXPANSION_BLOCKED,
            integrity_gate_status=gate_status,
            run_id=run_id,
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary.update(
            {
                "planned_chunk_count": first_batch.get("planned_chunk_count", 0),
                "stop_reason": "first controlled batch source could not be prepared",
                "first_batch_summary": _compact_phase4s_summary(first_batch),
            }
        )
        _write_json(summary_path, summary)
        return summary

    runner = build_full_range_resume_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format=input_format,
        max_codes_per_chunk=max_codes_per_chunk,
        max_chunks_to_execute=max_chunks_to_execute,
        max_allowed_chunks=4,
        data_source_type=data_source_type,
        run_id=run_id,
        stop_on_first_failure=True,
        max_failed_chunks_allowed=0,
    )
    post_integrity = build_post_expansion_integrity(run_id=run_id, runtime_dir=runtime_dir, report_dir=report_dir)
    failed_count = int(runner.get("failed_chunk_count") or 0)
    schema_status = str(runner.get("schema_validation_status") or "UNKNOWN")
    leakage_status = str(runner.get("leakage_audit_status") or "UNKNOWN")
    integrity_ok = (
        post_integrity["tmp_leftover_count"] == 0
        and post_integrity["duplicate_output_count"] == 0
        and post_integrity["duplicate_manifest_count"] == 0
        and post_integrity["orphan_output_count"] == 0
        and post_integrity["orphan_manifest_count"] == 0
        and post_integrity["final_output_exists_count"] == post_integrity["success_manifest_count"]
        and post_integrity["run_manifest_completed_chunk_count"] == post_integrity["success_manifest_count"]
    )
    expansion_ok = runner.get("status") == "OK" and failed_count == 0 and schema_status == "OK" and leakage_status == "OK" and integrity_ok
    planned = int(runner.get("planned_chunk_count") or first_batch.get("planned_chunk_count") or 0)
    completed = int(runner.get("completed_chunk_count") or 0)
    remaining = max(0, planned - completed - failed_count)
    feature_output_written_count = sum(1 for item in runner.get("executions", []) if item.get("final_output_path"))
    summary = {
        "status": "OK" if expansion_ok else "ERROR",
        "expansion_status": EXPANSION_COMPLETED if expansion_ok else EXPANSION_FAILED,
        "integrity_gate_status": gate_status,
        "run_id": run_id,
        "max_chunks_to_execute": max_chunks_to_execute,
        "stop_on_first_failure": True,
        "max_failed_chunks_allowed": 0,
        "planned_chunk_count": planned,
        "existing_success_chunk_count": int(first_batch.get("completed_chunk_count") or 0),
        "skipped_success_chunk_count": int(runner.get("skipped_success_chunk_count") or 0),
        "executed_chunk_count": int(runner.get("executed_chunk_count") or 0),
        "completed_chunk_count": completed,
        "failed_chunk_count": failed_count,
        "remaining_missing_chunk_count": remaining,
        "feature_output_written_count": feature_output_written_count,
        "schema_validation_status": schema_status,
        "leakage_audit_status": leakage_status,
        "tmp_leftover_count": post_integrity["tmp_leftover_count"],
        "duplicate_output_count": post_integrity["duplicate_output_count"],
        "duplicate_manifest_count": post_integrity["duplicate_manifest_count"],
        "orphan_output_count": post_integrity["orphan_output_count"],
        "orphan_manifest_count": post_integrity["orphan_manifest_count"],
        "stopped_on_failure": bool(runner.get("stopped_on_failure")),
        "stop_reason": runner.get("stop_reason"),
        "runner_status": runner.get("runner_status"),
        "post_expansion_integrity": post_integrity,
        "first_batch_summary": _compact_phase4s_summary(first_batch),
        "runner_summary": _compact_runner_summary(runner),
        "feature_generation_executed": bool(runner.get("feature_generation_executed")),
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "recommended_next_action": "run Phase4-V controlled expansion readiness for larger mock/runtime coverage"
        if expansion_ok
        else "inspect Phase4-U stopped_on_failure, schema/leakage status, and post-expansion integrity before retrying",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_post_expansion_integrity(
    *,
    run_id: str,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
) -> dict[str, Any]:
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    manifest_paths = sorted(path for path in paths.manifest_dir.glob(f"{run_id}_*manifest.json") if not path.name.endswith("_run_manifest.json"))
    manifests = [_read_json_optional(path) for path in manifest_paths]
    manifests = [manifest for manifest in manifests if manifest]
    output_paths = [Path(str(manifest.get("output_path") or "")) for manifest in manifests if manifest.get("output_path")]
    audit_paths = [Path(str(manifest.get("audit_path") or "")) for manifest in manifests if manifest.get("audit_path")]
    success_manifests = [manifest for manifest in manifests if manifest.get("status") == "SUCCESS"]
    failed_manifests = [manifest for manifest in manifests if manifest.get("status") == "FAILED"]
    run_manifest_path = paths.manifest_dir / f"{run_id}_run_manifest.json"
    run_manifest = _read_json_optional(run_manifest_path)
    feature_run_dir = paths.feature_dir / run_id
    all_outputs = sorted(feature_run_dir.glob("*.json")) if feature_run_dir.exists() else []
    referenced_outputs = {str(path) for path in output_paths}
    tmp_run_dir = paths.tmp_dir / run_id
    tmp_leftovers = sorted(str(path) for path in tmp_run_dir.rglob("*") if path.is_file()) if tmp_run_dir.exists() else []
    chunk_ids = [str(manifest.get("chunk_id") or "") for manifest in manifests]
    return {
        "run_id": run_id,
        "final_output_exists_count": sum(1 for path in output_paths if path.is_file()),
        "chunk_manifest_count": len(manifest_paths),
        "chunk_audit_count": sum(1 for path in audit_paths if path.is_file()),
        "success_manifest_count": len(success_manifests),
        "failed_manifest_count": len(failed_manifests),
        "run_manifest_exists": run_manifest_path.is_file(),
        "run_manifest_completed_chunk_count": int(run_manifest.get("completed_chunk_count") or 0),
        "run_manifest_failed_chunk_count": int(run_manifest.get("failed_chunk_count") or 0),
        "tmp_leftover_count": len(tmp_leftovers),
        "tmp_leftover_paths": tmp_leftovers,
        "duplicate_output_count": len(output_paths) - len({str(path) for path in output_paths}),
        "duplicate_manifest_count": len(chunk_ids) - len(set(chunk_ids)),
        "orphan_output_count": sum(1 for path in all_outputs if str(path) not in referenced_outputs),
        "orphan_manifest_count": 0,
    }


def _evaluate_phase4t_gate(summary: dict[str, Any]) -> str:
    ready = (
        summary.get("integrity_status") == READY_FOR_EXPANSION
        and summary.get("tmp_leftover_count") == 0
        and summary.get("schema_validation_all_ok") is True
        and summary.get("leakage_audit_all_ok") is True
        and summary.get("resume_success_skip_ready") is True
        and summary.get("duplicate_output_count") == 0
        and summary.get("orphan_output_count") == 0
    )
    return "READY" if ready else "BLOCKED"


def _base_summary(
    *,
    status: str,
    expansion_status: str,
    integrity_gate_status: str,
    run_id: str,
    max_chunks_to_execute: int,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "status": status,
        "expansion_status": expansion_status,
        "integrity_gate_status": integrity_gate_status,
        "run_id": run_id,
        "max_chunks_to_execute": max_chunks_to_execute,
        "stop_on_first_failure": True,
        "max_failed_chunks_allowed": 0,
        "planned_chunk_count": 0,
        "existing_success_chunk_count": 0,
        "skipped_success_chunk_count": 0,
        "executed_chunk_count": 0,
        "completed_chunk_count": 0,
        "failed_chunk_count": 0,
        "remaining_missing_chunk_count": 0,
        "feature_output_written_count": 0,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "tmp_leftover_count": 0,
        "duplicate_output_count": 0,
        "duplicate_manifest_count": 0,
        "orphan_output_count": 0,
        "orphan_manifest_count": 0,
        "stopped_on_failure": False,
        "stop_reason": None,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "recommended_next_action": "fix the Phase4-T integrity gate before controlled expansion",
        "summary_path": str(summary_path),
    }


def _compact_phase4s_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "batch_status",
        "gate_status",
        "planned_chunk_count",
        "executed_chunk_count",
        "completed_chunk_count",
        "failed_chunk_count",
        "schema_validation_status",
        "leakage_audit_status",
    )
    return {key: summary.get(key) for key in keys}


def _compact_runner_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "runner_status",
        "planned_chunk_count",
        "skipped_success_chunk_count",
        "rerun_failed_chunk_count",
        "run_missing_chunk_count",
        "executed_chunk_count",
        "completed_chunk_count",
        "failed_chunk_count",
        "partial_tmp_warning_count",
        "blocked_inconsistency_count",
        "schema_validation_status",
        "leakage_audit_status",
        "tmp_to_final_atomic_move",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
