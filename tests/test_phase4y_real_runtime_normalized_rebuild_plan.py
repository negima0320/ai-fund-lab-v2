from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import append_manifest_record, create_storage_backend
from ai_fund_lab_v2.data_store.manifest import manifest_path, sanitize_request_params
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4y_real_runtime_normalized_rebuild_plan import (
    READY,
    build_real_runtime_normalized_rebuild_plan_summary,
    run_audit,
)
from scripts.prepare_phase4k_normalized_history import build_mock_daily_quote_raw_records, prepare_mock_normalized_history


def test_rebuild_plan_ready_with_isolated_output_when_mock_would_be_overwritten(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    _write_raw_daily_quotes(runtime_dir)
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=66,
        code_count=5,
        output_format="jsonl",
        report_dir=report_dir / "candidate_ai",
    )

    summary = build_real_runtime_normalized_rebuild_plan_summary(runtime_dir=runtime_dir)

    assert summary["status"] == "READY"
    assert summary["readiness_status"] == READY
    assert summary["api_call_performed"] is False
    assert summary["raw_daily_quotes_detected"] is True
    assert summary["safe_rebuild_possible"] is True
    assert summary["would_overwrite_mock_history"] is True
    assert summary["isolated_output_path"].endswith("raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet")
    assert summary["isolated_output_overwrites_mock"] is False
    assert summary["schema_mapping_defined"] is True
    assert summary["provenance_manifest_defined"] is True
    assert summary["promotion_condition_defined"] is True
    assert summary["rollback_plan_defined"] is True
    assert summary["normalized_rebuild_executed"] is False
    assert summary["mock_history_overwritten"] is False
    assert not Path(summary["isolated_output_path"]).exists()
    assert summary["expected_normalized_row_count"] > 0
    assert summary["existing_normalized_data_source_type"] == "mock"
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_rebuild_plan_skips_without_raw(tmp_path: Path) -> None:
    summary = build_real_runtime_normalized_rebuild_plan_summary(runtime_dir=tmp_path / "runtime")

    assert summary["status"] == "SKIPPED"
    assert summary["readiness_status"] == "SKIPPED_NO_RAW"
    assert summary["raw_daily_quotes_detected"] is False
    assert summary["normalized_rebuild_executed"] is False


def test_rebuild_plan_uses_existing_real_normalized_as_not_mock(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    raw_records = _write_raw_daily_quotes(runtime_dir)
    normalized, _ = normalize_daily_quotes(raw_records)
    paths = RuntimePaths(runtime_dir=runtime_dir)
    output_path = write_daily_quotes_normalized(paths, "jsonl", normalized)
    append_manifest_record(
        manifest_path(paths.raw_data),
        {
            "endpoint": "daily_quotes_normalized",
            "source_endpoint": "/v2/equities/bars/daily",
            "normalized_endpoint": "daily_quotes_normalized",
            "status": "NORMALIZED",
            "storage_format": "jsonl",
            "storage_path": str(output_path),
            "output_record_count": len(normalized),
            "validation_status": "OK",
        },
    )

    summary = build_real_runtime_normalized_rebuild_plan_summary(runtime_dir=runtime_dir)

    assert summary["status"] == "READY"
    assert summary["readiness_status"] == READY
    assert summary["would_overwrite_mock_history"] is False
    assert summary["isolated_output_overwrites_mock"] is False


def test_phase4y_audit_completes(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    _write_raw_daily_quotes(runtime_dir)
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=66,
        code_count=5,
        output_format="jsonl",
        report_dir=report_dir / "candidate_ai",
    )
    result = run_audit(
        runtime_dir=runtime_dir,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "phase4y.json",
        markdown_report_path=tmp_path / "phase4y.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "phase4y.json").is_file()
    assert (tmp_path / "phase4y.md").is_file()


def test_phase4y_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4y_real_runtime_normalized_rebuild_plan.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["api_call_not_performed"]
    assert payload["checks"]["normalized_rebuild_not_executed"]


def _write_raw_daily_quotes(runtime_dir: Path) -> list[dict[str, object]]:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    paths.ensure_base_dirs()
    raw_records = build_mock_daily_quote_raw_records(start_date="2026-06-01", business_days=1, code_count=5)
    raw_base = paths.raw_data / "jquants" / "equities_bars_daily" / "data"
    raw_path = create_storage_backend("jsonl").path_for(raw_base)
    create_storage_backend("jsonl").write_records(raw_path, raw_records)
    append_manifest_record(
        manifest_path(paths.raw_data),
        {
            "created_at": "2026-06-12T00:00:00+00:00",
            "endpoint": "/v2/equities/bars/daily",
            "source_endpoint": "/v2/equities/bars/daily",
            "status": "FETCHED",
            "storage_format": "jsonl",
            "storage_path": str(raw_path),
            "record_count": len(raw_records),
            "validation_status": "OK",
            "request_params": sanitize_request_params({"endpoint_name": "daily_quotes"}),
        },
    )
    return raw_records
