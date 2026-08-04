from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    evaluate_buy_item_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicyError,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import position_count_authority_from_context
from ai_fund_lab_v2.runtime_v2.position_sizing_authority import resolve_position_sizing_authority
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import cash_exposure_authority_from_context


def test_phase26_step4_position_sizing_authority_wins_over_fixed_weight_path(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=500_000, market_value=700_000, total_equity=1_200_000)
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(
            pending_item_id="buy-1",
            symbol="7203",
            estimated_amount=175_000,
            quantity_contract=_position_sizing_context(amount=180_000, symbol="7203"),
        ),
        policy=policy,
        current=current,
        authority_source="phase26_step4_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="demo",
    )

    assert evidence["status"] == "PASS"
    assert evidence["selected_position_amount"] == 180_000
    assert evidence["position_sizing_authority_winner"] == "strategy_position_sizing"
    assert evidence["legacy_position_sizing_used"] is False
    assert evidence["position_sizing_fallback_used"] is False
    assert "max_position_amount" not in evidence
    assert "max_position_weight" not in evidence


def test_phase26_step4_position_sizing_blocks_without_fixed_weight_fallback(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=500_000, market_value=700_000, total_equity=1_200_000)
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(
            pending_item_id="buy-1",
            symbol="7203",
            estimated_amount=190_000,
            quantity_contract=_position_sizing_context(amount=180_000, symbol="7203"),
        ),
        policy=policy,
        current=current,
        authority_source="phase26_step4_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="demo",
    )

    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["violated_policy"] == "position_sizing"
    assert evidence["reason"] == "estimated amount exceeds selected_position_amount"
    assert evidence["selected_position_amount"] == 180_000


def test_phase26_step4_missing_position_sizing_fails_closed(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json"))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=500_000, market_value=700_000, total_equity=1_200_000)
    )

    evidence = evaluate_buy_item_submit_feasibility(
        item=SimpleNamespace(pending_item_id="buy-1", symbol="7203", estimated_amount=100_000),
        policy=policy,
        current=current,
        authority_source="phase26_step4_test",
        position_count_authority=_position_count_authority(policy, current),
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="historical",
    )

    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["violated_policy"] == "position_sizing"
    assert evidence["position_sizing_authority_winner"] == "REVIEW_REQUIRED"
    assert evidence["legacy_position_sizing_used"] is False
    assert evidence["position_sizing_fallback_used"] is False


def test_phase26_step4_mode_parity_uses_same_position_sizing_authority_contract() -> None:
    authorities = [
        resolve_position_sizing_authority(
            symbol="7203",
            business_date="2026-07-09",
            runtime_mode=mode,
            active_deployment_capital=1_200_000,
            selected_dynamic_exposure_ratio=0.85,
            selected_runtime_exposure_limit=1_020_000,
            selected_dynamic_position_count=8,
            current_position_market_value=0.0,
            policy_context=_position_sizing_context(amount=180_000, symbol="7203"),
            consumer=f"phase26_step4_{mode}",
        )
        for mode in ("production", "demo", "historical")
    ]

    assert {authority.position_sizing_authority_winner for authority in authorities} == {"strategy_position_sizing"}
    assert {authority.runtime_path for authority in authorities} == {"Production/Demo/Historical common runtime_v2"}
    assert {authority.selected_position_amount for authority in authorities} == {180_000}


def test_phase26_step4_policy_rejects_legacy_fixed_position_weight_config(tmp_path: Path) -> None:
    path = _policy(tmp_path / "capital_policy.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["max_position_weight"] = 0.2
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(CapitalDeploymentPolicyError, match="legacy position sizing policy fields unsupported"):
        load_capital_deployment_policy(path)


def _position_count_authority(policy, current):
    return position_count_authority_from_context(
        {"target_position_count": 8, "safety_hard_maximum": None},
        business_date="2026-07-09",
        runtime_mode="demo",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer="phase26_step4_test",
    )


def _cash_exposure_authority(current):
    return cash_exposure_authority_from_context(
        {"target_cash_ratio": 0.10, "target_gross_exposure_ratio": 0.85, "maximum_gross_exposure_ratio": 0.90},
        business_date="2026-07-09",
        runtime_mode="demo",
        current_total_equity=current.current_total_equity,
        active_deployment_capital=current.active_deployment_capital,
        current_cash=current.cash,
        current_market_value=current.current_exposure,
        consumer="phase26_step4_test",
    )


def _current(path: Path, *, cash: float, market_value: float, total_equity: float) -> Path:
    path.write_text(
        json.dumps(
            {
                "cash": cash,
                "buying_power": cash,
                "market_value": market_value,
                "total_equity": total_equity,
                "runtime_evaluation_capital": 1_000_000,
                "positions": [{"symbol": "1111", "quantity": 100, "market_value": market_value}],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _policy(path: Path) -> Path:
    path.write_text(
        json.dumps(
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
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _position_sizing_context(*, amount: float, symbol: str) -> dict:
    return {
        "symbol": symbol,
        "selected_position_amount": amount,
        "remaining_add_capacity": amount,
        "selected_position_weight": 0.18,
        "target_weight": 0.18,
        "target_notional": amount,
        "incremental_buy_notional": amount,
        "maximum_position_weight": 0.18,
        "portfolio_policy_source": "phase26_step4_fixture_portfolio_policy",
    }
