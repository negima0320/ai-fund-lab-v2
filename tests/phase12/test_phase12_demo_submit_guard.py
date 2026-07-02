from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.operations.guards import evaluate_max_exposure
import ai_fund_lab_v2.operations.operations as operations_module
from ai_fund_lab_v2.operations.operations import run_approval_prepare, run_daily_plan, run_demo_submit, run_market_refresh, run_preflight
from ai_fund_lab_v2.operations.io import write_json


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
    assert "approval_missing_or_not_demo_allowed" in result["blocks"]
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
    run_approval_prepare(trade_date="2026-06-29", root=tmp_path, approve=True, approver_label="operator", max_notional=Decimal("120000"))

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "PASS"
    assert result["submitted_orders"][0]["status"] == "DRY_RUN_READY"
    assert result["demo_order_submitted"] is False
    assert result["production_order_submitted"] is False


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
            "approval_expires_at": "2026-07-02T04:30:00+00:00",
            "max_notional": "600000",
        },
    )

    result = run_demo_submit(trade_date="2026-07-02", root=tmp_path)

    assert result["status"] == "PASS"
    assert result["submit_run_date"] == "2026-07-02"
    assert result["order_plan_source_date"] == "2026-07-01"
    assert result["approval_source_date"] == "2026-07-01"
    assert result["uses_previous_business_day_order_plan"] is True
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

    result = run_demo_submit(trade_date="2026-06-29", root=tmp_path, execute_demo_order=True, second_password_present=True)
    rows = {row["item_id"]: row for row in result["submitted_orders"]}

    assert result["status"] == "PASS"
    assert result["accepted_order_count"] == 5
    assert result["blocked_item_count"] == 0
    assert result["blocked_items"] == []
    assert rows["buy_4"]["status"] == "ORDER_ACCEPTED"
    assert rows["buy_5"]["status"] == "ORDER_ACCEPTED"
    assert result["production_order_submitted"] is False


def _write_listed(tmp_path, codes: list[str]) -> None:
    listed = tmp_path / "feature_refresh" / "2026-06-29" / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    listed.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    pd.DataFrame([{"Code": code, "code": code, "MktNm": "プライム", "ProdCat": "011"} for code in codes]).to_parquet(listed)
