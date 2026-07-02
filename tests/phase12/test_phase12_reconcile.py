from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_daily_plan, run_market_refresh, run_reconcile


def test_reconcile_reports_missing_targets_as_review(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(trade_date="2026-06-29", root=tmp_path)

    result = run_reconcile(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "REVIEW_REQUIRED"
    assert "approval" in result["missing"]
