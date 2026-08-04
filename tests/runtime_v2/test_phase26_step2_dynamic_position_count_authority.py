from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    evaluate_buy_item_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import resolve_position_count_authority
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import cash_exposure_authority_from_context
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy


def test_phase26_step2_dynamic_position_count_wins_over_legacy_max_positions(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    artifact_path = _dynamic_position_count_artifact(root, target_position_count=8, current_position_count=5)
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json", max_positions=5))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=700_000, market_value=500_000, total_equity=1_200_000, positions=5)
    )

    authority = resolve_position_count_authority(
        runtime_root=root,
        business_date="2026-07-09",
        runtime_mode="demo",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer="phase26_step2_test",
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
        authority_source="phase26_step2_test",
        position_count_authority=authority,
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="demo",
    )

    assert artifact_path.is_file()
    assert authority.status == "PASS"
    assert authority.selected_dynamic_position_count == 8
    assert authority.available_position_slots == 3
    assert authority.configured_legacy_max_positions == 5
    assert authority.legacy_position_count_config_used is False
    assert authority.position_count_fallback_used is False
    assert evidence["status"] == "PASS"
    assert evidence["active_max_positions"] == 8
    assert evidence["configured_legacy_max_positions"] == 5
    assert evidence["position_count_authority_winner"] == "safety_hard_maximum_only"
    assert evidence["legacy_position_count_config_used"] is False
    assert evidence["position_count_fallback_used"] is False
    assert evidence["capital_authority_winner"] == "current_total_equity"
    assert evidence["active_deployment_capital"] == 1_200_000


def test_phase26_step2_no_legacy_fallback_when_dynamic_authority_missing(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json", max_positions=5))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=700_000, market_value=500_000, total_equity=1_200_000, positions=4)
    )

    authority = resolve_position_count_authority(
        runtime_root=tmp_path / ".runtime",
        business_date="2026-07-09",
        runtime_mode="demo",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer="phase26_step2_test",
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
        authority_source="phase26_step2_test",
        position_count_authority=authority,
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="demo",
    )

    assert authority.status == "REVIEW_REQUIRED"
    assert authority.selected_dynamic_position_count == 0
    assert authority.configured_legacy_max_positions == 5
    assert authority.legacy_position_count_config_used is False
    assert authority.position_count_fallback_used is False
    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["violated_policy"] == "safety_hard_maximum"
    assert evidence["reason"] == "dynamic_position_count_authority_missing"


def test_phase26_step2_current_holdings_at_target_position_count_do_not_block_buy(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _dynamic_position_count_artifact(root, target_position_count=1, current_position_count=1, safety_hard_maximum=10)
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json", max_positions=5))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=700_000, market_value=100_000, total_equity=800_000, positions=1)
    )

    authority = resolve_position_count_authority(
        runtime_root=root,
        business_date="2026-07-09",
        runtime_mode="historical",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer="phase26_step2_test",
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
        authority_source="phase26_step2_test",
        position_count_authority=authority,
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="historical",
    )

    assert authority.status == "PASS"
    assert authority.strategy_requested_position_count == 1
    assert authority.safety_hard_maximum == 10
    assert authority.position_count_binding_constraint == "SAFETY_HARD_MAXIMUM"
    assert authority.available_position_slots == 9
    assert evidence["status"] == "PASS"
    assert evidence["violated_policy"] == ""


def test_phase26_a_safety_hard_maximum_still_blocks_new_buy(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _dynamic_position_count_artifact(root, target_position_count=10, current_position_count=1, safety_hard_maximum=1)
    policy = load_capital_deployment_policy(_policy(tmp_path / "capital_policy.json", max_positions=5))
    current = load_runtime_current_exposure(
        _current(tmp_path / "state.json", cash=700_000, market_value=100_000, total_equity=800_000, positions=1)
    )

    authority = resolve_position_count_authority(
        runtime_root=root,
        business_date="2026-07-09",
        runtime_mode="demo",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer="phase26_a_test",
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
        authority_source="phase26_a_test",
        position_count_authority=authority,
        cash_exposure_authority=_cash_exposure_authority(current),
        business_date="2026-07-09",
        runtime_mode="demo",
    )

    assert authority.status == "PASS"
    assert authority.position_count_binding_constraint == "SAFETY_HARD_MAXIMUM"
    assert authority.available_position_slots == 0
    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["violated_policy"] == "safety_hard_maximum"
    assert evidence["reason"] == "BUY would exceed safety_hard_maximum"


def _dynamic_position_count_artifact(
    root: Path,
    *,
    target_position_count: int,
    current_position_count: int,
    safety_hard_maximum: int | None = None,
) -> Path:
    path = root / "strategy_artifacts" / "dynamic_position_count" / "2026-07-09" / "dynamic_position_count.json"
    payload = {
        "schema_version": "dynamic_position_count.v1",
        "producer_version": "phase22_h_dynamic_position_count_producer.v1",
        "business_date": "2026-07-09",
        "as_of": "2026-07-09T00:00:00+00:00",
        "feature_date": "2026-07-09",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "PASS",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "target_position_count_resolution": "RESOLVED",
        "minimum_position_count": 0,
        "calculated_target_position_count": target_position_count,
        "target_position_count": target_position_count,
        "maximum_position_count": target_position_count,
        "safety_hard_maximum": safety_hard_maximum,
        "legacy_active_max_positions": 5,
        "strategy_minimum_position_count": 0,
        "strategy_target_position_count": target_position_count,
        "strategy_maximum_position_count": target_position_count,
        "actual_target_position_count": target_position_count,
        "meaningful_allocation_position_count": target_position_count,
        "safety_hard_maximum_status": "REMOVED",
        "strategy_fixed_position_cap_used": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False,
        "capacity_constraint_status": "SUFFICIENT",
        "ceiling_authority_status": "SEPARATED",
        "confidence": 0.9,
        "uncertainty": "LOW",
        "reason_codes": ["fixed_position_count_safety_hard_maximum_removed"],
        "eligible_opportunity_count": target_position_count,
        "available_candidate_count": target_position_count,
        "available_opportunity_count": target_position_count,
        "shadow_comparison": {
            "existing_active_max_positions": 5,
            "dynamic_minimum": 0,
            "dynamic_target": target_position_count,
            "dynamic_maximum": target_position_count,
            "difference_from_existing": target_position_count - 5,
            "would_change_available_slots": True,
            "runtime_behavior_changed": False,
        },
        "current_position_count": current_position_count,
        "capital_affordable_position_count": target_position_count,
        "liquidity_feasible_position_count": target_position_count,
        "position_count_posture": "INCREASE",
        "source_artifacts": [{"role": "portfolio_policy", "path": "test", "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "portfolio_policy", "path": "test", "sha256": "0" * 64}],
        "temporal_safety": {
            "point_in_time": True,
            "future_leakage_used": False,
            "feature_date_lte_business_date": True,
            "implicit_latest_fallback_used": False,
            "previous_day_target_copied": False,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


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


def _policy(path: Path, *, max_positions: int) -> Path:
    payload = {
        "policy_version": "capital_deployment_v1",
        "policy_source": str(path),
        "evaluation_capital": 1_000_000,
        "max_positions": max_positions,
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
        "portfolio_policy_source": "phase26_step2_fixture_portfolio_policy",
    }


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
        consumer="phase26_step2_regression",
    )
