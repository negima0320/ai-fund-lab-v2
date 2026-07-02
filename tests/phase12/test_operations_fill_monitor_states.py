from __future__ import annotations

from ai_fund_lab_v2.operations.io import write_json
from ai_fund_lab_v2.operations.operations import run_fill_monitor, run_reconcile, run_safety_monitor


def test_fill_monitor_classifies_required_states_and_blocks_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    write_json(
        tmp_path / "submitted_orders" / "2026-06-29" / "submitted_orders.json",
        {
            "submitted_orders": [
                {"item_id": "submitted", "status": "DRY_RUN_READY"},
                {"item_id": "accepted", "broker_status": "ACCEPTED"},
                {"item_id": "waiting", "broker_status": "WAITING_FILL"},
                {"item_id": "partial", "broker_status": "PARTIALLY_FILLED"},
                {"item_id": "filled", "broker_status": "FILLED"},
                {"item_id": "rejected", "broker_status": "REJECTED"},
                {"item_id": "expired", "broker_status": "EXPIRED"},
                {"item_id": "canceled", "broker_status": "CANCELED"},
                {"item_id": "unknown", "broker_status": "nonsense"},
            ]
        },
    )

    result = run_fill_monitor(trade_date="2026-06-29", root=tmp_path)
    states = {event["item_id"]: event["lifecycle"] for event in result["fill_events"]}

    assert result["status"] == "BLOCK"
    assert states["submitted"] == "SUBMITTED"
    assert states["accepted"] == "ACCEPTED"
    assert states["waiting"] == "WAITING_FILL"
    assert states["partial"] == "PARTIALLY_FILLED"
    assert states["filled"] == "FILLED"
    assert states["rejected"] == "REJECTED"
    assert states["expired"] == "EXPIRED"
    assert states["canceled"] == "CANCELED"
    assert states["unknown"] == "UNKNOWN_STATUS"
    assert result["auto_resubmit"] is False
    assert result["auto_cancel"] is False
    assert result["auto_sell"] is False


def test_fill_safety_reconcile_handle_explained_blocked_item_without_emergency_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    trade_date = "2026-06-29"
    write_json(
        tmp_path / "submitted_orders" / trade_date / "submitted_orders.json",
        {
            "status": "PARTIAL_PASS_WITH_ITEM_BLOCKS",
            "submitted_orders": [
                {"item_id": "accepted", "status": "ORDER_ACCEPTED", "side": "BUY", "issue_code": "42650", "quantity": "100", "broker_order_api_called": True, "demo_order_submitted": True},
                {
                    "item_id": "blocked",
                    "status": "BLOCKED_ITEM",
                    "side": "BUY",
                    "issue_code": "23930",
                    "quantity": "100",
                    "block_reason": "remaining_approval_budget_insufficient",
                    "block_reasons": ["remaining_approval_budget_insufficient"],
                    "blocking_stage": "approval_budget",
                },
            ],
            "blocked_items": [{"item_id": "blocked", "block_reason": "remaining_approval_budget_insufficient"}],
        },
    )
    write_json(tmp_path / "broker_orders" / trade_date / "orders.json", {"orders": [{"issue_code": "4265", "side": "3", "quantity": "100", "remaining_quantity": "0", "executed_quantity": "100", "status": "全部約定"}]})
    write_json(tmp_path / "broker_snapshot_summary" / trade_date / "broker_snapshot_summary.json", {"orders_count": 1, "positions_count": 0, "executions_count": 0, "buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    write_json(tmp_path / "broker_positions" / trade_date / "positions.json", {"positions": []})
    write_json(tmp_path / "broker_executions" / trade_date / "executions.json", {"executions": []})
    write_json(tmp_path / "broker_buying_power" / trade_date / "buying_power.json", {"buying_power": "1000000"})
    write_json(tmp_path / "broker_account_summary" / trade_date / "account_summary.json", {})
    write_json(tmp_path / "ledger" / trade_date / "ledger_summary.json", {"status": "PASS"})
    write_json(tmp_path / "ledger" / trade_date / "ledger_state.json", {"orders_summary": {"count": 1}, "positions_summary": {"count": 0}, "executions_summary": {"count": 0}})
    write_json(tmp_path / "ledger" / trade_date / "ledger_update_manifest.json", {"status": "PASS"})

    fill = run_fill_monitor(trade_date=trade_date, root=tmp_path)
    states = {event["item_id"]: event for event in fill["fill_events"]}
    safety = run_safety_monitor(trade_date=trade_date, root=tmp_path)
    reconcile = run_reconcile(trade_date=trade_date, root=tmp_path)

    assert fill["status"] == "PASS"
    assert states["blocked"]["lifecycle"] == "BLOCKED_ITEM"
    assert states["blocked"]["explained_item_block"] is True
    assert safety["status"] == "PASS"
    assert safety["safety_state"] == "ALLOW"
    assert reconcile["status"] != "SYSTEM_EMERGENCY_STOP"


def test_reconcile_passes_previous_day_plan_partial_submit_with_explained_blocked_item(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    trade_date = "2026-07-02"
    source_date = "2026-07-01"
    write_json(tmp_path / "market_refresh" / trade_date / "market_refresh_manifest.json", {"status": "PASS"})
    write_json(tmp_path / "feature_refresh" / trade_date / "feature_refresh_manifest.json", {"status": "PASS"})
    write_json(tmp_path / "daily_plan" / source_date / "daily_plan_result.json", {"status": "PASS"})
    write_json(tmp_path / "order_plan" / source_date / "order_plan.json", {"status": "PASS", "feature_buy_adapter": {"candidate_count": 5}})
    write_json(tmp_path / "approval_artifact" / source_date / "approval_artifact.json", {"status": "APPROVED"})
    write_json(
        tmp_path / "submitted_orders" / trade_date / "submitted_orders.json",
        {
            "status": "PARTIAL_PASS_WITH_ITEM_BLOCKS",
            "submit_run_date": trade_date,
            "order_plan_source_date": source_date,
            "approval_source_date": source_date,
            "submitted_orders": [
                {
                    "item_id": "accepted",
                    "status": "ORDER_ACCEPTED",
                    "side": "BUY",
                    "issue_code": "42650",
                    "broker_issue_code": "4265",
                    "quantity": "100",
                    "broker_order_api_called": True,
                    "demo_order_submitted": True,
                },
                {
                    "item_id": "blocked",
                    "status": "BLOCKED_ITEM",
                    "side": "BUY",
                    "issue_code": "23930",
                    "broker_issue_code": "2393",
                    "quantity": "100",
                    "block_reason": "remaining_approval_budget_insufficient",
                    "block_reasons": ["remaining_approval_budget_insufficient"],
                    "blocking_stage": "approval_budget",
                },
            ],
            "blocked_items": [{"item_id": "blocked", "block_reason": "remaining_approval_budget_insufficient"}],
        },
    )
    write_json(tmp_path / "broker_snapshot" / trade_date / "broker_snapshot.json", {"status": "PASS"})
    write_json(tmp_path / "broker_snapshot_summary" / trade_date / "broker_snapshot_summary.json", {"orders_count": 1, "positions_count": 0, "executions_count": 0, "buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    write_json(tmp_path / "broker_orders" / trade_date / "orders.json", {"orders": [{"issue_code": "4265", "side": "3", "quantity": "100", "remaining_quantity": "0", "executed_quantity": "100", "status": "全部約定"}]})
    write_json(tmp_path / "broker_positions" / trade_date / "positions.json", {"positions": []})
    write_json(tmp_path / "broker_executions" / trade_date / "executions.json", {"executions": []})
    write_json(tmp_path / "broker_buying_power" / trade_date / "buying_power.json", {"buying_power": "1000000"})
    write_json(tmp_path / "ledger" / trade_date / "ledger_summary.json", {"status": "PASS"})
    write_json(tmp_path / "ledger" / trade_date / "ledger_state.json", {"orders_summary": {"count": 1}, "positions_summary": {"count": 0}, "executions_summary": {"count": 0}})
    write_json(tmp_path / "ledger" / trade_date / "ledger_update_manifest.json", {"status": "PASS"})
    write_json(tmp_path / "fill_events" / trade_date / "fill_events.json", {"status": "PASS", "fill_events": [{"item_id": "accepted", "lifecycle": "FILLED"}, {"item_id": "blocked", "lifecycle": "BLOCKED_ITEM"}]})
    write_json(tmp_path / "safety_monitor" / trade_date / "safety_monitor_result.json", {"status": "PASS", "safety_state": "ALLOW"})
    write_json(tmp_path / "safety_result" / trade_date / "safety_result.json", {"status": "PASS"})

    reconcile = run_reconcile(trade_date=trade_date, root=tmp_path)

    assert reconcile["status"] == "PASS_WITH_BLOCKED_ITEMS"
    assert reconcile["missing"] == []
    assert reconcile["source_dates"]["order_plan_source_date"] == source_date
    assert reconcile["submit_reconciliation"]["accepted_order_count"] == 1
    assert reconcile["submit_reconciliation"]["blocked_item_count"] == 1
    assert reconcile["submit_reconciliation"]["demo_empty_executions_positions_explained"] is True
