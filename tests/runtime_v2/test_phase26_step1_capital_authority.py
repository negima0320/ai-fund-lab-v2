from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    evaluate_buy_item_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import position_count_authority_from_context
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import cash_exposure_authority_from_context
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy


def test_phase26_step1_current_total_equity_wins_over_runtime_evaluation_capital(tmp_path: Path) -> None:
    current_path = tmp_path / "state.json"
    _write_json(
        current_path,
        {
            "cash": 388_010,
            "buying_power": 388_010,
            "market_value": 679_650,
            "total_equity": 1_067_660,
            "runtime_evaluation_capital": 1_000_000,
            "positions": [{"symbol": "1111", "quantity": 100, "market_value": 679_650}],
        },
    )

    current = load_runtime_current_exposure(current_path)

    assert current.selected_capital_source == "current_state.total_equity"
    assert current.active_deployment_capital == 1_067_660
    assert current.initial_or_bootstrap_capital == 1_000_000
    assert current.capital_fallback_used is False


def test_phase26_step1_buy_feasibility_uses_active_deployment_capital_not_fixed_policy_cap(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(
            tmp_path / "state.json",
            cash=500_000,
            market_value=567_660,
            total_equity=1_067_660,
            runtime_evaluation_capital=1_000_000,
        )
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(
            pending_item_id="buy-1",
            symbol="7203",
            estimated_amount=205_000,
            quantity_contract=_position_sizing_context(220_000),
        ),
        policy=policy,
        current=current,
        authority_source="phase26_step1_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=_cash_exposure_authority(current),
    )

    assert evidence["status"] == "PASS"
    assert evidence["capital_authority_winner"] == "current_total_equity"
    assert evidence["active_deployment_capital"] == 1_067_660
    assert evidence["selected_position_amount"] == 220_000
    assert evidence["position_sizing_authority_winner"] == "strategy_position_sizing"
    assert evidence["selected_runtime_exposure_limit"] == 907_511
    assert evidence["legacy_exposure_config_used"] is False
    assert evidence["cash_exposure_fallback_used"] is False
    assert evidence["legacy_capital_config_used"] is False
    assert evidence["capital_fallback_used"] is False


def test_phase26_step1_fixed_evaluation_capital_no_longer_blocks_growth_case(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(
            tmp_path / "state.json",
            cash=400_000,
            market_value=700_000,
            total_equity=1_100_000,
            runtime_evaluation_capital=1_000_000,
        )
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(
            pending_item_id="buy-1",
            symbol="7203",
            estimated_amount=210_000,
            quantity_contract=_position_sizing_context(220_000),
        ),
        policy=policy,
        current=current,
        authority_source="phase26_step1_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=_cash_exposure_authority(current),
    )

    assert evidence["status"] == "PASS"
    assert evidence["selected_position_amount"] == 220_000
    assert evidence["legacy_position_sizing_used"] is False
    assert evidence["position_sizing_fallback_used"] is False


def _current(
    path: Path,
    *,
    cash: float,
    market_value: float,
    total_equity: float,
    runtime_evaluation_capital: float,
) -> Path:
    _write_json(
        path,
        {
            "cash": cash,
            "buying_power": cash,
            "market_value": market_value,
            "total_equity": total_equity,
            "runtime_evaluation_capital": runtime_evaluation_capital,
            "positions": [{"symbol": "1111", "quantity": 100, "market_value": market_value}],
        },
    )
    return path


def _policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _position_sizing_context(amount: float) -> dict:
    return {
        "selected_position_amount": amount,
        "remaining_add_capacity": amount,
        "selected_position_weight": 0.18,
        "target_weight": 0.18,
        "target_notional": amount,
        "incremental_buy_notional": amount,
        "maximum_position_weight": 0.18,
        "portfolio_policy_source": "phase26_step1_fixture_portfolio_policy",
    }


def _position_count_authority(policy, current):
    return position_count_authority_from_context(
        {
            "target_position_count": 8,
            "safety_hard_maximum": None,
        },
        business_date="2026-07-09",
        runtime_mode="demo",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer="phase26_step1_capital_regression",
    )


def _cash_exposure_authority(current):
    return cash_exposure_authority_from_context(
        {
            "target_cash_ratio": 0.10,
            "target_gross_exposure_ratio": 0.85,
            "maximum_gross_exposure_ratio": 0.90,
        },
        business_date="2026-07-09",
        runtime_mode="demo",
        current_total_equity=current.current_total_equity,
        active_deployment_capital=current.active_deployment_capital,
        current_cash=current.cash,
        current_market_value=current.current_exposure,
        consumer="phase26_step1_capital_regression",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
