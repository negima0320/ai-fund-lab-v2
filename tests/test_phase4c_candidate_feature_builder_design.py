from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4c_candidate_feature_builder_design import run_audit


def test_phase4c_candidate_feature_builder_design_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4c_audit.json",
        markdown_report_path=tmp_path / "phase4c_audit.md",
    )

    assert result["status"] == "complete"
    checks = result["checks"]
    assert checks["required_input_docs_present"]
    assert checks["phase4c_design_doc_present"]
    assert checks["phase4c_report_present"]
    assert checks["feature_builder_responsibility_present"]
    assert checks["input_source_present"]
    assert checks["output_schema_present"]
    assert checks["feature_category_present"]
    assert checks["daily_quotes_normalized_core_input"]
    assert checks["as_of_date_only_rule_present"]
    assert checks["lookback_past_only_present"]
    assert checks["fins_publication_date_rule_present"]
    assert checks["market_index_sector_rule_present"]
    assert checks["missing_value_rule_present"]
    assert checks["universe_filter_rule_present"]
    assert checks["feature_version_rule_present"]
    assert checks["runtime_output_path_present"]
    assert checks["manifest_audit_integration_present"]
    assert checks["leakage_audit_rule_present"]
    assert checks["mock_fixture_design_present"]
    assert checks["forbidden_features_present"]
    assert checks["candidate_boundary_present"]
    assert checks["non_implementation_boundary_present"]
    assert checks["no_candidate_feature_builder_code_added"]


def test_phase4c_candidate_feature_builder_design_audit_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "reports" / "phase4c_audit.json"
    markdown_report = tmp_path / "docs" / "phase4c_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert json_report.is_file()
    assert markdown_report.is_file()
    saved_json = json.loads(json_report.read_text(encoding="utf-8"))
    saved_markdown = markdown_report.read_text(encoding="utf-8")
    assert saved_json["status"] == result["status"] == "complete"
    assert "Phase4-C Candidate Feature Builder Design Audit" in saved_markdown


def test_phase4c_candidate_feature_builder_design_audit_has_no_sensitive_values(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4c_audit.json"
    markdown_report = tmp_path / "phase4c_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)
    combined = json.dumps(result, ensure_ascii=False) + json_report.read_text(encoding="utf-8") + markdown_report.read_text(encoding="utf-8")

    for forbidden in [
        "secret-auth-id",
        "secret-password",
        "secret-token",
        "secret-cookie",
        "https://example.invalid",
    ]:
        assert forbidden not in combined
