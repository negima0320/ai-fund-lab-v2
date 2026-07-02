from __future__ import annotations

from ai_fund_lab_v2.operations.io import read_json
from ai_fund_lab_v2.operations.operations import run_market_refresh


def test_daily_manifest_contains_phase12d_required_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    manifest = read_json(tmp_path / "daily_manifest" / "2026-06-29" / "daily_manifest.json")

    for key in [
        "market_refresh_status",
        "feature_refresh_status",
        "daily_plan_status",
        "approval_status",
        "preflight_status",
        "submit_status",
        "fill_monitor_status",
        "safety_monitor_status",
        "reconciliation_status",
        "daily_report_status",
        "operation_audit_status",
        "missed_jobs",
        "run_lock_status",
    ]:
        assert key in manifest
    assert manifest["line_send_executed"] is False
    assert manifest["production_order_submitted"] is False
    assert manifest["ai_retraining_executed"] is False
    assert manifest["backtest_run"] is False
    assert manifest["raw_response_saved"] is False
    assert manifest["secret_saved"] is False
    assert manifest["phase9_parallel_running_allowed"] is True
    assert manifest["phase9_artifacts_modified_by_phase12"] is False
    assert manifest["phase9_launchd_modified_by_phase12"] is False
    assert str(manifest["phase12_artifact_root"]) == str(tmp_path)
