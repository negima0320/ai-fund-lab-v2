from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.candidate_ai import (
    ALLOWED_FEATURE_PREFIXES,
    FORBIDDEN_FEATURE_TERMS,
    REQUIRED_FEATURE_COLUMNS,
    CandidateAIRuntimePaths,
    audit_feature_table,
    validate_feature_table,
)
from ai_fund_lab_v2.candidate_ai.schemas import AUDIT_FIELDS, MANIFEST_FIELDS
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4d_candidate_feature_builder_skeleton import run_audit


def valid_feature_rows() -> list[dict[str, object]]:
    return [
        {
            "as_of_date": "2026-06-01",
            "target_date": "2026-06-01",
            "code": "7203",
            "feature_version": "candidate_features_v1",
            "source_snapshot_id": "snapshot-001",
            "universe_eligible": True,
            "excluded_reason": "",
            "price_momentum_return_20d": 0.12,
            "volume_momentum_ratio_5d_20d": 1.8,
            "volatility_20d": 0.03,
            "missing_flags_price": False,
        }
    ]


def test_schema_contract_constants_are_defined() -> None:
    assert {
        "as_of_date",
        "target_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "universe_eligible",
        "excluded_reason",
    }.issubset(REQUIRED_FEATURE_COLUMNS)
    assert "price_momentum_" in ALLOWED_FEATURE_PREFIXES
    assert "volume_momentum_" in ALLOWED_FEATURE_PREFIXES
    assert "missing_flags_" in ALLOWED_FEATURE_PREFIXES
    assert "future_return_" in FORBIDDEN_FEATURE_TERMS
    assert "momentum_candidate_label" in FORBIDDEN_FEATURE_TERMS
    assert "pnl" in FORBIDDEN_FEATURE_TERMS


def test_manifest_and_audit_schema_contracts_are_defined() -> None:
    assert {"feature_version", "created_at", "as_of_date", "target_date", "output_path", "audit_path"}.issubset(
        MANIFEST_FIELDS
    )
    assert {
        "status",
        "forbidden_feature_detected",
        "forbidden_columns",
        "post_as_of_data_detected",
        "missing_required_columns",
        "invalid_prefix_columns",
    }.issubset(AUDIT_FIELDS)


def test_candidate_runtime_paths_are_under_runtime_candidate_ai(tmp_path: Path) -> None:
    paths = CandidateAIRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))

    assert paths.features == tmp_path / ".runtime" / "candidate_ai" / "features"
    assert paths.manifests == tmp_path / ".runtime" / "candidate_ai" / "manifests"
    assert paths.audit == tmp_path / ".runtime" / "candidate_ai" / "audit"
    assert paths.reports == tmp_path / ".runtime" / "candidate_ai" / "reports"
    assert paths.tmp == tmp_path / ".runtime" / "candidate_ai" / "tmp"

    paths.ensure_dirs()
    assert all(path.is_dir() for path in paths.iter_dirs())


def test_valid_feature_table_passes_validation() -> None:
    result = validate_feature_table(valid_feature_rows())

    assert result.is_valid
    assert result.missing_required_columns == ()
    assert result.forbidden_columns == ()
    assert result.invalid_prefix_columns == ()
    assert result.invalid_date_rows == ()


def test_forbidden_column_is_detected() -> None:
    rows = valid_feature_rows()
    rows[0]["future_return_20d"] = 0.2

    result = validate_feature_table(rows)
    audit = audit_feature_table(rows)

    assert not result.is_valid
    assert "future_return_20d" in result.forbidden_columns
    assert audit.status == "ERROR"
    assert audit.forbidden_feature_detected
    assert audit.future_column_detected


def test_as_of_date_after_target_date_is_detected() -> None:
    rows = valid_feature_rows()
    rows[0]["as_of_date"] = "2026-06-02"
    rows[0]["target_date"] = "2026-06-01"

    result = validate_feature_table(rows)
    audit = audit_feature_table(rows)

    assert not result.is_valid
    assert result.invalid_date_rows == (0,)
    assert audit.post_as_of_data_detected
    assert audit.target_date_leakage_detected


def test_invalid_feature_prefix_is_detected() -> None:
    rows = valid_feature_rows()
    rows[0]["mystery_signal"] = 1

    result = validate_feature_table(rows)

    assert not result.is_valid
    assert "mystery_signal" in result.invalid_prefix_columns


def test_phase4d_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4d_audit.json"
    markdown_report = tmp_path / "phase4d_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert result["status"] == "complete"
    assert json_report.is_file()
    assert markdown_report.is_file()
    saved_json = json.loads(json_report.read_text(encoding="utf-8"))
    assert saved_json["status"] == "complete"
    assert result["checks"]["valid_feature_table_fixture_passes"]
    assert result["checks"]["forbidden_column_fixture_detected"]
    assert result["checks"]["invalid_date_fixture_detected"]
    assert result["checks"]["non_implementation_boundary_present"]


def test_phase4d_audit_has_no_sensitive_values(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4d_audit.json"
    markdown_report = tmp_path / "phase4d_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)
    combined = json.dumps(result, ensure_ascii=False) + json_report.read_text(encoding="utf-8") + markdown_report.read_text(encoding="utf-8")

    for forbidden in ["secret-auth-id", "secret-password", "secret-token", "secret-cookie", "https://example.invalid"]:
        assert forbidden not in combined
