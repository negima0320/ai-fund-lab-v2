from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.operations.guards import evaluate_max_exposure
import ai_fund_lab_v2.operations.operations as operations_module
from ai_fund_lab_v2.operations.operations import run_approval_prepare, run_daily_plan, run_demo_submit, run_market_refresh, run_preflight, run_submit_operation
from ai_fund_lab_v2.operations.io import read_json, stable_hash, write_json
from ai_fund_lab_v2.operations.pending_order_plan import build_pending_order_plan, write_pending_order_plan


def test_demo_submit_rejects_missing_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "BLOCK"
    assert "pending_order_plan_missing" in result["blocks"]
    assert result["production_order_submitted"] is False


def test_demo_submit_dry_run_ready_after_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "PASS"
    assert result["submitted_orders"][0]["status"] == "DRY_RUN_READY"
    assert result["demo_order_submitted"] is False
    assert result["production_order_submitted"] is False


def test_runtime_submit_blocks_manual_override_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "order_plan" / "2026-06-29" / "order_plan.json", {
        "artifact_type": "order_plan",
        "business_date": "2026-06-29",
        "environment": "demo",
        "items": [{"item_id": "buy_1", "issue_code": "7203", "code": "7203", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"}],
    })
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "approval_max_notional": "600000",
        "max_notional": "600000",
        "approval_max_notional_source": "manual_override",
    })
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "BLOCK"
    assert result["approval_manual_override_detected"] is True
    assert "manual_override_approval_not_allowed_for_runtime_submit" in result["blocks"]
    assert result["production_order_submitted"] is False


def test_common_submit_enters_production_executor_but_blocks_orders(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "production")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "code": "7203", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "order_plan" / "2026-06-29" / "order_plan.json", {
        "artifact_type": "order_plan",
        "business_date": "2026-06-29",
        "environment": "production",
        "items": [{"item_id": "buy_1", "issue_code": "7203", "code": "7203", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"}],
    })
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": False,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "approval_max_notional": "850000",
        "max_notional": "850000",
        "approval_max_notional_source": "dynamic_max_exposure",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    _write_listed(tmp_path, ["7203"])
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_submit_operation(trade_date="2026-06-29", root=tmp_path, execute_order=True, second_password_present=True)

    assert result["status"] == "BLOCK"
    assert result["runtime_submit_entry"] == "run_submit_operation"
    assert result["executor_kind"] == "ProductionOrderExecutor"
    assert result["adapter_kind"] == "PRODUCTION_BLOCKED_PHASE12_5"
    assert result["production_order_submitted"] is False
    assert "production_order_disabled_phase12_5" in result["blocks"]
    assert result["submitted_orders"][0]["status"] == "BLOCKED_PRODUCTION_PROHIBITED"


def test_demo_submit_uses_previous_business_day_plan_for_next_morning(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    write_json(
        tmp_path / "order_plan" / "2026-06-30" / "order_plan.json",
        {
            "artifact_type": "order_plan",
            "business_date": "2026-06-30",
            "environment": "demo",
            "items": [{"item_id": "old_buy", "issue_code": "9999", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "100", "estimated_value": "10000"}],
        },
    )
    write_json(
        tmp_path / "approval_artifact" / "2026-06-30" / "approval_artifact.json",
        {"approval_id": "old_approval", "demo_order_allowed": True, "production_order_allowed": False, "approved_item_ids": ["old_buy"], "max_notional": "600000"},
    )
    write_json(
        tmp_path / "order_plan" / "2026-07-01" / "order_plan.json",
        {
            "artifact_type": "order_plan",
            "business_date": "2026-07-01",
            "environment": "demo",
            "items": [{"item_id": "latest_buy", "issue_code": "42650", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "430", "estimated_value": "43000"}],
        },
    )
    write_json(
        tmp_path / "approval_artifact" / "2026-07-01" / "approval_artifact.json",
        {
            "approval_id": "latest_approval",
            "demo_order_allowed": True,
            "production_order_allowed": False,
            "approved_item_ids": ["latest_buy"],
                "approval_expires_at": "2099-01-01T00:00:00+00:00",
            "max_notional": "600000",
        },
    )
    _write_pending_from_dated_artifacts(tmp_path, "2026-07-01", "2026-07-02")

    result = run_demo_submit(trade_date="2026-07-02", root=tmp_path)

    assert result["status"] == "PASS"
    assert result["submit_run_date"] == "2026-07-02"
    assert result["order_plan_source_date"] == "2026-07-01"
    assert result["approval_source_date"] == "2026-07-01"
    assert result["uses_previous_business_day_order_plan"] is False
    assert result["submit_source"] == "pending_order_plan"
    assert result["submitted_orders"][0]["item_id"] == "latest_buy"
    assert result["submitted_orders"][0]["issue_code"] == "42650"
    assert all(row["item_id"] != "old_buy" for row in result["submitted_orders"])
    assert result["demo_order_submitted"] is False
    assert result["production_order_submitted"] is False


def test_max_exposure_blocks_buy_but_not_sell():
    blocked_buy = evaluate_max_exposure(
        side="BUY",
        order_value=Decimal("200000"),
        current_exposure=Decimal("800000"),
        broker_actual_equity=Decimal("1000000"),
    )
    allowed_sell = evaluate_max_exposure(
        side="SELL",
        order_value=Decimal("200000"),
        current_exposure=Decimal("900000"),
        broker_actual_equity=Decimal("1000000"),
    )

    assert blocked_buy.status == "BLOCK"
    assert blocked_buy.reason == "MAX_EXPOSURE_EXCEEDED"
    assert allowed_sell.allowed is True


def test_demo_submit_blocks_duplicate_active_same_code_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "code": "7203", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"}],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "max_notional": "120000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    write_json(tmp_path / "broker_orders" / "2026-06-29" / "orders.json", {"orders": [{"issue_code": "7203", "side": "3", "quantity": "100", "remaining_quantity": "100", "status": "未約定"}]})
    listed = tmp_path / "feature_refresh" / "2026-06-29" / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    listed.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    pd.DataFrame([{"Code": "7203", "code": "7203", "MktNm": "プライム", "ProdCat": "011"}]).to_parquet(listed)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)

    assert result["status"] == "REVIEW_REQUIRED_ITEM_BLOCKS"
    assert result["submitted_orders"][0]["status"] == "BLOCKED_ITEM"
    assert "duplicate_active_broker_order_exists" in result["submitted_orders"][0]["reasons"]
    assert result["broker_order_api_called"] is False


def test_demo_submit_processes_multiple_items_and_blocks_only_duplicate_item(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[
            {"item_id": "buy_1", "issue_code": "7203", "code": "7203", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"},
            {"item_id": "buy_2", "issue_code": "6758", "code": "6758", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"},
        ],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1", "buy_2"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "max_notional": "250000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    write_json(tmp_path / "broker_orders" / "2026-06-29" / "orders.json", {"orders": [{"issue_code": "7203", "side": "3", "quantity": "100", "remaining_quantity": "100", "status": "未約定"}]})
    _write_listed(tmp_path, ["7203", "6758"])

    class FakeAdapter:
        def submit_cash_stock_order(self, command):
            class Result:
                def to_dict(self):
                    return {"status": "FAKE_NOT_SENT", "broker_order_api_called": False, "demo_order_executed": False, "response": {"accepted": False, "status": "FAKE_NOT_SENT"}}

            return Result()

    monkeypatch.setattr(operations_module, "TachibanaDemoOrderAdapter", FakeAdapter)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)

    assert result["status"] == "REVIEW_REQUIRED_ITEM_BLOCKS"
    assert result["submitted_orders"][0]["status"] == "BLOCKED_ITEM"
    assert "duplicate_active_broker_order_exists" in result["submitted_orders"][0]["reasons"]
    assert result["submitted_orders"][1]["item_id"] == "buy_2"
    assert result["submitted_orders"][1]["status"] == "FAKE_NOT_SENT"
    assert result["broker_order_api_called"] is False


def test_demo_submit_blocks_items_over_remaining_approval_budget_before_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[
            {"item_id": "buy_1", "issue_code": "7203", "code": "7203", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1000", "estimated_value": "100000"},
        ],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "max_notional": "50000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    _write_listed(tmp_path, ["7203"])
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)

    assert result["submitted_orders"][0]["status"] == "BLOCKED_ITEM"
    assert "remaining_approval_budget_insufficient" in result["submitted_orders"][0]["reasons"]
    assert result["submitted_orders"][0]["block_reason"] == "remaining_approval_budget_insufficient"
    assert result["blocked_items"][0]["item_id"] == "buy_1"
    assert result["broker_order_api_called"] is False


def test_demo_submit_partial_success_records_blocked_item_reason_and_continues(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[
            {"item_id": "buy_1", "issue_code": "42650", "code": "42650", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "456", "estimated_value": "45600"},
            {"item_id": "buy_2", "issue_code": "41790", "code": "41790", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "600", "estimated_value": "60000"},
            {"item_id": "buy_3", "issue_code": "29620", "code": "29620", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1990", "estimated_value": "199000"},
            {"item_id": "buy_4", "issue_code": "23930", "code": "23930", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "4295", "estimated_value": "429500"},
            {"item_id": "buy_5", "issue_code": "61660", "code": "61660", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "766", "estimated_value": "76600"},
        ],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1", "buy_2", "buy_3", "buy_4", "buy_5"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "max_notional": "600000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    _write_listed(tmp_path, ["42650", "41790", "29620", "23930", "61660"])

    class FakeAdapter:
        def submit_cash_stock_order(self, command):
            class Result:
                def to_dict(self):
                    return {"status": "PASS", "broker_order_api_called": True, "demo_order_executed": True, "response": {"accepted": True, "status": "ORDER_ACCEPTED", "broker_order_id_hash": "hash"}}

            return Result()

    monkeypatch.setattr(operations_module, "TachibanaDemoOrderAdapter", FakeAdapter)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)
    rows = {row["item_id"]: row for row in result["submitted_orders"]}

    assert result["status"] == "PARTIAL_PASS_WITH_ITEM_BLOCKS"
    assert result["accepted_order_count"] == 4
    assert result["blocked_item_count"] == 1
    assert result["blocked_items"][0]["item_id"] == "buy_4"
    assert rows["buy_4"]["status"] == "BLOCKED_ITEM"
    assert rows["buy_4"]["block_reason"] == "remaining_approval_budget_insufficient"
    assert rows["buy_4"]["blocking_stage"] == "approval_budget"
    assert rows["buy_4"]["remaining_approval_budget"] == "295400"
    assert rows["buy_4"]["item_expected_notional"] == "429500"
    assert rows["buy_4"]["cumulative_submitted_notional"] == "304600"
    assert rows["buy_4"]["max_notional"] == "600000"
    assert rows["buy_5"]["status"] == "ORDER_ACCEPTED"
    assert result["production_order_submitted"] is False


def test_demo_submit_dynamic_850000_approval_budget_allows_20260702_case(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[
            {"item_id": "buy_1", "issue_code": "42650", "code": "42650", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "456", "estimated_value": "45600"},
            {"item_id": "buy_2", "issue_code": "41790", "code": "41790", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "600", "estimated_value": "60000"},
            {"item_id": "buy_3", "issue_code": "29620", "code": "29620", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "1990", "estimated_value": "199000"},
            {"item_id": "buy_4", "issue_code": "23930", "code": "23930", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "4295", "estimated_value": "429500"},
            {"item_id": "buy_5", "issue_code": "61660", "code": "61660", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "766", "estimated_value": "76600"},
        ],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1", "buy_2", "buy_3", "buy_4", "buy_5"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "approval_max_notional": "850000",
        "max_notional": "850000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    _write_listed(tmp_path, ["42650", "41790", "29620", "23930", "61660"])

    class FakeAdapter:
        def submit_cash_stock_order(self, command):
            class Result:
                def to_dict(self):
                    return {"status": "PASS", "broker_order_api_called": True, "demo_order_executed": True, "response": {"accepted": True, "status": "ORDER_ACCEPTED", "broker_order_id_hash": "hash"}}

            return Result()

    monkeypatch.setattr(operations_module, "TachibanaDemoOrderAdapter", FakeAdapter)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)
    rows = {row["item_id"]: row for row in result["submitted_orders"]}

    assert result["status"] == "PASS"
    assert result["accepted_order_count"] == 5
    assert result["blocked_item_count"] == 0
    assert result["blocked_items"] == []
    assert rows["buy_4"]["status"] == "ORDER_ACCEPTED"
    assert rows["buy_5"]["status"] == "ORDER_ACCEPTED"
    assert result["production_order_submitted"] is False


def test_post_send_unknown_is_confirmed_by_broker_readonly_without_resubmit(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "42650", "code": "42650", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "456", "estimated_value": "45600"}],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "approval_max_notional": "850000",
        "max_notional": "850000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    _write_listed(tmp_path, ["42650"])

    class FakeAdapter:
        calls = 0

        def submit_cash_stock_order(self, command):
            FakeAdapter.calls += 1

            class Result:
                def to_dict(self):
                    return {
                        "status": "POST_SEND_UNKNOWN",
                        "broker_order_api_called": True,
                        "demo_order_executed": False,
                        "submit_classification": "POST_SEND_UNKNOWN",
                        "post_send_unknown": True,
                        "broker_readonly_confirmation_status": "PENDING",
                        "response": {"accepted": False, "status": "POST_SEND_UNKNOWN"},
                        "attempts": [{"attempt": 1, "failure_stage": "order_post_send_unknown", "safe_error_class": "TimeoutError", "retryable": False, "classification": "POST_SEND_UNKNOWN"}],
                    }

            return Result()

    def fake_refresh(*, trade_date, root, run_enabled=False, include_quotes=False):
        write_json(tmp_path / "broker_snapshot" / trade_date / "broker_snapshot.json", {"status": "PASS"})
        write_json(tmp_path / "broker_orders" / trade_date / "orders.json", {"orders": [{"issue_code": "4265", "side": "3", "quantity": "100", "status": "未約定", "broker_order_id_hash": "order_hash"}]})
        write_json(tmp_path / "broker_executions" / trade_date / "executions.json", {"executions": []})
        write_json(tmp_path / "broker_positions" / trade_date / "positions.json", {"positions": []})
        write_json(tmp_path / "broker_buying_power" / trade_date / "buying_power.json", {"buying_power": "954400"})
        write_json(tmp_path / "broker_account_summary" / trade_date / "account_summary.json", {})
        write_json(tmp_path / "broker_snapshot_summary" / trade_date / "broker_snapshot_summary.json", {"orders_count": 1, "positions_count": 0, "executions_count": 0, "buying_power": "954400"})
        return {"status": "PASS", "api_called": True, "artifacts_written": True}

    monkeypatch.setattr(operations_module, "TachibanaDemoOrderAdapter", FakeAdapter)
    monkeypatch.setattr(operations_module, "refresh_demo_broker_readonly_artifacts", fake_refresh)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)
    row = result["submitted_orders"][0]

    assert FakeAdapter.calls == 1
    assert result["status"] == "PASS"
    assert row["status"] == "ORDER_ACCEPTED"
    assert row["submit_classification"] == "ACCEPTED"
    assert row["classification_source"] == "broker_readonly_order_confirmation"
    assert row["post_send_unknown"] is True
    assert row["broker_readonly_confirmation_attempted"] is True
    assert row["broker_readonly_confirmation_status"] == "CONFIRMED"
    assert row["broker_order_id_hash"] == "order_hash"
    assert row["raw_broker_order_id_saved"] is False
    assert result["production_order_submitted"] is False


def test_post_send_unknown_without_broker_confirmation_is_review_required(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "42650", "code": "42650", "side": "BUY", "quantity": "100", "order_type": "CASH_EQUITY", "price_type": "LIMIT", "limit_price": "456", "estimated_value": "45600"}],
    )
    write_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json", {
        "approval_id": "approval-1",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "approved_item_ids": ["buy_1"],
        "approval_expires_at": "2099-01-01T00:00:00+00:00",
        "approval_max_notional": "850000",
        "max_notional": "850000",
    })
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})
    _write_listed(tmp_path, ["42650"])

    class FakeAdapter:
        calls = 0

        def submit_cash_stock_order(self, command):
            FakeAdapter.calls += 1

            class Result:
                def to_dict(self):
                    return {
                        "status": "POST_SEND_UNKNOWN",
                        "broker_order_api_called": True,
                        "demo_order_executed": False,
                        "submit_classification": "POST_SEND_UNKNOWN",
                        "post_send_unknown": True,
                        "broker_readonly_confirmation_status": "PENDING",
                        "response": {"accepted": False, "status": "POST_SEND_UNKNOWN"},
                    }

            return Result()

    def fake_refresh(*, trade_date, root, run_enabled=False, include_quotes=False):
        return {"status": "BLOCK", "api_called": True, "artifacts_written": False}

    monkeypatch.setattr(operations_module, "TachibanaDemoOrderAdapter", FakeAdapter)
    monkeypatch.setattr(operations_module, "refresh_demo_broker_readonly_artifacts", fake_refresh)
    _write_pending_from_dated_artifacts(tmp_path, "2026-06-29", "2026-06-29")

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)
    row = result["submitted_orders"][0]

    assert FakeAdapter.calls == 1
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["status"] == "REVIEW_REQUIRED"
    assert row["submit_classification"] == "REVIEW_REQUIRED"
    assert row["post_send_unknown"] is True
    assert row["broker_readonly_confirmation_attempted"] is True
    assert row["broker_readonly_confirmation_status"] == "NOT_CONFIRMED"
    assert row["broker_order_api_called"] is True
    assert row["demo_order_submitted"] is False
    assert result["production_order_submitted"] is False


def _write_listed(tmp_path, codes: list[str]) -> None:
    listed = tmp_path / "feature_refresh" / "2026-06-29" / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    listed.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    pd.DataFrame([{"Code": code, "code": code, "MktNm": "プライム", "ProdCat": "011"} for code in codes]).to_parquet(listed)


def _write_pending_from_dated_artifacts(tmp_path: Path, plan_date: str, submit_date: str) -> None:
    order_plan_path = tmp_path / "order_plan" / plan_date / "order_plan.json"
    approval_path = tmp_path / "approval_artifact" / plan_date / "approval_artifact.json"
    order_plan = read_json(order_plan_path)
    approval = read_json(approval_path)
    plan_id = str(order_plan.get("plan_id") or f"operation_plan_{plan_date}_test")
    order_plan["plan_id"] = plan_id
    order_plan.setdefault("status", "PASS")
    order_plan.setdefault("requires_approval", True)
    order_plan.setdefault("buy_item_count", sum(1 for item in order_plan.get("items", []) if item.get("side") == "BUY"))
    order_plan.setdefault("sell_item_count", sum(1 for item in order_plan.get("items", []) if item.get("side") == "SELL"))
    approval["plan_id"] = plan_id
    approval.setdefault("status", "APPROVED")
    approval.setdefault("approval_id", "approval-1")
    approval.setdefault("approval_expires_at", "2099-01-01T00:00:00+00:00")
    approval.setdefault("approval_max_notional", approval.get("max_notional", "850000"))
    approval.setdefault("approval_max_notional_source", "dynamic_max_exposure")
    approval.setdefault("production_order_allowed", False)
    write_json(order_plan_path, order_plan)
    write_json(approval_path, approval)
    pending = build_pending_order_plan(
        root=tmp_path,
        order_plan=order_plan,
        order_plan_path=order_plan_path,
        plan_created_date=plan_date,
        intended_submit_date=submit_date,
        target_session_date=submit_date,
        promotion_source="test",
    )
    pending["state"] = "APPROVED"
    pending["approval"].update(
        {
            "status": "APPROVED",
            "approval_id": approval["approval_id"],
            "path": f"approval_artifact/{plan_date}/approval_artifact.json",
            "hash": stable_hash(approval),
            "approved_item_ids": list(approval.get("approved_item_ids", [])),
            "approval_expires_at": approval["approval_expires_at"],
            "approval_max_notional": approval["approval_max_notional"],
            "approval_max_notional_source": approval["approval_max_notional_source"],
            "source_order_plan_hash": stable_hash(order_plan),
        }
    )
    write_pending_order_plan(tmp_path, pending)
