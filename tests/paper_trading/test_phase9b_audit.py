from pathlib import Path

from scripts.audit_phase9b_report_framework import run_audit


def test_phase9b_report_framework_audit_passes(tmp_path: Path) -> None:
    summary = run_audit(output_root=tmp_path)
    assert summary["status"] == "PASS"
    assert summary["internal_report_generated"] is True
    assert summary["public_report_generated"] is True
    assert summary["blog_draft_generated"] is True
    assert summary["broker_order_api_called"] is False

