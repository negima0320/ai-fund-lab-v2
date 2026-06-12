from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4k_normalized_history_readiness import inspect_normalized_history, run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_phase4k_audit_script_runs(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "reports")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_phase4k_normalized_history_readiness.py",
            "--runtime-dir",
            str(runtime_dir),
            "--input-format",
            "jsonl",
            "--max-codes",
            "3",
            "--max-rows",
            "180",
            "--json-report",
            str(tmp_path / "audit.json"),
            "--markdown-report",
            str(tmp_path / "audit.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["readiness_status"] == "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_history_inspection_outputs_business_day_and_per_code_stats(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=4, output_format="jsonl", report_dir=tmp_path / "reports")

    history = inspect_normalized_history(runtime_dir=runtime_dir, input_format="jsonl", min_lookback_rows=60)

    assert history["business_day_count"] == 65
    assert history["code_count"] == 4
    assert history["row_count"] == 260
    assert history["per_code_row_count_min"] == 65
    assert history["per_code_row_count_max"] == 65
    assert history["codes_with_sufficient_lookback"] == 4
    assert history["codes_with_insufficient_lookback"] == 0


def test_phase4k_audit_blocks_when_history_is_short(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    paths = RuntimePaths(runtime_dir=runtime_dir)
    normalized, _ = normalize_daily_quotes(
        [{"Date": "2026-06-01", "Code": "11110", "O": 10, "H": 12, "L": 9, "C": 11, "Vo": 1000}]
    )
    write_daily_quotes_normalized(paths, "jsonl", normalized)

    result = run_audit(
        runtime_dir=runtime_dir,
        input_format="jsonl",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "incomplete"
    assert result["readiness_status"] == "BLOCKED_BY_DATA_WINDOW"
    assert result["normalized_history"]["business_day_count"] == 1
    assert result["prepared_dry_run_summary"]["eligible_count"] == 0


def test_phase4k_audit_ready_when_history_is_sufficient(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=5, output_format="jsonl", report_dir=tmp_path / "reports")

    result = run_audit(
        runtime_dir=runtime_dir,
        input_format="jsonl",
        max_codes=5,
        max_rows=300,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"
    assert result["data_source_type"] == "mock"
    assert result["prepared_dry_run_summary"]["eligible_count"] > 0
    assert result["prepared_dry_run_summary"]["schema_validation_status"] == "OK"
    assert result["prepared_dry_run_summary"]["leakage_audit_status"] == "OK"


def test_phase4k_prepare_does_not_require_real_api(tmp_path: Path) -> None:
    summary = prepare_mock_normalized_history(runtime_dir=tmp_path / "runtime", business_days=60, code_count=2, output_format="jsonl", report_dir=tmp_path / "reports")

    assert summary["status"] == "OK"
    assert summary["data_source_type"] == "mock"
    assert summary["api_call"] is False
    assert Path(summary["normalized_storage_path"]).is_file()


def test_phase4k_outputs_have_no_sensitive_values(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "reports")
    result = run_audit(
        runtime_dir=runtime_dir,
        input_format="jsonl",
        max_codes=3,
        max_rows=180,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )
    combined = json.dumps(result, ensure_ascii=True) + (tmp_path / "audit.md").read_text(encoding="utf-8")

    for forbidden in ("secret-auth-id", "secret-password", "secret-token", "secret-cookie", "second-password"):
        assert forbidden not in combined


def test_phase4k_no_training_inference_backtest_or_trading_implementation() -> None:
    source = "\n".join(
        [
            Path("scripts/prepare_phase4k_normalized_history.py").read_text(encoding="utf-8"),
            Path("scripts/audit_phase4k_normalized_history_readiness.py").read_text(encoding="utf-8"),
        ]
    )

    for forbidden in ("def train", "def predict", "def backtest", "def generate_labels", "submit_order", "place_order"):
        assert forbidden not in source
