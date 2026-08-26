from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-08-27"
TARGET_RUN = "runtime-test-historical-extended-smoke-20260825T072702567342Z"


def test_phase31_g113_actual_76470_add_shadow_is_lot_level_and_non_authoritative() -> None:
    competition = _competition_from_run(TARGET_RUN, "2022-12-06")
    shadow = competition["canonical_add_marginal_capital_competition"]
    rows = [row for row in shadow["increment_rows"] if row["symbol"] == "76470"]

    assert shadow["schema_version"] == "canonical_add_marginal_capital_competition.v1"
    assert shadow["authority"] == "SHADOW"
    assert shadow["authoritative_allocation_changed"] is False
    assert shadow["feeds_position_sizing"] is False
    assert shadow["feeds_runtime_planning"] is False
    assert shadow["feeds_submit"] is False
    assert shadow["feeds_execution"] is False
    assert shadow["add_vs_new_buy_final_frontier_complete"] is True
    assert shadow["cash_first_class_in_marginal_frontier"] is True
    assert shadow["residual_cash_allowed"] is True
    assert rows
    assert rows[0]["pre_increment_quantity"] == 400
    assert rows[0]["post_increment_quantity"] == 500
    assert rows[1]["pre_increment_quantity"] == rows[0]["post_increment_quantity"]
    assert all(row["hypothetical_only"] is True for row in rows)
    assert all(row["portfolio_state_mutated"] is False for row in rows)
    assert all(row["cash_preferred_participation_valid_is_add_beats_cash"] is False for row in rows)
    assert shadow["future_information_used"] is False
    assert shadow["historical_outcome_used"] is False


def test_phase31_g113_add_vs_add_and_cash_frontier_are_first_class() -> None:
    competition = _competition(
        [
            _add("20010", requested_weight=0.04, current_quantity=400, current_weight=0.04, priority=2),
            _add("10010", requested_weight=0.03, current_quantity=200, current_weight=0.02, priority=1),
            _new("30010", weight=0.05, priority=3),
        ],
        available_budget=0.20,
    )

    shadow = competition["canonical_add_marginal_capital_competition"]
    symbols = {row["symbol"] for row in shadow["increment_rows"]}

    assert shadow["add_vs_add_frontier_complete"] is True
    assert shadow["add_vs_new_buy_final_frontier_complete"] is True
    assert shadow["competitor_frontier"]["add_count"] == 2
    assert shadow["competitor_frontier"]["new_buy_count"] == 1
    assert shadow["competitor_frontier"]["cash_count"] == 1
    assert shadow["competitor_frontier"]["residual_optionality_count"] == 1
    assert symbols == {"10010", "20010"}
    assert shadow["shadow_increment_count"] >= 2
    assert shadow["cash_frontier"]["competitor_type"] == "CASH"
    assert shadow["residual_optionality"]["residual_cash_allowed"] is True


def test_phase31_g113_terminal_and_lot_infeasible_rows_do_not_resurrect() -> None:
    competition = _competition(
        [
            _add("10010", requested_weight=0.0005, current_quantity=100, current_weight=0.02, priority=1),
            _add("20010", requested_weight=0.20, current_quantity=900, current_weight=0.095, priority=2, cap=0.10),
        ],
        available_budget=0.20,
    )

    shadow = competition["canonical_add_marginal_capital_competition"]
    by_symbol = {row["symbol"]: row for row in shadow["increment_rows"]}

    assert by_symbol["10010"]["classification"] == "LOT_INFEASIBLE"
    assert by_symbol["20010"]["classification"] == "SAFETY_TERMINAL"
    assert shadow["safety_terminal_resurrection_count"] == 0
    assert shadow["cap_infeasible_resurrection_count"] == 0
    assert shadow["lot_infeasible_resurrection_count"] == 0


def test_phase31_g113_shadow_is_deterministic_without_symbol_order_privilege() -> None:
    members = [
        _add("20010", requested_weight=0.04, current_quantity=400, current_weight=0.04, priority=2),
        _add("10010", requested_weight=0.03, current_quantity=200, current_weight=0.02, priority=1),
        _new("30010", weight=0.05, priority=3),
    ]
    first = _competition(members, available_budget=0.20)["canonical_add_marginal_capital_competition"]
    second = _competition(list(reversed(members)), available_budget=0.20)["canonical_add_marginal_capital_competition"]

    assert first["add_marginal_competition_hash"] == second["add_marginal_competition_hash"]
    assert first["symbol_order_privilege"] is False
    assert [row["increment_id"] for row in first["increment_rows"]] == [
        row["increment_id"] for row in second["increment_rows"]
    ]


def _competition_from_run(run_id: str, business_date: str) -> dict[str, object]:
    strategy_dir = Path("reports/runtime_tests/runs") / run_id / "daily" / business_date / "strategy"
    pc = json.loads((strategy_dir / "portfolio_construction.json").read_text())
    risk_pacing_evidence = (pc.get("portfolio_policy_allocation_authority") or {}).get("risk_pacing_evidence") or {}
    multi = pc["capital_competition"]["canonical_multi_allocation_deployment_set"]
    return build_capital_competition_framework(
        members=pc["portfolio_members"],
        target_gross_exposure=pc.get("target_gross_exposure"),
        total_target_weight=pc.get("total_target_weight")
        or sum(float(row.get("target_weight") or 0.0) for row in pc["portfolio_members"]),
        business_date=business_date,
        incremental_budget_evidence={"available_incremental_budget": multi.get("available_incremental_budget")},
        lot_reallocation_evidence=pc.get("lot_aware_final_reallocation") or {},
        risk_pacing_evidence=risk_pacing_evidence,
    )


def _competition(members: list[dict[str, object]], *, available_budget: float) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.50,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(),
    )


def _risk() -> dict[str, object]:
    return {
        "risk_pacing_intent": "CAUTIOUS_DEPLOYMENT",
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": "SHORT_TERM_BREADTH_BREAKDOWN",
            "market_quality_evidence_completeness": "COMPLETE",
            "future_information_used": False,
            "historical_outcome_used": False,
        },
        "incremental_capital_budget_envelope": {
            "schema_version": "incremental_capital_budget_envelope.v1",
            "owner": "PORTFOLIO_POLICY",
            "authority_status": "AUTHORITATIVE",
            "business_date": BUSINESS_DATE,
            "market_quality_as_of": BUSINESS_DATE,
            "risk_pacing_as_of": BUSINESS_DATE,
            "deployment_capacity_semantic": "SELECTIVE_DEPLOYMENT_CAPACITY",
            "bootstrap_or_residual_cash_state": "NORMAL_INVESTED_PORTFOLIO",
            "trading_consumer_connected": False,
            "envelope_hash": "test-g113-risk",
        },
    }


def _add(
    symbol: str,
    *,
    requested_weight: float,
    current_quantity: int,
    current_weight: float,
    priority: int,
    cap: float = 0.25,
) -> dict[str, object]:
    score = 1.0 - priority / 100.0
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "construction_priority": priority,
        "opportunity_buy_rank": priority,
        "runtime_opportunity_score": score,
        "confidence": score,
        "target_weight": current_weight + requested_weight,
        "requested_incremental_weight": requested_weight,
        "accepted_incremental_weight": requested_weight,
        "add_allocation_eligibility_status": "PASS",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "entry_admission_action": "ADD_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_class": "COMPARABLE_MARGINAL",
        "quality_status": "PASS",
        "current_quantity": current_quantity,
        "current_weight": current_weight,
        "reference_price": 1000.0,
        "portfolio_value": 1_000_000.0,
        "trading_unit": 100,
        "single_name_cap": cap,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": priority,
            "marginal_capital_value_class": "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
            "future_information_used": False,
        },
    }


def _new(symbol: str, *, weight: float, priority: int) -> dict[str, object]:
    score = 1.0 - priority / 100.0
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "construction_priority": priority,
        "opportunity_buy_rank": priority,
        "runtime_opportunity_score": score,
        "confidence": score,
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
        "entry_admission_action": "BUY_NEW_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_class": "COMPARABLE_MARGINAL",
        "quality_status": "PASS",
        "reference_price": 1000.0,
        "portfolio_value": 1_000_000.0,
        "trading_unit": 100,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": priority,
            "marginal_capital_value_class": "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
            "future_information_used": False,
        },
    }
