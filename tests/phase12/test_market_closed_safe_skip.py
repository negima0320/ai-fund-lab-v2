from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.operations.io import write_json
from ai_fund_lab_v2.operations.operations import (
    run_approval_prepare,
    run_audit,
    run_daily_plan,
    run_demo_special_fill_simulation,
    run_demo_submit,
    run_fill_monitor,
    run_market_refresh,
    run_preflight,
    run_reconcile,
    run_safety_monitor,
)


MARKET_CLOSED_DATE = "2026-09-21"


def test_market_closed_daily_plan_approval_submit_and_special_fill_skip(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    market = run_market_refresh(trade_date=MARKET_CLOSED_DATE, root=tmp_path)
    plan = run_daily_plan(trade_date=MARKET_CLOSED_DATE, root=tmp_path)
    approval = run_approval_prepare(
        trade_date=MARKET_CLOSED_DATE,
        root=tmp_path,
        auto_demo_approval=True,
        max_notional=Decimal("600000"),
    )
    submit = run_demo_submit(
        trade_date=MARKET_CLOSED_DATE,
        root=tmp_path,
        execute_demo_order=True,
        second_password_present=True,
    )
    special = run_demo_special_fill_simulation(
        trade_date=MARKET_CLOSED_DATE,
        root=tmp_path,
        demo_special_fill_simulation_enabled=True,
    )

    assert market["status"] == "SKIPPED_MARKET_CLOSED"
    assert plan["status"] == "SKIPPED_MARKET_CLOSED"
    assert plan["buy_item_count"] == 0
    assert plan["sell_item_count"] == 0
    assert approval["status"] == "SKIPPED_MARKET_CLOSED"
    assert approval["demo_order_allowed"] is False
    assert submit["status"] == "SKIPPED_MARKET_CLOSED"
    assert submit["demo_order_executed"] is False
    assert submit["clm_kabu_new_order_called"] is False
    assert special["status"] == "SKIPPED_MARKET_CLOSED"
    assert special["simulated_fill"] is False
    assert not (tmp_path / "approval_artifact" / MARKET_CLOSED_DATE / "approval_artifact.json").exists()


def test_market_closed_readonly_steps_use_market_closed_statuses(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    preflight = run_preflight(trade_date=MARKET_CLOSED_DATE, root=tmp_path, required_env=[])
    fill = run_fill_monitor(trade_date=MARKET_CLOSED_DATE, root=tmp_path)
    safety = run_safety_monitor(trade_date=MARKET_CLOSED_DATE, root=tmp_path)
    reconcile = run_reconcile(trade_date=MARKET_CLOSED_DATE, root=tmp_path)

    assert preflight["status"] == "PASS_MARKET_CLOSED_READONLY_ONLY"
    assert preflight["submit_allowed"] is False
    assert fill["status"] == "PASS_MARKET_CLOSED_MONITOR_ONLY"
    assert safety["status"] == "PASS_MARKET_CLOSED_SYSTEM_ONLY"
    assert reconcile["status"] == "PASS_MARKET_CLOSED_RECONCILE_ONLY"


def test_operation_audit_blocks_if_order_trace_exists_on_market_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    calendar = {
        "trade_date": MARKET_CLOSED_DATE,
        "is_business_day": False,
        "market_closed": True,
        "market_closed_reason": "JP_MARKET_HOLIDAY_FALLBACK",
        "calendar_source": "fallback",
    }
    write_json(
        tmp_path / "daily_manifest" / MARKET_CLOSED_DATE / "daily_manifest.json",
        {"business_date": MARKET_CLOSED_DATE, "status": "PASS", "market_calendar": calendar},
    )
    write_json(
        tmp_path / "submitted_orders" / MARKET_CLOSED_DATE / "submitted_orders.json",
        {
            "business_date": MARKET_CLOSED_DATE,
            "status": "PASS",
            "market_calendar": calendar,
            "demo_order_executed": True,
            "broker_order_api_called": True,
            "production_order_submitted": False,
        },
    )

    audit = run_audit(root=tmp_path)

    assert audit["status"] == "BLOCK"
    assert audit["orders_blocked_on_market_closed"] is False
    assert audit["market_closed_order_trace_count"] == 1


def test_operation_audit_pass_market_closed_without_order_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    calendar = {
        "trade_date": MARKET_CLOSED_DATE,
        "is_business_day": False,
        "market_closed": True,
        "market_closed_reason": "JP_MARKET_HOLIDAY_FALLBACK",
        "calendar_source": "fallback",
    }
    write_json(
        tmp_path / "daily_manifest" / MARKET_CLOSED_DATE / "daily_manifest.json",
        {"business_date": MARKET_CLOSED_DATE, "status": "PASS", "market_calendar": calendar},
    )

    audit = run_audit(root=tmp_path)

    assert audit["status"] == "PASS_MARKET_CLOSED"
    assert audit["market_closed_safe_skip"] is True
    assert audit["orders_blocked_on_market_closed"] is True
