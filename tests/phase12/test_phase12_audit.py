from __future__ import annotations

from ai_fund_lab_v2.operations.io import write_json
from ai_fund_lab_v2.operations.operations import run_audit, run_daily_report, run_reconcile


def test_audit_passes_without_production_order_or_line_send(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_daily_report(trade_date="2026-06-29", root=tmp_path)
    run_reconcile(trade_date="2026-06-29", root=tmp_path)

    result = run_audit(root=tmp_path)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["operation_day_type"] == "INCOMPLETE_OPERATION_DAY"
    assert result["no_production_order_audit"] is True
    assert result["line_send_executed"] is False


def test_audit_blocks_production_order_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    write_json(tmp_path / "submitted_orders" / "2026-06-29" / "submitted_orders.json", {"production_order_submitted": True})

    result = run_audit(root=tmp_path)

    assert result["status"] == "BLOCK"
    assert result["no_production_order_audit"] is False
