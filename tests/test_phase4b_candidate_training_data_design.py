from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4b_candidate_training_data_design import run_audit


def test_phase4b_candidate_training_data_design_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4b_audit.json",
        markdown_report_path=tmp_path / "phase4b_audit.md",
    )

    assert result["status"] == "complete"
    checks = result["checks"]
    assert checks["required_input_docs_present"]
    assert checks["phase4b_design_doc_present"]
    assert checks["phase4b_report_present"]
    assert checks["feature_table_schema_present"]
    assert checks["label_table_schema_present"]
    assert checks["training_dataset_schema_present"]
    assert checks["audit_table_schema_present"]
    assert checks["as_of_date_rule_present"]
    assert checks["target_date_rule_present"]
    assert checks["lookback_window_rule_present"]
    assert checks["future_label_isolation_present"]
    assert checks["time_series_split_present"]
    assert checks["random_split_forbidden"]
    assert checks["forbidden_features_present"]
    assert checks["candidate_boundary_present"]
    assert checks["non_implementation_boundary_present"]
    assert checks["no_candidate_ai_code_added"]


def test_phase4b_candidate_training_data_design_audit_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "reports" / "phase4b_audit.json"
    markdown_report = tmp_path / "docs" / "phase4b_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert json_report.is_file()
    assert markdown_report.is_file()
    saved_json = json.loads(json_report.read_text(encoding="utf-8"))
    saved_markdown = markdown_report.read_text(encoding="utf-8")
    assert saved_json["status"] == result["status"] == "complete"
    assert "Phase4-B Candidate Training Data Design Audit" in saved_markdown


def test_phase4b_candidate_training_data_design_audit_has_no_sensitive_values(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4b_audit.json"
    markdown_report = tmp_path / "phase4b_audit.md"

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
