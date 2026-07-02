from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_audit, run_market_refresh


def test_operation_audit_records_phase9_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)

    result = run_audit(root=tmp_path)
    isolation = result["phase9_isolation_audit"]

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["operation_day_type"] == "INCOMPLETE_OPERATION_DAY"
    assert isolation["phase9_artifact_root_untouched"] is True
    assert isolation["phase9_launchd_untouched"] is True
    assert isolation["phase9_cli_untouched"] is True
    assert isolation["phase9_reports_untouched"] is True
    assert isolation["phase12_artifact_root_does_not_use_phase9"] is True
    assert isolation["phase12_launchd_prefix_is_operations"] is True
    assert result["phase9_parallel_running_allowed"] is True
    assert result["phase9_artifacts_modified_by_phase12"] is False
    assert result["phase9_launchd_modified_by_phase12"] is False
