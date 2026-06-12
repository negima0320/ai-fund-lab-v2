from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    CONTROLLED_EXECUTION_FAILED,
    CONTROLLED_EXECUTION_READY,
    build_full_range_chunk_plan,
    build_full_range_controlled_summary,
    execute_full_range_chunk_controlled,
    resolve_full_range_paths,
)
from scripts.audit_phase4o_full_range_controlled_execution import run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_controlled_execution_writes_tmp_then_final_and_manifest(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock", max_codes_per_chunk=2)
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    result = execute_full_range_chunk_controlled(records, plans[0], paths=paths, max_chunks_to_execute=1)

    assert result.status == CONTROLLED_EXECUTION_READY
    assert result.executed_chunk_count == 1
    assert result.row_count == 2
    assert result.schema_validation_status == "OK"
    assert result.leakage_audit_status == "OK"
    assert result.final_output_path is not None
    assert Path(result.final_output_path).is_file()
    assert result.tmp_output_path is not None
    assert not Path(result.tmp_output_path).exists()
    manifest = json.loads(Path(result.chunk_manifest_path).read_text(encoding="utf-8"))
    assert manifest["status"] == "SUCCESS"
    assert manifest["output_path"] == result.final_output_path


def test_controlled_execution_failed_manifest_without_final_output(tmp_path: Path) -> None:
    records = _records()
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock", max_codes_per_chunk=2)
    empty_plan = plans[0].__class__(**{**plans[0].to_dict(), "chunk_id": "empty", "codes": ("99990",), "code_count": 1})
    paths = resolve_full_range_paths(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    result = execute_full_range_chunk_controlled(records, empty_plan, paths=paths, max_chunks_to_execute=1)

    assert result.status == CONTROLLED_EXECUTION_FAILED
    assert result.final_output_path is None
    manifest = json.loads(Path(result.chunk_manifest_path).read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["output_path"] is None


def test_controlled_summary_updates_run_manifest(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "prep")

    summary = build_full_range_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=3,
        run_id="controlled",
    )

    assert summary["status"] == "OK"
    assert summary["executed_chunk_count"] == 1
    assert summary["feature_output_written"] is True
    run_manifest = json.loads(Path(summary["run_manifest_path"]).read_text(encoding="utf-8"))
    assert run_manifest["completed_chunk_count"] == 1
    assert run_manifest["failed_chunk_count"] == 0
    assert run_manifest["skipped_chunk_count"] >= 0
    assert run_manifest["last_updated_at"]


def test_controlled_summary_blocks_when_max_chunks_not_one(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "prep")

    summary = build_full_range_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=3,
        max_chunks_to_execute=2,
        run_id="blocked",
    )

    assert summary["status"] == "ERROR"
    assert summary["executed_chunk_count"] == 0
    assert summary["feature_output_written"] is False


def test_controlled_cli_runs_one_chunk(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "prep")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_candidate_features_full_range_controlled.py",
            "--runtime-dir",
            str(runtime_dir),
            "--report-dir",
            str(report_dir),
            "--input-format",
            "jsonl",
            "--max-codes-per-chunk",
            "3",
            "--run-id",
            "cli_controlled",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["executed_chunk_count"] == 1
    assert payload["max_chunks_to_execute"] == 1
    assert payload["feature_output_written"] is True
    assert Path(payload["feature_output_path"]).is_file()
    assert not Path(payload["tmp_output_path"]).exists()


def test_phase4o_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4o.json",
        markdown_report_path=tmp_path / "phase4o.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["only_one_minimal_chunk_executed"]
    assert result["checks"]["tmp_to_final_atomic_move_exists"]
    assert (tmp_path / "phase4o.json").is_file()
    assert (tmp_path / "phase4o.md").is_file()


def test_phase4o_does_not_add_label_training_or_trading_code() -> None:
    source = "\n".join(
        [
            Path("src/ai_fund_lab_v2/candidate_ai/full_range.py").read_text(encoding="utf-8"),
            Path("scripts/build_candidate_features_full_range_controlled.py").read_text(encoding="utf-8"),
            Path("scripts/audit_phase4o_full_range_controlled_execution.py").read_text(encoding="utf-8"),
        ]
    )

    for forbidden in ("def train", "def predict", "def backtest", "def generate_labels", "submit_order", "place_order"):
        assert forbidden not in source


def _records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day in range(1, 23):
        date = f"2026-03-{day:02d}"
        for code in ("11110", "22220"):
            records.append({"Date": date, "Code": code, "Open": 10 + day, "High": 12 + day, "Low": 9 + day, "Close": 11 + day, "Volume": 1000 + day})
    return records
