from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.operations.operations import run_approval_prepare, run_daily_plan, run_market_refresh
from ai_fund_lab_v2.operations.io import read_json


def test_approval_prepare_can_create_pending_and_approved_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )

    pending = run_approval_prepare(trade_date="2026-06-29", root=tmp_path)
    assert pending["approved"] is False

    run_approval_prepare(trade_date="2026-06-29", root=tmp_path, approve=True, approver_label="operator", max_notional=Decimal("120000"))
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")
    assert artifact["demo_order_allowed"] is True
    assert artifact["production_order_allowed"] is False
    assert artifact["approved_item_ids"] == ["buy_1"]


def test_auto_demo_approval_is_demo_only_and_records_source(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})

    result = run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True, max_notional=Decimal("120000"))
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")

    assert result["approved"] is True
    assert artifact["approval_source"] == "demo_auto_approval"
    assert artifact["manual_approval_required"] is False
    assert artifact["demo_order_allowed"] is True
    assert artifact["production_order_allowed"] is False
    assert artifact["approval_max_notional_source"] == "manual_override"


def test_auto_demo_approval_defaults_to_dynamic_demo_evaluation_equity(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "20000000", "broker_actual_equity": "20000000", "current_exposure": "0"})

    result = run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True)
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")

    assert result["approved"] is True
    assert artifact["max_notional"] == "850000"
    assert artifact["approval_max_notional"] == "850000"
    assert artifact["approval_max_notional_source"] == "dynamic_max_exposure"
    assert artifact["equity_basis"] == "1000000"
    assert artifact["equity_basis_source"] == "demo_evaluation_equity"
    assert artifact["max_total_exposure_ratio"] == "0.85"
    assert artifact["current_exposure"] == "0"
    assert artifact["available_exposure_budget"] == "850000"
    assert artifact["available_buying_power_or_cash"] == "1000000"
    assert artifact["approval_max_notional_inputs"]["demo_broker_cash_used_for_equity_basis"] is False


def test_auto_demo_approval_dynamic_budget_reflects_current_exposure(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_positions" / "2026-06-29" / "positions.json", {"positions": [{"issue_code": "6758", "quantity": "100", "market_value": "300000"}]})
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "20000000", "broker_actual_equity": "20000000", "current_exposure": "300000"})

    run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True)
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")

    assert artifact["approval_max_notional"] == "550000"
    assert artifact["current_exposure"] == "300000"
    assert artifact["current_exposure_source"] == "broker_positions_market_value"
    assert artifact["available_exposure_budget"] == "550000"


def test_auto_demo_approval_uses_persistent_demo_ledger_net_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_positions" / "2026-06-29" / "positions.json", {"positions": []})
    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "20000000", "broker_actual_equity": "20000000", "current_exposure": "0"})
    ledger = tmp_path / "demo_ledger" / "positions.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text('{"business_date":"2026-06-29","record_type":"demo_special_simulated_position","net_quantity":"0","fill_price":"5410","position_state":"OPENED_THEN_CLOSED_BY_SIMULATION"}\n', encoding="utf-8")

    run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True)
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")

    assert artifact["approval_max_notional"] == "850000"
    assert artifact["current_exposure"] == "0"
    assert artifact["current_exposure_source"] == "persistent_demo_ledger"


def test_manual_max_notional_override_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})

    run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True, max_notional=Decimal("120000"))
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")

    assert artifact["approval_max_notional"] == "120000"
    assert artifact["approval_max_notional_source"] == "manual_override"
    assert artifact["approval_max_notional_inputs"]["dynamic_approval_max_notional"] == "850000"


def test_auto_demo_approval_fails_closed_in_production(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "production")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[{"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"}],
    )

    result = run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True, max_notional=Decimal("120000"))

    assert result["approved"] is False
    assert "auto_demo_approval_requires_demo_environment" in result["approval_blocks"]


def test_auto_demo_approval_can_approve_multiple_buy_items_within_total_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[
            {"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"},
            {"item_id": "buy_2", "issue_code": "6758", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"},
        ],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})

    result = run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True, max_notional=Decimal("250000"))
    artifact = read_json(tmp_path / "approval_artifact" / "2026-06-29" / "approval_artifact.json")

    assert result["approved"] is True
    assert artifact["approved_item_ids"] == ["buy_1", "buy_2"]


def test_auto_demo_approval_blocks_multiple_buy_items_over_total_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date="2026-06-29", root=tmp_path)
    run_daily_plan(
        trade_date="2026-06-29",
        root=tmp_path,
        plan_items=[
            {"item_id": "buy_1", "issue_code": "7203", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"},
            {"item_id": "buy_2", "issue_code": "6758", "side": "BUY", "quantity": "100", "limit_price": "1000", "estimated_value": "100000"},
        ],
    )
    from ai_fund_lab_v2.operations.io import write_json

    write_json(tmp_path / "broker_snapshot_summary" / "2026-06-29" / "broker_snapshot_summary.json", {"buying_power": "1000000", "broker_actual_equity": "1000000", "current_exposure": "0"})

    result = run_approval_prepare(trade_date="2026-06-29", root=tmp_path, auto_demo_approval=True, max_notional=Decimal("150000"))

    assert result["approved"] is False
    assert "total_buy_notional_exceeds_auto_approval_max" in result["approval_blocks"]


def test_auto_approval_launchd_does_not_use_fixed_600000_override():
    plist = Path("tools/launchd/com.aifundlab.operations.auto_approval.plist").read_text()

    assert "--max-notional" not in plist
    assert "600000" not in plist
