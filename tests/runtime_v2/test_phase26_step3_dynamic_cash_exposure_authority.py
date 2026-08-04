from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import resolve_cash_exposure_authority
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    evaluate_buy_item_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicyError,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import position_count_authority_from_context


def test_phase26_step3_dynamic_cash_exposure_wins_over_legacy_fixed_exposure(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=700_000, market_value=500_000, total_equity=1_200_000, positions=4)
    )
    authority = resolve_cash_exposure_authority(
        business_date="2026-07-09",
        runtime_mode="demo",
        current_total_equity=current.current_total_equity,
        active_deployment_capital=current.active_deployment_capital,
        current_cash=current.cash,
        current_market_value=current.current_exposure,
        policy_context={"target_cash_ratio": 0.20, "target_gross_exposure_ratio": 0.80, "maximum_gross_exposure_ratio": 0.88},
        consumer="phase26_step3_test",
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(
            pending_item_id="buy-1",
            symbol="9001",
            estimated_amount=100_000,
            quantity_contract=_position_sizing_context(120_000),
        ),
        policy=policy,
        current=current,
        authority_source="phase26_step3_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=authority,
        business_date="2026-07-09",
        runtime_mode="demo",
    )

    assert evidence["status"] == "PASS"
    assert evidence["strategy_requested_cash_ratio"] == 0.20
    assert evidence["selected_dynamic_exposure_ratio"] == 0.80
    assert evidence["selected_runtime_exposure_limit"] == 960_000
    assert evidence["target_cash_amount"] == 240_000
    assert evidence["cash_exposure_authority_winner"] == "strategy_dynamic_cash_exposure"
    assert evidence["legacy_cash_config_used"] is False
    assert evidence["legacy_exposure_config_used"] is False
    assert evidence["cash_exposure_fallback_used"] is False
    assert "configured_legacy_max_exposure" not in evidence
    assert "max_exposure" not in evidence


def test_phase26_step3_missing_dynamic_cash_exposure_does_not_fallback_to_old_values(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=700_000, market_value=500_000, total_equity=1_200_000, positions=4)
    )
    authority = resolve_cash_exposure_authority(
        runtime_root=tmp_path / ".runtime",
        business_date="2026-07-09",
        runtime_mode="historical",
        current_total_equity=current.current_total_equity,
        active_deployment_capital=current.active_deployment_capital,
        current_cash=current.cash,
        current_market_value=current.current_exposure,
        consumer="phase26_step3_test",
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(
            pending_item_id="buy-1",
            symbol="9001",
            estimated_amount=100_000,
            quantity_contract=_position_sizing_context(120_000),
        ),
        policy=policy,
        current=current,
        authority_source="phase26_step3_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=authority,
        business_date="2026-07-09",
        runtime_mode="historical",
    )

    assert authority.status == "REVIEW_REQUIRED"
    assert authority.cash_exposure_binding_constraint == "REVIEW_REQUIRED"
    assert authority.selected_runtime_exposure_limit == 0.0
    assert authority.cash_exposure_fallback_used is False
    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["violated_policy"] == "dynamic_cash_exposure"
    assert evidence["selected_dynamic_cash_ratio"] is None
    assert evidence["selected_dynamic_exposure_ratio"] is None
    assert evidence["selected_runtime_exposure_limit"] == 0.0


def test_phase26_step3_runtime_policy_rejects_legacy_cash_exposure_fields(tmp_path: Path) -> None:
    path = _policy(tmp_path / "capital_policy.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update({"target_investment_ratio": 0.85, "cash_buffer": 0.05, "max_exposure": 850_000})
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(CapitalDeploymentPolicyError, match="legacy cash/exposure policy fields unsupported"):
        load_capital_deployment_policy(path)


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
        consumer="phase26_step3_test",
    )


def _current(path: Path, *, cash: float, market_value: float, total_equity: float, positions: int) -> Path:
    payload = {
        "cash": cash,
        "buying_power": cash,
        "market_value": market_value,
        "total_equity": total_equity,
        "runtime_evaluation_capital": 1_000_000,
        "positions": [
            {"symbol": f"{index:04d}", "quantity": 100, "market_value": market_value / positions}
            for index in range(1, positions + 1)
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _policy(path: Path) -> Path:
    payload = {
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
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
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
        "portfolio_policy_source": "phase26_step3_fixture_portfolio_policy",
    }
