from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.data_store import append_manifest_record, create_storage_backend
from ai_fund_lab_v2.data_store.manifest import manifest_path, sanitize_request_params
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4z_real_runtime_normalized_isolated import run_audit
from scripts.prepare_phase4k_normalized_history import build_mock_daily_quote_raw_records, prepare_mock_normalized_history
from scripts.rebuild_phase4z_real_runtime_normalized_isolated import (
    READY,
    rebuild_isolated_real_runtime_normalized,
)


def test_isolated_rebuild_writes_real_runtime_output_without_mock_overwrite(tmp_path: Path) -> None:
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
    default_mock_path = runtime_dir / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    # The fixture used jsonl for mock, while phase output uses parquet by default. Track whichever exists.
    if not default_mock_path.exists():
        default_mock_path = default_mock_path.with_suffix(".jsonl")
    before = _file_hash(default_mock_path)

    summary = rebuild_isolated_real_runtime_normalized(
        runtime_dir=runtime_dir,
        report_dir=report_dir / "full_range",
        input_format="jsonl",
        output_format="jsonl",
    )

    assert summary["status"] == "OK"
    assert summary["coverage_status"] == READY
    assert summary["data_source_type"] == "real_runtime"
    assert summary["api_call_performed"] is False
    assert Path(summary["isolated_output_path"]).is_file()
    assert Path(summary["isolated_manifest_path"]).is_file()
    assert summary["default_mock_path_unchanged"] is True
    assert summary["mock_history_overwritten"] is False
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False
    assert _file_hash(default_mock_path) == before
    assert summary["row_count"] > 0
    assert summary["code_count"] > 0
    assert summary["schema_mapping_status"] == "OK"
    assert "insufficient for 60-day" in summary["coverage_status_detail"]
    manifest = json.loads(Path(summary["isolated_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["data_source_type"] == "real_runtime"
    assert manifest["source_provider"] == "jquants"
    assert manifest["api_call_performed"] is False
    assert manifest["promotion_status"] == "not_promoted"
    assert manifest["mock_history_overwritten"] is False


def test_isolated_rebuild_blocks_missing_raw(tmp_path: Path) -> None:
    summary = rebuild_isolated_real_runtime_normalized(runtime_dir=tmp_path / "runtime", report_dir=tmp_path / "reports")

    assert summary["status"] == "BLOCKED"
    assert summary["coverage_status"] == "BLOCKED_BY_MISSING_RAW"
    assert summary["row_count"] == 0
    assert summary["mock_history_overwritten"] is False


def test_phase4z_audit_completes(tmp_path: Path) -> None:
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
    summary = rebuild_isolated_real_runtime_normalized(
        runtime_dir=runtime_dir,
        report_dir=report_dir / "full_range",
        input_format="jsonl",
        output_format="jsonl",
    )
    result = run_audit(
        runtime_dir=runtime_dir,
        report_dir=report_dir / "full_range",
        summary_path=Path(summary["summary_path"]),
        json_report_path=tmp_path / "phase4z.json",
        markdown_report_path=tmp_path / "phase4z.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert (tmp_path / "phase4z.json").is_file()
    assert (tmp_path / "phase4z.md").is_file()


def test_phase4z_scripts_run() -> None:
    rebuild = subprocess.run(
        [sys.executable, "scripts/rebuild_phase4z_real_runtime_normalized_isolated.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rebuild.returncode == 0
    rebuild_payload = json.loads(rebuild.stdout[rebuild.stdout.find("{") :])
    assert rebuild_payload["promotion_performed"] is False
    assert rebuild_payload["mock_history_overwritten"] is False

    audit = subprocess.run(
        [sys.executable, "scripts/audit_phase4z_real_runtime_normalized_isolated.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert audit.returncode == 0
    audit_payload = json.loads(audit.stdout)
    assert audit_payload["status"] == "complete"
    assert audit_payload["checks"]["reader_switch_not_performed"]


def _write_raw_daily_quotes(runtime_dir: Path) -> None:
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


def _file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
