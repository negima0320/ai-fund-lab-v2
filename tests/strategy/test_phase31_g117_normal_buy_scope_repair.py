from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import apply_lot_aware_final_reallocation


BUSINESS_DATE = "2022-10-03"


def test_phase31_g117_normal_new_buy_cash_preferred_enters_final_allocation_loop() -> None:
    members = [
        _new(symbol, priority=index + 1, weight=0.033636)
        for index, symbol in enumerate(
            [
                "94340",
                "37820",
                "93600",
                "33700",
                "83060",
                "92420",
                "58200",
                "41920",
                "89180",
                "76470",
                "45750",
                "33500",
                "11110",
                "11120",
                "11130",
                "11140",
                "11150",
                "11160",
                "11170",
                "11180",
                "11190",
                "11200",
            ]
        )
    ]
    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {
                "symbol": str(member["symbol"]),
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.01,
                "phase29_l19_lot_resolution": {
                    "semantic_type": "BUY_NEW",
                    "one_lot_quantity": 100,
                    "one_lot_notional": 10_000.0,
                    "one_lot_feasibility_status": "PASS",
                    "final_allocated_quantity": 100,
                    "safety_hard_cap": 0.25,
                    "safety_hard_cap_weight": 0.25,
                    "safety_hard_cap_preserved": True,
                    "post_trade_weight": 0.01,
                },
            }
            for member in members
        ],
        target_gross_exposure=0.74,
        single_name_cap=0.25,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.74},
        final_capital_competition_risk_pacing_evidence=_risk(),
    )

    evidence = result["evidence"]
    interactions = evidence["lot_reconsideration_binding_integration"]["pre_lot_market_candidate_cash_interaction"]["interaction_results"]
    new_buy_interactions = [row for row in interactions if row["competitor_type"] == "NEW_BUY"]
    allocation_iterations = evidence["phase29_l19_allocation_iterations"]
    skipped_reasons = {str(row.get("reason") or "") for row in evidence["skipped"]}

    assert len(members) == 22
    assert sum(1 for member in members if member.get("pm_action") == "ADD") == 0
    assert any(row["interaction_result"] == "CASH_PREFERRED" for row in new_buy_interactions)
    assert allocation_iterations
    assert any(row["participant_type"] == "BUY_NEW" for row in allocation_iterations)
    assert "g43_binding_cash_preferred" not in skipped_reasons
    assert sum(float(member.get("lot_aware_accepted_buy_new_weight") or 0.0) > 0.0 for member in result["members"]) > 1


def test_phase31_g117_add_cash_preferred_still_uses_g115_staged_one_increment() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _add("76470", requested_weight=0.05, current_quantity=400, current_weight=0.04, priority=1),
        ],
        lot_feasibility_rows=[
            {
                "symbol": "76470",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.01,
                "phase29_l19_lot_resolution": {
                    "semantic_type": "BUY_ADD",
                    "one_lot_quantity": 100,
                    "one_lot_notional": 10_000.0,
                    "one_lot_feasibility_status": "PASS",
                    "final_allocated_quantity": 100,
                    "safety_hard_cap": 0.25,
                    "safety_hard_cap_weight": 0.25,
                    "safety_hard_cap_preserved": True,
                    "post_trade_weight": 0.05,
                },
            }
        ],
        target_gross_exposure=0.30,
        single_name_cap=0.25,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.30},
        final_capital_competition_risk_pacing_evidence=_risk(),
    )
    member = result["members"][0]
    lot_authority = member["target_weight_resolution"]["lot_aware_final_reallocation"]
    g115_authority = lot_authority["canonical_add_marginal_capital_competition_authority"]

    assert "G115_CASH_PREFERRED_ADD_SENT_TO_STAGED_FRONTIER_GUARD" in result["reason_codes"]
    assert member["lot_aware_accepted_incremental_weight"] == 0.01
    assert g115_authority["authority_status"] == "AUTHORITATIVE_STAGED_PC_BINDING"
    assert g115_authority["authorized_increment_weight"] == 0.01
    assert g115_authority["full_requested_block_authorized"] is False
    assert lot_authority["pc_positive_executable_quantity_authority"]["final_allocated_quantity"] == 100


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
            "bootstrap_or_residual_cash_state": "EMPTY_OR_NEAR_EMPTY_BOOTSTRAP",
            "envelope_hash": "test-g117-risk",
        },
    }


def _new(symbol: str, *, priority: int, weight: float) -> dict[str, object]:
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
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_class": "COMPARABLE_MARGINAL",
        "quality_status": "PASS",
        "marginal_capital_value_authority": _marginal(symbol, priority),
    }


def _add(
    symbol: str,
    *,
    requested_weight: float,
    current_quantity: int,
    current_weight: float,
    priority: int,
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
        "reference_price": 100.0,
        "portfolio_value": 1_000_000.0,
        "trading_unit": 100,
        "single_name_cap": 0.25,
        "safety_hard_cap": 0.25,
        "marginal_capital_value_authority": _marginal(symbol, priority),
    }


def _marginal(symbol: str, priority: int) -> dict[str, object]:
    return {
        "canonical_marginal_capital_priority_index": priority,
        "marginal_capital_value_class": "ELIGIBLE_COMPARABLE",
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_evidence": {
            "schema_version": "opportunity_quality.v1",
            "symbol": symbol,
            "business_date": BUSINESS_DATE,
            "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
            "future_information_used": False,
            "historical_outcome_used": False,
        },
        "future_information_used": False,
    }
