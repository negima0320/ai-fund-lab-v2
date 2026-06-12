from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai import (
    audit_feature_table,
    build_candidate_features_mock,
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    validate_feature_table,
    write_candidate_feature_outputs,
)
from scripts.audit_phase4e_candidate_feature_builder_mock import run_audit


def test_mock_feature_builder_outputs_required_columns() -> None:
    result = build_candidate_features_mock_with_audit(
        build_mock_daily_quotes_normalized(),
        as_of_date="2026-06-01",
    )

    assert result.validation.is_valid
    assert result.audit.status == "OK"
    assert result.audit.row_count == 2
    required = {
        "as_of_date",
        "target_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "universe_eligible",
        "excluded_reason",
    }
    assert all(required.issubset(row) for row in result.rows)


def test_mock_feature_builder_generates_expected_features() -> None:
    rows = build_candidate_features_mock(build_mock_daily_quotes_normalized(), as_of_date="2026-06-01")
    row = next(item for item in rows if item["code"] == "7203")

    assert row["universe_eligible"] is True
    assert row["excluded_reason"] == ""
    assert row["price_momentum_return_5d"] is not None
    assert row["price_momentum_return_20d"] is not None
    assert row["volume_momentum_ratio_5d"] is not None
    assert row["volatility_return_std_20d"] is not None
    assert row["trend_close_over_ma_20d"] is not None
    assert row["liquidity_avg_volume_20d"] is not None
    assert row["missing_flags_insufficient_lookback"] is False


def test_future_input_rows_are_ignored() -> None:
    source_rows = build_mock_daily_quotes_normalized()

    with_future = build_candidate_features_mock(source_rows, as_of_date="2026-06-01")
    without_future = build_candidate_features_mock(
        [row for row in source_rows if str(row["date"]) <= "2026-06-01"],
        as_of_date="2026-06-01",
    )

    assert [_without_created_at(row) for row in with_future] == [_without_created_at(row) for row in without_future]


def test_insufficient_lookback_is_excluded() -> None:
    rows = build_candidate_features_mock(build_mock_daily_quotes_normalized(), as_of_date="2026-06-01")
    row = next(item for item in rows if item["code"] == "9999")

    assert row["universe_eligible"] is False
    assert row["excluded_reason"] == "insufficient_lookback"
    assert row["missing_flags_insufficient_lookback"] is True
    assert row["price_momentum_return_20d"] is None


def test_schema_validation_and_leakage_audit_are_connected() -> None:
    result = build_candidate_features_mock_with_audit(
        build_mock_daily_quotes_normalized(),
        as_of_date="2026-06-01",
    )

    assert validate_feature_table(result.rows).is_valid
    assert audit_feature_table(result.rows).status == "OK"

    forbidden_rows = [dict(result.rows[0], future_return_20d=0.1)]
    forbidden_audit = audit_feature_table(forbidden_rows)
    assert forbidden_audit.status == "ERROR"
    assert "future_return_20d" in forbidden_audit.forbidden_columns


def test_manifest_and_audit_outputs_are_written_under_runtime(tmp_path: Path) -> None:
    result = build_candidate_features_mock_with_audit(
        build_mock_daily_quotes_normalized(),
        as_of_date="2026-06-01",
    )

    paths = write_candidate_feature_outputs(result.rows, audit=result.audit, runtime_dir=tmp_path / ".runtime")

    assert paths["features"].is_file()
    assert paths["manifest"].is_file()
    assert paths["audit"].is_file()
    assert paths["features"].parent == tmp_path / ".runtime" / "candidate_ai" / "features"
    assert paths["manifest"].parent == tmp_path / ".runtime" / "candidate_ai" / "manifests"
    assert paths["audit"].parent == tmp_path / ".runtime" / "candidate_ai" / "audit"
    assert json.loads(paths["audit"].read_text(encoding="utf-8"))["status"] == "OK"


def test_build_script_runs_and_writes_runtime_outputs(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/build_candidate_features_mock.py",
            "--runtime-dir",
            str(tmp_path / ".runtime"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)

    assert summary["status"] == "OK"
    assert summary["row_count"] == 2
    assert Path(summary["features_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()


def test_phase4e_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4e_audit.json"
    markdown_report = tmp_path / "phase4e_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert result["status"] == "complete"
    assert json_report.is_file()
    assert markdown_report.is_file()
    assert result["checks"]["schema_validation_passes"]
    assert result["checks"]["leakage_audit_passes"]
    assert result["checks"]["runtime_outputs_written"]
    assert result["checks"]["non_implementation_boundary_present"]


def test_phase4e_outputs_have_no_sensitive_values(tmp_path: Path) -> None:
    result = build_candidate_features_mock_with_audit(
        build_mock_daily_quotes_normalized(),
        as_of_date="2026-06-01",
    )
    paths = write_candidate_feature_outputs(result.rows, audit=result.audit, runtime_dir=tmp_path / ".runtime")
    combined = "".join(path.read_text(encoding="utf-8") for path in paths.values())

    for forbidden in ["secret-auth-id", "secret-password", "secret-token", "secret-cookie", "https://example.invalid"]:
        assert forbidden not in combined


def _without_created_at(row: dict[str, object]) -> dict[str, object]:
    comparable = dict(row)
    comparable.pop("created_at", None)
    return comparable
