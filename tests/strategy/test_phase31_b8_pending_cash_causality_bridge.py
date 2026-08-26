from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.marginal_capital_value_shadow import build_marginal_capital_value_shadow_payload


TARGET_RUN = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z")


def test_phase31_b8_pending_reserved_cash_chain_is_bridged_from_canonical_authority() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={"portfolio_members": [_add("94320"), _new("27780", input_opportunity_rank=40)]},
        position_sizing_payload={
            "positions": [
                {"security_code": "94320", "transaction_quantity_candidate": 300},
                {"security_code": "27780", "transaction_quantity_candidate": 100},
            ]
        },
        runtime_planning_payload={
            "plans": [
                {"security_code": "27780", "planning_intent": "BUY_NEW", "planned_quantity": 100, "reference_price": 331},
                {"security_code": "94320", "planning_intent": "BUY_ADD", "planned_quantity": 300, "reference_price": 199.5},
            ]
        },
        strategy_planning_authority_payload={
            "lineage": {
                "cash_feasible_buy_batch": {
                    "status": "PASS",
                    "starting_cash": 40000,
                    "starting_buying_power": 40000,
                    "final_reserved_notional_total": 33100,
                    "remaining_reserved_cash": 6900,
                    "items": [
                        _cash_item("27780", 1, "INCLUDE", 33100, 0, 40000, 6900, "planning_submit_feasibility_pass"),
                        _cash_item("94320", 2, "PRUNE", 59850, 33100, 6900, 6900, "DEFERRED_INSUFFICIENT_RESERVED_CASH"),
                    ],
                }
            }
        },
    )

    add = _by_symbol(payload, "94320")
    causality = add["pending_cash_causality"]
    assert causality["pre_batch_cash"] == 40000
    assert causality["required_reserved_notional"] == 59850
    assert causality["cumulative_reserved_before_item"] == 33100
    assert causality["remaining_cash_before_item"] == 6900
    assert causality["remaining_cash_after_item"] == 6900
    assert causality["final_pending_state"] == "PRUNE"
    assert causality["final_cash_feasibility_result"] == "FAIL"
    assert causality["typed_guard_code"] == "DEFERRED_INSUFFICIENT_RESERVED_CASH"
    assert causality["cash_causality_classification"] == "CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM"
    assert causality["starving_prior_items"][0]["symbol"] == "27780"
    assert payload["actual_trading_path_mutated"] is False


def test_phase31_b8_b0_real_94320_full_causality_is_reconstructed() -> None:
    expectations = {
        "2022-08-19": (187950.0, 59850.0, 163000.0, 24950.0, 24950.0, 6),
        "2022-08-24": (68900.0, 60510.0, 55700.0, 13200.0, 13200.0, 3),
    }

    for business_date, expected in expectations.items():
        payload = _real_payload(business_date)
        add = _by_symbol(payload, "94320")
        causality = add["pending_cash_causality"]

        assert (
            causality["pre_batch_cash"],
            causality["required_reserved_notional"],
            causality["cumulative_reserved_before_item"],
            causality["remaining_cash_before_item"],
            causality["remaining_cash_after_item"],
            causality["actual_pending_order"],
        ) == expected
        assert add["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
        assert causality["final_pending_state"] == "PRUNE"
        assert causality["final_cash_reason_code"] == "DEFERRED_INSUFFICIENT_RESERVED_CASH"
        assert causality["cash_causality_classification"] == "CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM"
        assert payload["pending_cash_authority"]["producer"] == "runtime_v2.planning.strategy_authority._cash_feasible_buy_batch"
        assert payload["pending_cash_authority"]["reserved_notional_source"] == "runtime_v2.order_reservation.resolve_order_cash_reservation"
        assert payload["future_information_used"] is False


def test_phase31_b8_order_inversion_without_cash_prune_is_not_starvation() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={"portfolio_members": [_add("94320"), _new("27780", input_opportunity_rank=40)]},
        runtime_planning_payload={
            "plans": [
                {"security_code": "27780", "planning_intent": "BUY_NEW", "planned_quantity": 100, "reference_price": 331},
                {"security_code": "94320", "planning_intent": "BUY_ADD", "planned_quantity": 300, "reference_price": 199.5},
            ]
        },
        strategy_planning_authority_payload={
            "lineage": {
                "cash_feasible_buy_batch": {
                    "status": "PASS",
                    "starting_cash": 100000,
                    "items": [
                        _cash_item("27780", 1, "INCLUDE", 33100, 0, 100000, 66900, "planning_submit_feasibility_pass"),
                        _cash_item("94320", 2, "INCLUDE", 59850, 33100, 66900, 7050, "planning_submit_feasibility_pass"),
                    ],
                }
            }
        },
    )

    add = _by_symbol(payload, "94320")
    assert add["actual_pending_order"] == 2
    assert add["shadow_priority"] == 1
    assert add["pending_cash_causality"]["cash_causality_classification"] == "NO_ACTUAL_STARVATION"
    assert payload["metrics"]["order_inversion_without_cash_effect_count"] == 2


def test_phase31_b8_missing_canonical_cash_evidence_is_explicit_unknown() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={"portfolio_members": [_new("27780")]},
    )

    unit = payload["candidate_units"][0]
    assert payload["pending_cash_authority"]["status"] == "NOT_AVAILABLE"
    assert unit["pending_cash_causality"]["status"] == "NOT_AVAILABLE"
    assert unit["actual_pending_order"] is None


def _real_payload(business_date: str) -> dict:
    day = TARGET_RUN / "daily" / business_date
    return build_marginal_capital_value_shadow_payload(
        business_date=business_date,
        portfolio_construction_payload=json.loads((day / "strategy" / "portfolio_construction.json").read_text(encoding="utf-8")),
        position_sizing_payload=json.loads((day / "strategy" / "position_sizing.json").read_text(encoding="utf-8")),
        runtime_planning_payload=json.loads((day / "strategy" / "runtime_planning.json").read_text(encoding="utf-8")),
        pending_payload=json.loads((day / "morning" / "pending_generation_evidence.json").read_text(encoding="utf-8")),
        strategy_planning_authority_payload=json.loads(
            (day / "morning" / "strategy_planning_authority_evidence.json").read_text(encoding="utf-8")
        ),
    )


def _by_symbol(payload: dict, symbol: str) -> dict:
    return next(row for row in payload["candidate_units"] if row["symbol"] == symbol)


def _cash_item(
    symbol: str,
    order: int,
    decision: str,
    reserved_notional: float,
    reserved_before: float,
    remaining_before: float,
    remaining_after: float,
    reason: str,
) -> dict:
    return {
        "symbol": symbol,
        "canonical_priority_index": order,
        "decision": decision,
        "reserved_notional": reserved_notional,
        "reserved_cash_before_item": reserved_before,
        "remaining_cash_before_item": remaining_before,
        "reserved_cash_after_item": remaining_after,
        "reason": reason,
    }


def _new(symbol: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "target_weight": 0.04,
        "accepted_buy_new_weight": 0.04,
        "runtime_opportunity_score": 0.5,
        "input_opportunity_rank": 1,
    }
    row.update(overrides)
    return row


def _add(symbol: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "current_position": True,
        "pm_action": "ADD",
        "target_weight": 0.08,
        "current_weight": 0.04,
        "accepted_incremental_weight": 0.04,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "input_opportunity_rank": 1,
    }
    row.update(overrides)
    return row
