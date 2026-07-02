from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_daily_plan, run_market_refresh


def test_daily_plan_schema_defaults_to_demo_unapproved(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    result = run_daily_plan(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "PASS"
    plan = (tmp_path / "order_plan" / "2026-06-29" / "order_plan.json").read_text()
    assert '"environment": "demo"' in plan
    assert '"production_order_allowed": false' in plan
    assert '"demo_order_allowed": false' in plan
    assert '"requires_approval": true' in plan
