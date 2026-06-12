from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    NO_WRITE_GATE_BLOCKED_BY_CHUNK_PLAN,
    NO_WRITE_GATE_BLOCKED_BY_RESUME_STATE,
    NO_WRITE_GATE_READY,
    audit_chunk_plan_distribution,
    build_full_range_chunk_plan,
    build_full_range_no_write_summary,
    check_resume_restart,
    evaluate_no_write_final_gate,
    resolve_full_range_paths,
    validate_chunks_no_write,
)
from scripts.audit_phase4n_full_range_no_write_gate import run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_chunk_plan_distribution_audit_ok() -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock", max_codes_per_chunk=2)

    audit = audit_chunk_plan_distribution(plans)

    assert audit.status == "OK"
    assert audit.chunk_count == 2
    assert audit.date_chunk_count == 2
    assert audit.code_chunk_count == 1
    assert audit.duplicate_chunk_id_count == 0
    assert audit.empty_chunk_ids == ()


def test_chunk_plan_distribution_detects_duplicate_and_empty() -> None:
    records = [{"Date": "2026-03-30", "Code": "11110"}]
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock")
    duplicate = [plans[0], plans[0]]

    audit = audit_chunk_plan_distribution(duplicate)

    assert audit.status == "ERROR"
    assert audit.duplicate_chunk_id_count == 1


def test_no_write_chunk_validation_ok(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock", max_codes_per_chunk=2)
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    result = validate_chunks_no_write(records, plans, paths=paths)

    assert result.status == "OK"
    assert result.checked_chunk_count == 2
    assert result.chunks_with_input_rows == 2
    assert result.schema_validation_status == "OK"
    assert result.leakage_audit_status == "OK"
    assert result.feature_output_written is False


def test_no_write_final_gate_ready(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock", max_codes_per_chunk=2)
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")
    distribution = audit_chunk_plan_distribution(plans)
    validation = validate_chunks_no_write(records, plans, paths=paths)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)

    gate = evaluate_no_write_final_gate(
        distribution=distribution,
        resume=resume,
        validation=validation,
        data_source_type="mock",
        feature_version=plans[0].feature_version,
        schema_version=plans[0].schema_version,
    )

    assert gate == NO_WRITE_GATE_READY


def test_no_write_final_gate_blocks_chunk_plan(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock")
    distribution = audit_chunk_plan_distribution([plans[0], plans[0]])
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")
    validation = validate_chunks_no_write(records, plans, paths=paths)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)

    gate = evaluate_no_write_final_gate(
        distribution=distribution,
        resume=resume,
        validation=validation,
        data_source_type="mock",
        feature_version=plans[0].feature_version,
        schema_version=plans[0].schema_version,
    )

    assert gate == NO_WRITE_GATE_BLOCKED_BY_CHUNK_PLAN


def test_resume_restart_abnormal_cases(tmp_path: Path) -> None:
    plans = build_full_range_chunk_plan(_records(), run_id="run", data_source_type="mock", max_codes_per_chunk=1)
    manifest_dir = tmp_path / "manifests"
    tmp_dir = tmp_path / "tmp"
    manifest_dir.mkdir()
    tmp_dir.mkdir()
    success = plans[0]
    failed = plans[1]
    (manifest_dir / f"{success.chunk_id}_chunk_manifest.json").write_text(
        json.dumps({"chunk_id": success.chunk_id, "status": "SUCCESS", "output_path": str(tmp_path / "missing_output.json")}),
        encoding="utf-8",
    )
    (manifest_dir / f"{failed.chunk_id}_chunk_manifest.json").write_text(
        json.dumps({"chunk_id": failed.chunk_id, "status": "FAILED"}),
        encoding="utf-8",
    )
    (manifest_dir / "unknown_status_chunk_manifest.json").write_text(
        json.dumps({"chunk_id": "unknown-status", "status": "MYSTERY"}),
        encoding="utf-8",
    )
    (tmp_dir / "partial.tmp").write_text("partial", encoding="utf-8")

    summary = check_resume_restart(plans, manifest_dir=manifest_dir, tmp_dir=tmp_dir)

    assert success.chunk_id in summary.completed_chunk_ids
    assert failed.chunk_id in summary.failed_chunk_ids
    assert summary.missing_chunk_ids
    assert summary.partial_tmp_paths
    assert any("missing_output_path" in item for item in summary.manifest_inconsistencies)
    assert any("unknown_status" in item for item in summary.manifest_inconsistencies)


def test_no_write_final_gate_blocks_resume_state(tmp_path: Path) -> None:
    plans = build_full_range_chunk_plan(_records(), run_id="run", data_source_type="mock")
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")
    paths.tmp_dir.mkdir(parents=True)
    (paths.tmp_dir / "partial.tmp").write_text("partial", encoding="utf-8")
    distribution = audit_chunk_plan_distribution(plans)
    validation = validate_chunks_no_write(_records(), plans, paths=paths)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)

    gate = evaluate_no_write_final_gate(
        distribution=distribution,
        resume=resume,
        validation=validation,
        data_source_type="mock",
        feature_version=plans[0].feature_version,
        schema_version=plans[0].schema_version,
    )

    assert gate == NO_WRITE_GATE_BLOCKED_BY_RESUME_STATE


def test_no_write_cli_outputs_ready_summary(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "prep")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_candidate_features_full_range_no_write.py",
            "--runtime-dir",
            str(runtime_dir),
            "--report-dir",
            str(report_dir),
            "--input-format",
            "jsonl",
            "--max-codes-per-chunk",
            "2",
            "--run-id",
            "test_no_write",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["gate_status"] == "READY_FOR_FULL_RANGE_EXECUTION"
    assert payload["feature_generation_executed"] is False
    assert payload["feature_output_written"] is False
    assert Path(payload["summary_path"]).is_file()


def test_no_write_summary_skips_without_data(tmp_path: Path) -> None:
    summary = build_full_range_no_write_summary(runtime_dir=tmp_path / "missing", report_dir=tmp_path / "reports", run_id="skip")

    assert summary["status"] == "SKIPPED"
    assert summary["gate_status"] == "SKIPPED_NO_DATA"
    assert summary["feature_output_written"] is False


def test_phase4n_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4n.json",
        markdown_report_path=tmp_path / "phase4n.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["no_write_cli_exists"]
    assert result["checks"]["final_gate_exists"]
    assert (tmp_path / "phase4n.json").is_file()
    assert (tmp_path / "phase4n.md").is_file()


def test_phase4n_does_not_add_generation_training_or_trading_code() -> None:
    source = "\n".join(
        [
            Path("src/ai_fund_lab_v2/candidate_ai/full_range.py").read_text(encoding="utf-8"),
            Path("scripts/check_candidate_features_full_range_no_write.py").read_text(encoding="utf-8"),
            Path("scripts/audit_phase4n_full_range_no_write_gate.py").read_text(encoding="utf-8"),
        ]
    )

    for forbidden in ("def train", "def predict", "def backtest", "def generate_labels", "submit_order", "place_order"):
        assert forbidden not in source


def _records() -> list[dict[str, object]]:
    return [
        {"Date": "2026-03-30", "Code": "11110", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
        {"Date": "2026-03-31", "Code": "22220", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
        {"Date": "2026-04-01", "Code": "11110", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
        {"Date": "2026-04-02", "Code": "22220", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
    ]
