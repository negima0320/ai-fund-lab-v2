from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai import (
    DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING,
    STANDARD_INPUT_COLUMNS,
    adapt_daily_quotes_normalized,
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    build_source_snapshot_id,
    validate_daily_quotes_normalized_input,
    write_candidate_loader_contract_outputs,
)
from scripts.audit_phase4f_candidate_real_data_loader_contract import run_audit


def normalized_records() -> list[dict[str, object]]:
    return [
        {"Date": "2026-05-29", "Code": "72030", "Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1000},
        {"Date": "2026-06-01", "Code": "72030", "Open": 108, "High": 112, "Low": 106, "Close": 111, "Volume": 1200},
        {"Date": "2026-06-02", "Code": "72030", "Open": 999, "High": 999, "Low": 999, "Close": 999, "Volume": 9999},
    ]


def test_daily_quotes_normalized_mapping_is_defined() -> None:
    assert DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING == {
        "Date": "date",
        "Code": "code",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    assert STANDARD_INPUT_COLUMNS == ("date", "code", "open", "high", "low", "close", "volume")


def test_input_schema_validation_accepts_future_rows_as_droppable() -> None:
    result = validate_daily_quotes_normalized_input(normalized_records(), as_of_date="2026-06-01")

    assert result.is_valid
    assert result.future_row_count == 1
    assert result.missing_required_fields == {}


def test_input_schema_validation_detects_missing_close_and_volume() -> None:
    records = [{"Date": "2026-06-01", "Code": "72030", "Open": 1, "High": 2, "Low": 1, "Close": None, "Volume": ""}]

    result = validate_daily_quotes_normalized_input(records, as_of_date="2026-06-01")

    assert not result.is_valid
    assert result.missing_close_count == 1
    assert result.missing_volume_count == 1


def test_adapter_outputs_candidate_builder_standard_rows_and_filters_future() -> None:
    result = adapt_daily_quotes_normalized(normalized_records(), as_of_date="2026-06-01")

    assert result.audit.dropped_future_row_count == 1
    assert result.audit.filtered_row_count == 2
    assert all(set(STANDARD_INPUT_COLUMNS).issubset(row) for row in result.rows)
    assert all(row["date"] <= "2026-06-01" for row in result.rows)
    assert result.rows[-1]["close"] == 111.0


def test_adapter_records_source_snapshot_id_and_hash() -> None:
    records = normalized_records()
    result = adapt_daily_quotes_normalized(records, as_of_date="2026-06-01")

    assert result.audit.source_snapshot_id == build_source_snapshot_id(records, as_of_date="2026-06-01")
    assert result.audit.input_hash_optional
    assert result.audit.schema_version
    assert result.audit.loader_version


def test_loader_manifest_outputs_are_written_under_runtime(tmp_path: Path) -> None:
    result = adapt_daily_quotes_normalized(normalized_records(), as_of_date="2026-06-01")

    paths = write_candidate_loader_contract_outputs(result.rows, audit=result.audit, runtime_dir=tmp_path / ".runtime")

    assert paths["rows"].is_file()
    assert paths["manifest"].is_file()
    assert paths["audit"].is_file()
    assert paths["rows"].parent == tmp_path / ".runtime" / "candidate_ai" / "tmp"
    assert paths["manifest"].parent == tmp_path / ".runtime" / "candidate_ai" / "manifests"
    assert paths["audit"].parent == tmp_path / ".runtime" / "candidate_ai" / "audit"
    saved_manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert saved_manifest["dropped_future_row_count"] == 1


def test_check_candidate_real_data_loader_contract_script_runs(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_candidate_real_data_loader_contract.py",
            "--runtime-dir",
            str(tmp_path / ".runtime"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)

    assert summary["status"] == "WARNING"
    assert summary["dropped_future_row_count"] == 1
    assert Path(summary["manifest_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()


def test_phase4e_mock_builder_still_passes() -> None:
    result = build_candidate_features_mock_with_audit(build_mock_daily_quotes_normalized(), as_of_date="2026-06-01")

    assert result.validation.is_valid
    assert result.audit.status == "OK"


def test_phase4f_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4f_audit.json"
    markdown_report = tmp_path / "phase4f_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert result["status"] == "complete"
    assert json_report.is_file()
    assert markdown_report.is_file()
    assert result["checks"]["future_rows_filtered"]
    assert result["checks"]["phase4e_mock_builder_compatible"]


def test_phase4f_outputs_have_no_sensitive_values(tmp_path: Path) -> None:
    result = adapt_daily_quotes_normalized(normalized_records(), as_of_date="2026-06-01")
    paths = write_candidate_loader_contract_outputs(result.rows, audit=result.audit, runtime_dir=tmp_path / ".runtime")
    combined = "".join(path.read_text(encoding="utf-8") for path in paths.values())

    for forbidden in ["secret-auth-id", "secret-password", "secret-token", "secret-cookie", "https://example.invalid"]:
        assert forbidden not in combined
