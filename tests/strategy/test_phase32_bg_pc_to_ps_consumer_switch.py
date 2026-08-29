from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import CashExposureAuthority
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    RuntimeCurrentExposure,
    evaluate_buy_item_submit_feasibility,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import PositionCountAuthority
from ai_fund_lab_v2.strategy.marginal_capital_frontier_authority import (
    activate_pc_to_ps_production_consumer_switch,
    build_marginal_capital_frontier_authority_payload,
)
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingConfig,
    PositionSizingSourceSummary,
    build_position_sizing_payload,
    load_position_sizing_config,
)


BUSINESS_DATE = "2026-08-29"


def test_phase32_bg_new_switched_target_consumed_by_ps() -> None:
    row = _new("10010", rank=1, target_weight=0.05)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0))
    position = payload["positions"][0]

    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "PASS"
    assert position["marginal_capital_frontier_switch_sizing_eligibility"] == "SELECTED_BY_BG_BF_AGGREGATED_TARGET_AUTHORITY"
    assert position["quantity_delta_candidate"] == 100
    assert position["final_quantity_delta"] == 100
    assert position["pc_discrete_quantity_authority_consumed"] is True
    assert position["legacy_zero_fallback_allowed"] is False
    authority = position["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]
    assert authority["future_information_used"] is False
    assert authority["historical_outcome_used"] is False


def test_phase32_bg_reentry_switched_target_consumed_by_ps() -> None:
    row = _reentry("20020", rank=1, target_weight=0.05)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0))
    position = payload["positions"][0]

    assert position["semantic_buy_type"] == "REENTRY"
    assert position["quantity_delta_candidate"] == 100
    assert position["pc_discrete_quantity_authority_consumed"] is True
    assert position["bg_bf_aggregated_target"]["semantic_type"] == "REENTRY_FIRST_LOT"
    authority = position["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]
    assert authority["future_information_used"] is False
    assert authority["historical_outcome_used"] is False


def test_phase32_bg_add_three_lots_connects_as_net_quantity_delta() -> None:
    row = _add("30030", current_quantity=100, current_weight=0.02, single_name_cap=0.50, rank=1, target_weight=0.02)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=310_000.0, budget=0.31), strategy_cap=0.50)
    position = payload["positions"][0]

    assert position["quantity_delta_candidate"] == 300
    assert position["final_target_quantity"] == 400
    assert position["pc_discrete_quantity_authority_consumed"] is True
    assert position["bg_bf_aggregated_target"]["accepted_lot_count"] == 3
    authority = position["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]
    assert authority["final_allocated_quantity"] == 300
    assert authority["future_information_used"] is False
    assert authority["historical_outcome_used"] is False


def test_phase32_br_add_three_200_share_lots_connect_as_600_share_net_delta() -> None:
    row = _add("94340", current_quantity=700, current_weight=0.10, single_name_cap=0.90, rank=1, target_weight=0.10)
    pc_summary = _pc([row], budget=0.70)
    disabled = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc_summary,
        position_sizing_payload={"positions": [{"security_code": "94340", "trading_unit": 100, "transaction_quantity_candidate": 200}]},
        cash_payload={"available_cash": 700_000.0},
    )
    pc_summary["canonical_marginal_capital_frontier_authority"] = activate_pc_to_ps_production_consumer_switch(disabled)

    payload = _position_sizing_payload([row], pc_summary, strategy_cap=0.90)
    position = payload["positions"][0]

    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "PASS"
    assert position["quantity_delta_candidate"] == 600
    assert position["final_quantity_delta"] == 600
    assert position["final_target_quantity"] == 1300
    assert position["bg_bf_aggregated_target"]["current_quantity"] == 700
    assert position["bg_bf_aggregated_target"]["final_quantity_delta"] == 600
    assert position["bg_bf_aggregated_target"]["final_target_quantity"] == 1300
    assert position["legacy_zero_fallback_allowed"] is False


def test_phase32_bg_cash_no_deployment_zeroes_without_legacy_fallback() -> None:
    row = _new("10010", rank=1, target_weight=0.20)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0, cash_preferred=True))
    position = payload["positions"][0]

    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "PASS"
    assert position["marginal_capital_frontier_switch_sizing_eligibility"] == "NOT_SELECTED_BY_BG_AUTHORITY"
    assert position["target_weight"] == 0.0
    assert position["quantity_delta_candidate"] == 0
    assert position["legacy_zero_fallback_allowed"] is False


def test_phase32_bz_bf_absent_add_target_blocks_residual_buy_add() -> None:
    row = _add(
        "94320",
        current_quantity=1100,
        current_weight=0.173269,
        single_name_cap=0.18,
        rank=1,
        target_weight=0.189167,
    )
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0), strategy_cap=0.18)
    position = payload["positions"][0]

    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "PASS"
    assert payload["marginal_capital_frontier_switch_consumption"]["accepted_boundary_target_count"] == 0
    assert position["marginal_capital_frontier_switch_sizing_eligibility"] == "NOT_SELECTED_BY_BG_AUTHORITY"
    assert position["bg_bf_aggregated_target"] == {}
    assert position["target_weight"] == 0.173269
    assert position["quantity_delta_candidate"] == 0
    assert position["final_quantity_delta"] == 0
    assert "BG_BF_ADD_TARGET_REQUIRED_NO_LEGACY_ADD_FALLBACK" in position["reason_codes"]
    authority = position["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]
    assert authority["status"] == "BLOCK"
    assert authority["discrete_authorized_quantity"] == 0
    assert authority["future_information_used"] is False
    assert authority["historical_outcome_used"] is False
    assert position["legacy_zero_fallback_allowed"] is False


def test_phase32_bg_missing_or_invalid_authority_fails_closed() -> None:
    row = _new("10010", rank=1, target_weight=0.20)
    pc_summary = _pc([row])
    authority = _active_authority([row], cash=1_000_000.0)
    authority["production_consumer_switch"]["status"] = "REVIEW_REQUIRED"
    pc_summary["canonical_marginal_capital_frontier_authority"] = authority

    payload = _position_sizing_payload([row], pc_summary)
    position = payload["positions"][0]

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "REVIEW_REQUIRED"
    assert position["sizing_status"] == "UPSTREAM_REVIEW_REQUIRED"
    assert "BG_PRODUCTION_CONSUMER_SWITCH_NOT_PASS" in payload["reason_codes"]
    assert payload["marginal_capital_frontier_switch_consumption"]["legacy_zero_fallback_used"] is False
    assert position["target_weight"] == 0.0


def test_phase32_bg_legacy_zero_fallback_impossible_and_runtime_lineage_present() -> None:
    row = _new("10010", rank=1, target_weight=0.05)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0))
    position = payload["positions"][0]
    source = position["bg_bf_aggregated_target"]

    assert position["target_weight"] > 0.0
    assert position["quantity_delta_candidate"] == 100
    assert position["legacy_target_gap_fallback_allowed"] is False
    assert position["legacy_zero_fallback_allowed"] is False
    assert source["accepted_frontier_candidate_ids"]
    assert source["source_candidate_ids"]
    assert payload["production_consumer_connected"] is True
    assert payload["legacy_authority_active"] is False


def test_phase32_bg_deterministic_consumer_ownership_and_shadow_count_zero() -> None:
    row = _add("30030", current_quantity=100, current_weight=0.02, single_name_cap=0.50, rank=1, target_weight=0.02)
    first_pc = _active_pc_summary([row], cash=310_000.0, budget=0.31)
    second_pc = _active_pc_summary([row], cash=310_000.0, budget=0.31)
    first = _position_sizing_payload([row], first_pc, strategy_cap=0.50)
    second = _position_sizing_payload([row], second_pc, strategy_cap=0.50)

    assert first_pc["canonical_marginal_capital_frontier_authority"]["production_consumer_count"] == 1
    assert first_pc["canonical_marginal_capital_frontier_authority"]["production_consumer_switch"]["shadow_frontier_production_consumer_count"] == 0
    assert first["marginal_capital_frontier_switch_consumption"]["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert json.dumps(first["positions"], sort_keys=True, default=str) == json.dumps(second["positions"], sort_keys=True, default=str)


def test_phase32_bl_runtime_nested_cash_keeps_budget_notional_units() -> None:
    row = _new("10010", rank=1, target_weight=0.05)
    authority = _active_authority(
        [row],
        budget=0.74,
        cash_payload={
            "status": "PASS",
            "summary": {
                "cash": 1_000_000.0,
                "buying_power": 1_000_000.0,
                "current_cash": 1_000_000.0,
                "portfolio_total_equity": 1_000_000.0,
            },
        },
    )
    budget = authority["allocation_budget_authority"]
    boundary = authority["pc_to_ps_consumer_switch_boundary"]

    assert budget["starting_cash_notional"] == 1_000_000.0
    assert budget["available_incremental_budget_notional"] == 740_000.0
    assert budget["available_incremental_budget_weight"] == 0.74
    assert authority["authority_result"]["accepted_target_count"] > 0
    assert boundary["aggregated_ps_target_count"] > 0

    pc_summary = _pc([row], budget=0.74)
    pc_summary["canonical_marginal_capital_frontier_authority"] = authority
    payload = _position_sizing_payload([row], pc_summary)
    position = payload["positions"][0]

    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "PASS"
    assert payload["marginal_capital_frontier_switch_consumption"]["accepted_boundary_target_count"] > 0
    assert position["quantity_delta_candidate"] == 100
    assert position["final_quantity_delta"] == 100
    assert payload["marginal_capital_frontier_switch_consumption"]["legacy_zero_fallback_used"] is False


def test_phase32_bl_available_incremental_budget_weight_not_cash_fallback() -> None:
    row = _new("10010", rank=1, target_weight=0.05)
    disabled = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], budget=0.74),
        cash_payload={},
    )

    assert disabled["cash_source_status"] == "REVIEW_REQUIRED"
    assert "REVIEW_REQUIRED" in disabled["review_reasons"]
    assert disabled["authority_result"]["status"] == "REVIEW_REQUIRED"
    assert disabled["authority_result"]["accepted_target_count"] == 0
    assert disabled["allocation_budget_authority"]["source_observations"][0]["budget_notional"] == 740_000.0
    assert disabled["allocation_budget_authority"]["starting_cash_notional"] == 0.0


def test_phase32_bo_bg_bf_quantity_authority_passes_planning_submit_feasibility() -> None:
    row = _new("10010", rank=1, target_weight=0.05)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0))
    position = payload["positions"][0]

    result = _submit_feasibility_for_position(position)

    assert result["status"] == "PASS"
    assert result["reason"] == "planning_submit_feasibility_pass"
    assert result["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert result["canonical_discrete_quantity_submit_authority"]["reason"] != "pc_discrete_quantity_authority_future_information_flag_invalid"
    assert position["legacy_zero_fallback_allowed"] is False


def test_phase32_bo_add_multi_lot_quantity_authority_passes_submit_feasibility() -> None:
    row = _add("30030", current_quantity=100, current_weight=0.02, single_name_cap=0.50, rank=1, target_weight=0.02)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=310_000.0, budget=0.31), strategy_cap=0.50)
    position = payload["positions"][0]

    result = _submit_feasibility_for_position(position)

    assert position["final_quantity_delta"] == 300
    assert result["status"] == "PASS"
    assert result["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert result["canonical_discrete_quantity_submit_authority"]["quantity_scope"] == "ORDER_INCREMENT"


def test_phase32_bo_future_information_injection_still_fails_closed() -> None:
    row = _new("10010", rank=1, target_weight=0.05)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=1_000_000.0))
    position = dict(payload["positions"][0])
    lot_resolution = dict(position["phase29_l19_lot_resolution"])
    authority = dict(lot_resolution["pc_positive_executable_quantity_authority"])
    authority["future_information_used"] = True
    lot_resolution["pc_positive_executable_quantity_authority"] = authority
    position["phase29_l19_lot_resolution"] = lot_resolution

    result = _submit_feasibility_for_position(position)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["violated_policy"] == "position_sizing"
    assert result["canonical_discrete_quantity_submit_authority"]["reason"] == "pc_discrete_quantity_authority_future_information_flag_invalid"


def test_phase32_cc_new_multilot_net_quantity_consumed_by_ps() -> None:
    row = _new("77770", rank=1, target_weight=0.04)
    row["reference_price"] = 100.0
    row["reference_price_resolution"] = {"status": "PASS", "resolved_price": 100.0}
    row["phase29_l19_lot_resolution"] = _entry_lot_resolution(400)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=50_000.0, budget=0.05))
    position = payload["positions"][0]

    assert payload["marginal_capital_frontier_switch_consumption"]["status"] == "PASS"
    assert position["quantity_delta_candidate"] == 400
    assert position["final_quantity_delta"] == 400
    assert position["final_target_quantity"] == 400
    assert position["bg_bf_aggregated_target"]["accepted_lot_count"] == 4
    assert position["bg_bf_aggregated_target"]["accepted_increment_indexes"] == [1, 2, 3, 4]
    assert position["legacy_zero_fallback_allowed"] is False


def test_phase32_cc_reentry_multilot_net_quantity_consumed_by_ps() -> None:
    row = _reentry("88880", rank=1, target_weight=0.03)
    row["reference_price"] = 100.0
    row["reference_price_resolution"] = {"status": "PASS", "resolved_price": 100.0}
    row["phase29_l19_lot_resolution"] = _entry_lot_resolution(300)
    payload = _position_sizing_payload([row], _active_pc_summary([row], cash=40_000.0, budget=0.04))
    position = payload["positions"][0]

    assert position["semantic_buy_type"] == "REENTRY"
    assert position["quantity_delta_candidate"] == 300
    assert position["final_quantity_delta"] == 300
    assert position["bg_bf_aggregated_target"]["semantic_type"] == "REENTRY_FIRST_LOT"
    assert position["bg_bf_aggregated_target"]["accepted_lot_count"] == 3
    assert position["pc_discrete_quantity_authority_consumed"] is True


def _active_pc_summary(rows: list[dict[str, Any]], *, cash: float, budget: float = 1.0, cash_preferred: bool = False) -> dict[str, Any]:
    payload = _pc(rows, budget=budget)
    payload["canonical_marginal_capital_frontier_authority"] = _active_authority(rows, cash=cash, budget=budget, cash_preferred=cash_preferred)
    return payload


def _active_authority(
    rows: list[dict[str, Any]],
    *,
    cash: float | None = None,
    budget: float = 1.0,
    cash_preferred: bool = False,
    cash_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if cash_payload is None:
        cash_payload = {"available_cash": cash if cash is not None else 0.0, "cash_preferred": cash_preferred}
    disabled = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(rows, budget=budget),
        cash_payload=cash_payload,
    )
    return activate_pc_to_ps_production_consumer_switch(disabled)


def _position_sizing_payload(rows: list[dict[str, Any]], pc_summary: Mapping[str, Any], *, strategy_cap: float = 0.30) -> dict[str, Any]:
    payload, _ = build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=_summary("pc", rows=rows, summary=dict(pc_summary)),
        capital_deployment_summary=_summary("cd"),
        dynamic_position_count_summary=_summary("dpc", summary={"target_position_count": 10}),
        dynamic_cash_exposure_summary=_summary("dce", summary={"target_gross_exposure_ratio": 1.0}),
        position_management_summary=_summary("pm"),
        opportunity_summary=_summary("opp"),
        current_position_summary=_summary("cur", summary={"portfolio_value": 1_000_000.0, "portfolio_total_equity": 1_000_000.0}),
        price_volatility_summary=_summary("pv"),
        safety_limit_summary=_summary("safety", summary={"maximum_position_weight": strategy_cap}),
        config=_config(strategy_cap=strategy_cap),
        production_consumer_connected=True,
    )
    return payload


def _submit_feasibility_for_position(position: Mapping[str, Any]) -> dict[str, Any]:
    quantity = float(position["final_quantity_delta"])
    reference_price = float(position["reference_price"])
    item = SimpleNamespace(
        pending_item_id=f"pending-{position['security_code']}",
        symbol=str(position["security_code"]),
        side="BUY",
        quantity=quantity,
        estimated_amount=quantity * reference_price,
        estimated_price=reference_price,
        reservation_price=reference_price,
        reserved_notional=quantity * reference_price,
        reservation_price_authority={},
        reservation_reason="test_reservation",
        quantity_contract={"position_sizing_authority": {"positions": [dict(position)]}},
    )
    current = RuntimeCurrentExposure(
        cash=1_000_000.0,
        buying_power=1_000_000.0,
        current_exposure=0.0,
        current_total_equity=1_000_000.0,
        active_deployment_capital=1_000_000.0,
        selected_capital_source="test_current_total_equity",
        capital_fallback_used=False,
        initial_or_bootstrap_capital=None,
        positions={},
        position_market_values={},
        current_position_source="",
    )
    cash_exposure = CashExposureAuthority(
        status="PASS",
        reason="test_cash_exposure_authority",
        strategy_requested_cash_ratio=None,
        selected_dynamic_cash_ratio=0.0,
        strategy_requested_exposure_ratio=None,
        selected_dynamic_exposure_ratio=1.0,
        current_total_equity=1_000_000.0,
        active_deployment_capital=1_000_000.0,
        current_cash=1_000_000.0,
        current_market_value=0.0,
        target_exposure_amount=1_000_000.0,
        selected_runtime_exposure_limit=1_000_000.0,
        safety_exposure_limit=None,
        target_cash_amount=0.0,
        available_cash_after_target=1_000_000.0,
        remaining_exposure_capacity=1_000_000.0,
        planning_budget=1_000_000.0,
        cash_exposure_authority_winner="test",
        cash_exposure_binding_constraint="NONE",
        legacy_cash_config_used=False,
        legacy_exposure_config_used=False,
        cash_exposure_fallback_used=False,
        runtime_mode="",
        business_date=BUSINESS_DATE,
        producer="test",
        consumer="test",
        runtime_path="",
        authority_source="test",
        authority_hash="sha256:test",
    )
    position_count = PositionCountAuthority(
        status="PASS",
        reason="test_position_count_authority",
        strategy_requested_position_count=None,
        selected_dynamic_position_count=20,
        current_position_count=0,
        available_position_slots=20,
        effective_order_limit=20,
        safety_hard_maximum=20,
        position_count_authority_winner="test",
        position_count_binding_constraint="NONE",
        legacy_position_count_config_used=False,
        position_count_fallback_used=False,
        runtime_mode="",
        business_date=BUSINESS_DATE,
        producer="test",
        consumer="test",
        runtime_path="",
        authority_source="test",
        authority_hash="sha256:test",
        configured_legacy_max_positions=5,
    )
    return evaluate_buy_item_submit_feasibility(
        item=item,
        policy=load_capital_deployment_policy("configs/runtime_v2/capital_deployment.json"),
        current=current,
        authority_source="phase32_bo_test",
        business_date=BUSINESS_DATE,
        runtime_mode="",
        cash_exposure_authority=cash_exposure,
        position_count_authority=position_count,
    )


def _summary(
    name: str,
    *,
    rows: list[dict[str, Any]] | None = None,
    summary: Mapping[str, Any] | None = None,
) -> PositionSizingSourceSummary:
    return PositionSizingSourceSummary("PASS", BUSINESS_DATE, BUSINESS_DATE, f"/tmp/{name}.json", "sha256:test", tuple(rows or ()), summary or {})


def _config(*, strategy_cap: float) -> PositionSizingConfig:
    base = load_position_sizing_config("configs/strategy/position_sizing.json")
    return PositionSizingConfig(
        config_version=base.config_version,
        config_source=base.config_source,
        sizing_method=base.sizing_method,
        opportunity_adjustment=base.opportunity_adjustment,
        volatility_adjustment=base.volatility_adjustment,
        pm_intent_adjustment=base.pm_intent_adjustment,
        minimum_meaningful_notional=base.minimum_meaningful_notional,
        strategy_maximum_position_weight=strategy_cap,
        safety_concentration_reference=base.safety_concentration_reference,
    )


def _pc(rows: list[dict[str, Any]], *, budget: float = 1.0) -> dict[str, Any]:
    return {
        "schema_version": "portfolio_construction.v1",
        "business_date": BUSINESS_DATE,
        "portfolio_value": 1_000_000.0,
        "portfolio_members": rows,
        "available_incremental_budget": budget,
        "incremental_budget_reconciliation": {"available_incremental_budget": budget},
        "capital_competition": {
            "canonical_multi_allocation_deployment_set": {
                "available_incremental_budget": budget,
                "budget_envelope": {"schema_version": "incremental_capital_budget_envelope.v1", "authority_status": "AUTHORITATIVE"},
            }
        },
    }


def _new(symbol: str, *, rank: int = 1, target_weight: float = 0.05) -> dict[str, Any]:
    return {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "semantic_buy_type": "BUY_NEW",
        "candidate_id": f"candidate-{symbol}",
        "runtime_opportunity_score": 0.9,
        "input_opportunity_rank": rank,
        "allocation_quality_score": 0.8,
        "quality_score": 0.8,
        "quality_decision_id": f"quality-{symbol}",
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_status": "PASS",
        "buy_quality_authority": {
            "quality_decision_id": f"quality-{symbol}",
            "quality_action": "FULL_ALLOCATION_ELIGIBLE",
            "quality_score": 0.8,
        },
        "quality_allocation_adjustment": 1.0,
        "entry_admission_action": "FULL_ALLOCATION_ELIGIBLE",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "target_weight": target_weight,
        "single_name_cap": 0.30,
        "reference_price": 1_000.0,
        "reference_price_authority": {"authority_type": "REFERENCE_PRICE_AUTHORITY", "PIT_status": "PASS", "source_field": "reference_price"},
        "reference_price_resolution": {"status": "PASS", "resolved_price": 1_000.0},
        "trading_unit": 100,
        "volatility": 0.03,
    }


def _reentry(symbol: str, *, rank: int = 1, target_weight: float = 0.05) -> dict[str, Any]:
    row = _new(symbol, rank=rank, target_weight=target_weight)
    row.update(
        {
            "semantic_buy_type": "REENTRY",
            "reentry_recovery_status": "PASS",
            "previous_exit_reason_class": "TREND_AND_OPPORTUNITY_BROKEN",
        }
    )
    return row


def _entry_lot_resolution(quantity: int) -> dict[str, Any]:
    return {
        "status": "PASS",
        "executable_quantity_delta": quantity,
        "pc_positive_executable_quantity_authority": {
            "status": "PASS",
            "final_allocated_quantity": quantity,
            "discrete_authorized_quantity": quantity,
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }


def _add(
    symbol: str,
    *,
    current_quantity: int,
    current_weight: float,
    single_name_cap: float,
    rank: int,
    target_weight: float,
) -> dict[str, Any]:
    row = _new(symbol, rank=rank, target_weight=target_weight)
    row.update(
        {
            "current_position": True,
            "membership_intent": "RETAIN",
            "pm_action": "ADD",
            "semantic_buy_type": "BUY_ADD",
            "position_campaign_id": f"pc-{symbol}-0001",
            "pm_decision_id": f"pm-{symbol}",
            "current_quantity": current_quantity,
            "current_weight": current_weight,
            "single_name_cap": single_name_cap,
            "expected_edge_improvement_state": "IMPROVING",
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
            "add_allocation_eligibility_status": "PASS",
            "same_campaign_continuation_status": "CONTINUING",
            "no_loss_averaging_status": "PASS",
        }
    )
    return row
