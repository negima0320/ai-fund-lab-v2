from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4a_candidate_ai_design import run_audit


def test_phase4a_candidate_ai_design_audit_completes(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4a_audit.json",
        markdown_report_path=tmp_path / "phase4a_audit.md",
    )

    assert result["status"] == "complete"
    checks = result["checks"]
    assert checks["required_docs_present"]
    assert checks["phase4a_report_present"]
    assert checks["candidate_feature_catalog_present"]
    assert checks["candidate_scope_limited_to_extraction"]
    assert checks["does_not_invade_downstream_responsibilities"]
    assert checks["required_design_items_present"]
    assert checks["forbidden_data_list_present"]
    assert checks["daily_quotes_normalized_present"]
    assert checks["no_training_inference_backtest_paper_ordering"]
    assert checks["future_labels_not_features"]
    assert checks["audit_policy_present"]
    assert checks["no_candidate_ai_code_added"]


def test_phase4a_candidate_ai_design_audit_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "reports" / "phase4a_audit.json"
    markdown_report = tmp_path / "docs" / "phase4a_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert json_report.is_file()
    assert markdown_report.is_file()
    saved_json = json.loads(json_report.read_text(encoding="utf-8"))
    saved_markdown = markdown_report.read_text(encoding="utf-8")
    assert saved_json["status"] == result["status"] == "complete"
    assert "Phase4-A Candidate AI Design Audit" in saved_markdown


def test_phase4a_candidate_ai_design_audit_has_no_sensitive_values(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4a_audit.json"
    markdown_report = tmp_path / "phase4a_audit.md"

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
