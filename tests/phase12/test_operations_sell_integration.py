from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.operations.io import read_json, write_json
from ai_fund_lab_v2.operations.operations import (
    run_approval_prepare,
    run_daily_plan,
    run_daily_report,
    run_demo_submit,
    run_fill_monitor,
    run_market_refresh,
    run_reconcile,
)

TRADE_DATE = "2026-06-29"


def _write_exit_position(root):
    write_json(
        root / "positions" / TRADE_DATE / "positions.json",
        {
            "artifact_type": "positions",
            "business_date": TRADE_DATE,
            "exit_source": "position_management_ai",
            "positions": [
                {
                    "issue_code": "7203",
                    "position_id": "pos_7203",
                    "lot_reference": "lot_7203_001",
                    "quantity": "100",
                    "entry_price": "1200",
                    "current_price": "1000",
                    "exit_action": "EXIT",
                    "exit_reason": "trend_break",
                    "sell_reason": "trend_break",
                }
            ],
        },
    )


def test_daily_plan_generates_sell_item_from_runtime_positions(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_exit_position(tmp_path)
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)

    result = run_daily_plan(
        trade_date=TRADE_DATE,
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "6758", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    order_plan = read_json(tmp_path / "order_plan" / TRADE_DATE / "order_plan.json")
    sell_items = [item for item in order_plan["items"] if item["side"] == "SELL"]

    assert result["status"] == "PASS"
    assert order_plan["buy_item_count"] == 1
    assert order_plan["sell_item_count"] == 1
    assert order_plan["exit_adapter"]["exit_source"] == "position_management_ai"
    assert sell_items[0]["position_id"] == "pos_7203"
    assert sell_items[0]["lot_reference"] == "lot_7203_001"
    assert sell_items[0]["expected_notional"] == "100000"
    assert sell_items[0]["sell_reason"] == "trend_break"
    assert sell_items[0]["production_order_allowed"] is False


def test_daily_plan_blocks_invalid_positions_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    write_json(
        tmp_path / "positions" / TRADE_DATE / "positions.json",
        {"artifact_type": "positions", "business_date": TRADE_DATE, "positions": {"issue_code": "7203"}},
    )
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)

    result = run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)
    order_plan = read_json(tmp_path / "order_plan" / TRADE_DATE / "order_plan.json")

    assert result["status"] == "BLOCK"
    assert order_plan["items"] == []
    assert "positions_artifact_invalid" in order_plan["exit_adapter"]["blocked_reasons"]


def test_sell_approval_scope_and_submit_position_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_exit_position(tmp_path)
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)
    run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)

    run_approval_prepare(trade_date=TRADE_DATE, root=tmp_path, approve=True, approver_label="operator")
    approval = read_json(tmp_path / "approval_artifact" / TRADE_DATE / "approval_artifact.json")

    assert approval["status"] == "APPROVED"
    assert approval["approved_sides"] == ["SELL"]
    assert approval["sell_approval_scope"][0]["approved_position_id"] == "pos_7203"
    assert approval["sell_approval_scope"][0]["approved_max_quantity"] == "100"
    assert approval["demo_order_allowed"] is True

    write_json(
        tmp_path / "positions" / TRADE_DATE / "positions.json",
        {
            "artifact_type": "positions",
            "business_date": TRADE_DATE,
            "exit_source": "position_management_ai",
            "positions": [
                {
                    "issue_code": "7203",
                    "position_id": "pos_7203",
                    "lot_reference": "lot_7203_001",
                    "quantity": "50",
                    "entry_price": "1200",
                    "current_price": "1000",
                }
            ],
        },
    )
    result = run_demo_submit(trade_date=TRADE_DATE, root=tmp_path)

    assert result["status"] == "BLOCK"
    assert result["submitted_orders"][0]["status"] == "BLOCKED_ITEM"
    assert "sell_quantity_exceeds_broker_position" in result["submitted_orders"][0]["reasons"]
    assert result["demo_order_submitted"] is False
    assert result["production_order_submitted"] is False


def test_sell_dry_run_fill_reconcile_and_report_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_exit_position(tmp_path)
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)
    run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)
    run_approval_prepare(trade_date=TRADE_DATE, root=tmp_path, approve=True, approver_label="operator")

    submit = run_demo_submit(trade_date=TRADE_DATE, root=tmp_path)
    fill = run_fill_monitor(trade_date=TRADE_DATE, root=tmp_path)
    reconcile = run_reconcile(trade_date=TRADE_DATE, root=tmp_path)
    report = run_daily_report(trade_date=TRADE_DATE, root=tmp_path)
    refs = read_json(tmp_path / "daily_report_refs" / TRADE_DATE / "daily_report_refs.json")

    assert submit["status"] == "PASS"
    assert submit["submitted_orders"][0]["side"] == "SELL"
    assert submit["submitted_orders"][0]["status"] == "DRY_RUN_READY"
    assert submit["submitted_orders"][0]["demo_order_submitted"] is False
    assert fill["fill_events"][0]["side"] == "SELL"
    assert fill["fill_events"][0]["realized_result_placeholder"] is True
    assert fill["fill_events"][0]["sell_reason"] == "trend_break"
    assert reconcile["sell_reconciliation"]["sell_event_count"] == 1
    assert reconcile["sell_reconciliation"]["broker_source_of_truth_required"] is True
    assert refs["sell_summary"]["sell_candidate_count"] == 1
    assert refs["sell_summary"]["items"][0]["sell_reason"] == "trend_break"
    assert report["line_send_executed"] is False
