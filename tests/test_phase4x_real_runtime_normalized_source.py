from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import append_manifest_record, create_storage_backend
from ai_fund_lab_v2.data_store.manifest import manifest_path, sanitize_request_params
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4x_real_runtime_normalized_source import (
    READY_EXISTING,
    READY_REBUILD,
    build_real_runtime_normalized_source_summary,
    run_audit,
)
from scripts.prepare_phase4k_normalized_history import build_mock_daily_quote_raw_records, prepare_mock_normalized_history


def test_source_audit_ready_to_rebuild_from_raw_when_normalized_is_mock(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    _write_raw_daily_quotes(runtime_dir, with_manifest=True)
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=66,
        code_count=5,
        output_format="jsonl",
        report_dir=report_dir / "candidate_ai",
    )

    summary = build_real_runtime_normalized_source_summary(runtime_dir=runtime_dir)

    assert summary["status"] == "READY"
    assert summary["readiness_status"] == READY_REBUILD
    assert summary["api_call_performed"] is False
    assert summary["raw_daily_quotes_detected"] is True
    assert summary["normalized_daily_quotes_detected"] is True
    assert summary["mock_normalized_history_detected"] is True
    assert summary["real_runtime_normalized_detected"] is False
    assert summary["manifest_detected"] is True
    assert summary["fixture_detected"] is False
    assert summary["selected_data_source_type"] == "real_raw_jquants"
    assert summary["raw_row_count"] > 0
    assert summary["raw_code_count"] > 0
    assert summary["safe_rebuild_possible"] is True
    assert summary["would_overwrite_mock_history"] is True
    assert summary["normalizer_available"] is True
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_source_audit_ready_to_use_existing_real_runtime_normalized(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    raw_records = _write_raw_daily_quotes(runtime_dir, with_manifest=True)
    _write_real_normalized(runtime_dir, raw_records)

    summary = build_real_runtime_normalized_source_summary(runtime_dir=runtime_dir)

    assert summary["status"] == "READY"
    assert summary["readiness_status"] == READY_EXISTING
    assert summary["mock_normalized_history_detected"] is False
    assert summary["real_runtime_normalized_detected"] is True
    assert summary["selected_data_source_type"] == "real_runtime"
    assert summary["selected_input_path"]
    assert summary["safe_rebuild_possible"] is True
    assert summary["would_overwrite_mock_history"] is False


def test_source_audit_blocks_raw_without_manifest(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    _write_raw_daily_quotes(runtime_dir, with_manifest=False)

    summary = build_real_runtime_normalized_source_summary(runtime_dir=runtime_dir)

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_MISSING_MANIFEST"
    assert summary["raw_daily_quotes_detected"] is True
    assert summary["manifest_detected"] is False
    assert summary["safe_rebuild_possible"] is False


def test_phase4x_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        runtime_dir=tmp_path / "runtime",
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "phase4x.json",
        markdown_report_path=tmp_path / "phase4x.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "phase4x.json").is_file()
    assert (tmp_path / "phase4x.md").is_file()


def test_phase4x_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4x_real_runtime_normalized_source.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["api_call_not_performed"]
    assert payload["checks"]["mock_history_not_misclassified"]


def _write_raw_daily_quotes(runtime_dir: Path, *, with_manifest: bool) -> list[dict[str, object]]:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    paths.ensure_base_dirs()
    raw_records = build_mock_daily_quote_raw_records(start_date="2026-06-01", business_days=1, code_count=5)
    raw_base = paths.raw_data / "jquants" / "equities_bars_daily" / "data"
    raw_path = create_storage_backend("jsonl").path_for(raw_base)
    create_storage_backend("jsonl").write_records(raw_path, raw_records)
    if with_manifest:
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


def _write_real_normalized(runtime_dir: Path, raw_records: list[dict[str, object]]) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    normalized, report = normalize_daily_quotes([dict(record) for record in raw_records])
    output_path = write_daily_quotes_normalized(paths, "jsonl", normalized)
    append_manifest_record(
        manifest_path(paths.raw_data),
        {
            "created_at": "2026-06-12T00:01:00+00:00",
            "endpoint": "daily_quotes_normalized",
            "source_endpoint": "/v2/equities/bars/daily",
            "normalized_endpoint": "daily_quotes_normalized",
            "status": "NORMALIZED",
            "storage_format": "jsonl",
            "storage_path": str(output_path),
            "input_record_count": len(raw_records),
            "output_record_count": len(normalized),
            "normalization_status": report.status,
            "validation_status": report.validation_status,
        },
    )
