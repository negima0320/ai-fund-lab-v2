from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4w_real_runtime_coverage import READY, build_real_runtime_coverage_summary, run_audit
from scripts.prepare_phase4k_normalized_history import build_mock_daily_quote_raw_records, prepare_mock_normalized_history


def test_real_runtime_coverage_skips_phase4k_mock_history(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=66,
        code_count=5,
        output_format="jsonl",
        report_dir=report_dir / "candidate_ai",
    )

    summary = build_real_runtime_coverage_summary(runtime_dir=runtime_dir, report_dir=report_dir / "full_range", input_format="jsonl")

    assert summary["status"] == "SKIPPED"
    assert summary["readiness_status"] == "SKIPPED_NO_REAL_RUNTIME_DATA"
    assert summary["api_call_performed"] is False
    assert summary["mock_history_detected"] is True
    assert summary["real_runtime_history_detected"] is False
    assert summary["selected_data_source_type"] == "mock"
    assert summary["row_count"] > 0
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_real_runtime_coverage_ready_for_real_runtime_fixture(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    _write_real_runtime_normalized_fixture(runtime_dir, business_days=66, code_count=4)

    summary = build_real_runtime_coverage_summary(runtime_dir=runtime_dir, report_dir=tmp_path / "reports", input_format="jsonl")

    assert summary["status"] == "READY"
    assert summary["readiness_status"] == READY
    assert summary["api_call_performed"] is False
    assert summary["mock_history_detected"] is False
    assert summary["real_runtime_history_detected"] is True
    assert summary["selected_data_source_type"] == "real_runtime"
    assert summary["business_day_count"] == 66
    assert summary["code_count"] == 4
    assert summary["row_count"] == 264
    assert summary["per_code_row_count_min"] == 66
    assert summary["per_code_row_count_max"] == 66
    assert summary["codes_with_60_business_day_lookback"] == 4
    assert summary["codes_without_60_business_day_lookback"] == 0
    assert summary["estimated_chunk_count"] > 0
    assert summary["estimated_feature_rows"] == 264
    assert summary["runtime_free_space_sufficient"] is True
    assert summary["recommended_max_chunks_first_run"] == 4


def test_real_runtime_coverage_blocks_insufficient_real_runtime_history(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    _write_real_runtime_normalized_fixture(runtime_dir, business_days=20, code_count=3)

    summary = build_real_runtime_coverage_summary(runtime_dir=runtime_dir, report_dir=tmp_path / "reports", input_format="jsonl")

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_REAL_RUNTIME_DATA_COVERAGE"
    assert summary["real_runtime_history_detected"] is True
    assert summary["business_day_count"] == 20
    assert summary["codes_with_60_business_day_lookback"] == 0


def test_phase4w_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        runtime_dir=tmp_path / "runtime",
        report_dir=tmp_path / "reports",
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "phase4w.json",
        markdown_report_path=tmp_path / "phase4w.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "phase4w.json").is_file()
    assert (tmp_path / "phase4w.md").is_file()


def test_phase4w_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4w_real_runtime_coverage.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["api_call_not_performed"]
    assert payload["checks"]["mock_history_not_misclassified_as_real_runtime"]


def _write_real_runtime_normalized_fixture(runtime_dir: Path, *, business_days: int, code_count: int) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    paths.ensure_base_dirs()
    raw = build_mock_daily_quote_raw_records(
        start_date="2026-03-02",
        business_days=business_days,
        code_count=code_count,
    )
    normalized, _ = normalize_daily_quotes(raw)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
