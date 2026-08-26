from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import (
    _canonical_marginal_capital_pending_order,
    _cash_feasible_buy_batch,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import RuntimeCurrentExposure
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy, ManualReviewThreshold
from ai_fund_lab_v2.strategy.portfolio_construction import apply_lot_aware_final_reallocation
from ai_fund_lab_v2.strategy.runtime_planning import _sort_plans_by_canonical_marginal_priority


BUSINESS_DATE = "2022-08-19"


def test_phase31_b10_pc_strong_add_outranks_comparable_new_without_add_label_priority() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_add("94320"), _new("27780", input_opportunity_rank=40)],
        lot_feasibility_rows=[_lot("94320"), _lot("27780")],
        target_gross_exposure=0.08,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
    )
    by_symbol = {row["security_code"]: row for row in result["members"]}

    assert by_symbol["94320"]["canonical_marginal_capital_priority_index"] == 1
    assert by_symbol["94320"]["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
    assert by_symbol["94320"]["lot_aware_accepted_incremental_weight"] == 0.04
    assert by_symbol["27780"]["lot_aware_accepted_buy_new_weight"] == 0.0
    authority = result["evidence"]["marginal_capital_value_authority"]
    assert authority["buy_add_unconditional_priority"] is False
    assert authority["buy_new_unconditional_priority"] is False
    assert authority["legacy_priority_fallback_active"] is False


def test_phase31_b10_strong_new_outranks_weak_add_with_limited_cash() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _add("94320", expected_edge_improvement_state="WEAKENING"),
            _new("60980", entry_admission_action="FULL_ALLOCATION_ELIGIBLE", input_opportunity_rank=1),
        ],
        lot_feasibility_rows=[_lot("94320"), _lot("60980")],
        target_gross_exposure=0.08,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
    )
    by_symbol = {row["security_code"]: row for row in result["members"]}

    assert by_symbol["60980"]["canonical_marginal_capital_priority_index"] == 1
    assert by_symbol["60980"]["lot_aware_accepted_buy_new_weight"] == 0.04
    assert by_symbol["94320"]["marginal_capital_value_class"] == "BLOCKED_OR_NOT_ELIGIBLE"
    assert by_symbol["94320"]["lot_aware_accepted_incremental_weight"] == 0.0


def test_phase31_b10_equal_priority_preserves_stable_order() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _new("11110", input_opportunity_rank=3, construction_priority=1),
            _new("22220", input_opportunity_rank=3, construction_priority=2),
        ],
        lot_feasibility_rows=[_lot("11110"), _lot("22220")],
        target_gross_exposure=0.08,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
    )
    order = result["evidence"]["marginal_capital_value_authority"]["canonical_order"]

    assert [row["symbol"] for row in order] == ["11110", "22220"]


def test_phase31_b10_runtime_planning_preserves_pc_buy_priority_without_reranking_sell() -> None:
    plans = _sort_plans_by_canonical_marginal_priority(
        [
            {"security_code": "27780", "planning_intent": "BUY_NEW", "order_side_intent": "BUY", "canonical_marginal_capital_priority_index": 3},
            {"security_code": "23230", "planning_intent": "SELL_EXIT", "order_side_intent": "SELL"},
            {"security_code": "94320", "planning_intent": "BUY_ADD", "order_side_intent": "BUY", "canonical_marginal_capital_priority_index": 1},
        ]
    )

    assert [row["security_code"] for row in plans] == ["94320", "27780", "23230"]
    assert plans[0]["canonical_strategy_order_source"] == "MARGINAL_CAPITAL_VALUE_AUTHORITY"
    assert plans[2]["canonical_strategy_order_source"] == "STABLE_NON_BUY_OR_NO_PRIORITY_ORDER"


def test_phase31_b10_b0_2022_08_19_94320_reserved_cash_order_regression() -> None:
    items = _canonical_marginal_capital_pending_order(
        (
            _buy("27780", 33100, priority=10, intent="BUY_NEW"),
            _buy("60540", 44200, priority=4, intent="BUY_NEW"),
            _buy("70140", 85700, priority=2, intent="BUY_NEW"),
            _buy("94320", 59850, priority=1, intent="BUY_ADD"),
        )
    )
    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=187950),
        policy=_policy(),
        business_date="2022-08-19",
        mode="historical",
    )

    assert evidence["items"][0]["symbol"] == "94320"
    assert evidence["items"][0]["decision"] == "INCLUDE"
    assert evidence["items"][0]["canonical_marginal_capital_priority_index"] == 1
    assert "94320" in [item.symbol for item in active]


def test_phase31_b10_b0_2022_08_24_94320_reserved_cash_order_regression() -> None:
    items = _canonical_marginal_capital_pending_order(
        (
            _buy("43760", 55700, priority=6, intent="BUY_NEW"),
            _buy("94320", 60510, priority=1, intent="BUY_ADD"),
        )
    )
    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=68900),
        policy=_policy(),
        business_date="2022-08-24",
        mode="historical",
    )

    assert [row["symbol"] for row in evidence["items"]] == ["94320", "43760"]
    assert evidence["items"][0]["decision"] == "INCLUDE"
    assert evidence["items"][1]["decision"] == "PRUNE"
    assert [item.symbol for item in active] == ["94320"]


def test_phase31_b10_buy_prune_does_not_block_valid_sell() -> None:
    items = _canonical_marginal_capital_pending_order(
        (
            _buy("94320", 120000, priority=1, intent="BUY_ADD"),
            _sell("23230"),
        )
    )
    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=50000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert evidence["items"][0]["symbol"] == "94320"
    assert evidence["items"][0]["decision"] == "PRUNE"
    assert [item.symbol for item in active] == ["23230"]


def _new(symbol: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "target_weight": 0.04,
        "accepted_buy_new_weight": 0.04,
        "runtime_opportunity_score": 0.5,
        "input_opportunity_rank": 10,
        "construction_priority": 10,
    }
    row.update(overrides)
    return row


def _add(symbol: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": True,
        "pm_action": "ADD",
        "current_weight": 0.04,
        "target_weight": 0.08,
        "accepted_incremental_weight": 0.04,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "input_opportunity_rank": 1,
        "construction_priority": 20,
        "add_investment_evidence": {
            "business_date": BUSINESS_DATE,
            "position_campaign_id": f"campaign-{symbol}",
            "campaign_continuation": {"status": "PASS", "state": "PASS", "authority": "same_campaign_identity_match"},
            "expected_edge": {"status": "PASS", "state": "IMPROVING", "baseline_business_date": "2022-08-18"},
            "incremental_value": {"status": "PASS", "state": "POSITIVE"},
            "opportunity_cost": {"status": "PASS", "state": "PASS"},
            "temporal_authority": {"point_in_time": True, "future_evidence_used": False},
        },
    }
    row.update(overrides)
    return row


def _lot(symbol: str) -> dict:
    return {
        "security_code": symbol,
        "lot_feasible": True,
        "broker_eligible": True,
        "minimum_executable_weight": 0.04,
        "lot_first_feasibility_classification": "PASS",
        "phase29_l19_lot_resolution": {
            "one_lot_feasibility_status": "PASS",
            "final_allocated_quantity": 100,
            "executable_quantity_delta": 100,
            "safety_hard_cap_preserved": True,
        },
    }


def _buy(symbol: str, reserved_notional: float, *, priority: int, intent: str) -> PendingOrderItem:
    quantity = 100.0
    price = reserved_notional / quantity
    return PendingOrderItem(
        pending_item_id=f"buy-{symbol}",
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=price,
        estimated_amount=reserved_notional,
        approved=False,
        state="CREATED",
        reference_price=price,
        reservation_price=price,
        reservation_price_type="test",
        reservation_price_authority={"authority_status": "PASS"},
        reservation_reason="test",
        reserved_notional=reserved_notional,
        quantity_contract={
            "selected_notional": reserved_notional,
            "selected_quantity": quantity,
            "planned_quantity": quantity,
            "planning_intent": intent,
            "position_count_authority": {"selected_dynamic_position_count": 10, "safety_hard_maximum": 10},
            "cash_exposure_authority": {
                "selected_dynamic_cash_ratio": 0.0,
                "selected_dynamic_exposure_ratio": 1.0,
                "maximum_gross_exposure_ratio": 1.0,
            },
            "position_sizing_authority": {
                "schema_version": "position_sizing.v1",
                "business_date": BUSINESS_DATE,
                "positions": [
                    {
                        "security_code": symbol,
                        "target_notional": reserved_notional,
                        "incremental_buy_notional": reserved_notional,
                        "selected_position_amount": reserved_notional,
                        "remaining_add_capacity": reserved_notional,
                        "target_weight": 0.10,
                        "selected_position_weight": 0.10,
                        "maximum_position_weight": 0.25,
                        "quantity_delta_candidate": quantity,
                        "target_quantity_candidate": quantity,
                        "quantity_status": "RESOLVED_EXECUTABLE",
                        "phase29_l19_lot_resolution": {},
                    }
                ],
            },
        },
        source_decision_type=intent,
        source_position_symbol=symbol,
        canonical_marginal_capital_priority_index=priority,
        marginal_capital_value_class="ELIGIBLE_STRONG" if priority == 1 else "ELIGIBLE_COMPARABLE",
        marginal_capital_value_authority={
            "authority_type": "MARGINAL_CAPITAL_VALUE_AUTHORITY",
            "canonical_marginal_capital_priority_index": priority,
            "future_information_used": False,
        },
    )


def _sell(symbol: str) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=f"sell-{symbol}",
        symbol=symbol,
        side="SELL",
        quantity=100.0,
        order_type="MARKET",
        estimated_price=100.0,
        estimated_amount=10000.0,
        approved=False,
        state="CREATED",
        source_decision_type="SELL_EXIT",
        source_position_symbol=symbol,
    )


def _current(*, cash: float) -> RuntimeCurrentExposure:
    return RuntimeCurrentExposure(
        cash=cash,
        buying_power=cash,
        current_exposure=0.0,
        current_total_equity=cash,
        active_deployment_capital=cash,
        selected_capital_source="test_current_total_equity",
        capital_fallback_used=False,
        initial_or_bootstrap_capital=cash,
        positions={},
        position_market_values={},
        current_position_source="test_current",
    )


def _policy() -> CapitalDeploymentPolicy:
    return CapitalDeploymentPolicy(
        policy_version="capital_deployment_v1",
        policy_source="phase31_b10_test_policy",
        evaluation_capital=1_000_000,
        max_positions=10,
        min_order_amount=0.0,
        max_buy_order_amount=None,
        max_sell_liquidation_amount=None,
        buy_notional_policy="derived_from_capital_allocation_and_constraints",
        sell_liquidation_policy="current_owned_available_quantity_policy",
        manual_review_threshold=ManualReviewThreshold(buy_amount=None, sell_liquidation_amount=None),
        loaded_from="phase31_b10_test_policy",
    )
