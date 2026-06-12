from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase3_safety_foundation import run_audit


def test_phase3_safety_completion_audit_reports_complete(tmp_path: Path) -> None:
    json_report = tmp_path / "reports" / "phase3_audit.json"
    markdown_report = tmp_path / "docs" / "phase3_audit.md"

    result = run_audit(
        runtime_dir=tmp_path / ".runtime",
        json_report_path=json_report,
        markdown_report_path=markdown_report,
    )

    assert result["status"] == "complete"
    checks = result["checks"]
    assert checks["safety_models"]
    assert checks["reconciliation"]
    assert checks["trading_lock"]
    assert checks["safety_report"]
    assert checks["broker_snapshot_integration"]
    assert checks["dry_run"]
    assert checks["manual_review"]
    assert checks["manual_unlock"]
    assert checks["manual_unlock_apply"]
    assert checks["operation_guard_lock_state"]
    assert checks["fail_closed"]
    assert checks["runtime_safety_paths"]
    assert checks["tests_present"]


def test_phase3_safety_completion_audit_writes_json_and_markdown(tmp_path: Path) -> None:
    json_report = tmp_path / "reports" / "phase3_audit.json"
    markdown_report = tmp_path / "docs" / "phase3_audit.md"

    result = run_audit(
        runtime_dir=tmp_path / ".runtime",
        json_report_path=json_report,
        markdown_report_path=markdown_report,
    )

    assert json_report.is_file()
    assert markdown_report.is_file()
    saved_json = json.loads(json_report.read_text(encoding="utf-8"))
    saved_markdown = markdown_report.read_text(encoding="utf-8")
    assert saved_json["status"] == result["status"] == "complete"
    assert "Phase3 Safety Foundation Completion Audit" in saved_markdown
    assert "Phase3 Complete" in saved_markdown


def test_phase3_safety_completion_audit_forbidden_checks_are_true(tmp_path: Path) -> None:
    result = run_audit(
        runtime_dir=tmp_path / ".runtime",
        json_report_path=tmp_path / "phase3_audit.json",
        markdown_report_path=tmp_path / "phase3_audit.md",
    )

    checks = result["checks"]
    assert checks["no_live_mode"]
    assert checks["no_real_api"]
    assert checks["no_ordering"]
    assert checks["no_ai_integration"]
    assert checks["no_auto_recovery"]


def test_phase3_safety_completion_audit_does_not_include_sensitive_values(tmp_path: Path) -> None:
    json_report = tmp_path / "reports" / "phase3_audit.json"
    markdown_report = tmp_path / "docs" / "phase3_audit.md"

    result = run_audit(
        runtime_dir=tmp_path / ".runtime",
        json_report_path=json_report,
        markdown_report_path=markdown_report,
    )
    combined = json.dumps(result, ensure_ascii=False) + json_report.read_text(encoding="utf-8") + markdown_report.read_text(encoding="utf-8")

    for forbidden in [
        "secret-auth-id",
        "https://example.invalid/request",
        "https://example.invalid/session",
        "secret-password",
        "secret-token",
        "secret-cookie",
        "second-password",
    ]:
        assert forbidden not in combined
