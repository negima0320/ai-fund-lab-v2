from __future__ import annotations

from ai_fund_lab_v2.strategy import marginal_capital_value


def _member(symbol: str, *, held: bool, rank: int = 3, score: float = 0.55) -> dict[str, object]:
    return {
        "symbol": symbol,
        "business_date": "2026-07-15",
        "current_position": held,
        "current_quantity": 300 if held else 0,
        "current_weight": 0.04 if held else 0.0,
        "target_weight": 0.05,
        "position_campaign_id": f"pc-{symbol}-0001" if held else "",
        "membership_intent": "RETAIN" if held else "ADD_CANDIDATE",
        "pm_action": "ADD" if held else "",
        "semantic_buy_type": "BUY_ADD" if held else "BUY_NEW",
        "source_candidate_id": f"candidate-{symbol}",
        "source_opportunity_id": f"opportunity-{symbol}",
        "source_pm_decision_ref": f"pm-{symbol}-add" if held else "",
        "input_opportunity_rank": rank,
        "runtime_opportunity_score": score,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "entry_admission_action": "ADD_REDUCED_ONLY" if held else "BUY_NEW_ALLOWED",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "selection_quality_tier": "TOP_TIER",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "strategy_intelligence_relative_strength_state": "STRONG",
        "tick_normalized_trend_state": "ROBUST",
        "momentum_confidence_state": "CONFIRMED",
        "liquidity_capacity_status": "PASS",
        "rolling_median_traded_value_20": 100000000,
        "phase29_l19_lot_resolution": {
            "final_allocated_quantity": 100,
            "one_lot_notional": 90000,
            "one_lot_quantity": 100,
            "pc_positive_executable_quantity_authority": {"status": "PASS"},
        },
    }


def _cash() -> dict[str, object]:
    return {
        "business_date": "2026-07-15",
        "cash_competitor_evidence_hash": "cash",
        "cash_preference_semantic": "RISK_OPTIONALITY_PREFERRED",
        "current_cash_weight": 0.2,
        "evidence_completeness": "COMPLETE",
        "remaining_cash_weight": 0.2,
        "reason_codes": ["VALID_POLICY_RESERVE"],
    }


def test_phase32_eh_pc_consumer_is_shadow_only_and_preserves_new_equivalence() -> None:
    add = _member("94320", held=True)
    add["add_investment_evidence"] = {
        "incremental_value": {"state": "UNKNOWN"},
        "expected_edge": {"state": "WEAKENING"},
        "opportunity_cost": {"state": "NEW_BUY_SUPERIOR"},
    }
    new = _member("72030", held=False, rank=1, score=0.82)
    security = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-15",
        members=[add, new],
    )
    marginal = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add, new],
        competitors=[{"competitor_type": "NEW_BUY", "symbol": "72030", "accepted_weight": 0.05, "status": "COMPETITOR_SELECTED"}],
        cash_evidence=_cash(),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "72030"},
    )

    consumer = marginal_capital_value.build_pc_security_opportunity_shadow_consumer(
        business_date="2026-07-15",
        security_opportunity_evidence=security,
        unified_marginal_capital_shadow=marginal,
    )

    assert consumer["authority_type"] == "PC_SECURITY_OPPORTUNITY_SHADOW_CONSUMER"
    assert consumer["authoritative_consumer_count"] == 0
    assert consumer["production_allocation_consumer"] is False
    assert consumer["production_ordering_consumer"] is False
    assert consumer["production_sizing_consumer"] is False
    assert consumer["runtime_planning_consumer"] is False
    assert consumer["production_pc_path_unchanged"] is True
    assert consumer["new_equivalence"]["status"] == "PASS"
    assert consumer["add_unknown_reclassification_counts"]["COMPARABLE_NEGATIVE"] == 1


def test_phase32_eh_security_opportunity_alone_does_not_rescue_blocked_add() -> None:
    add = _member("94320", held=True)
    add["quality_action"] = "BUY_WAIT"
    add["add_investment_evidence"] = {
        "incremental_value": {"state": "UNKNOWN"},
        "expected_edge": {"state": "IMPROVING"},
        "opportunity_cost": {"state": "PASS"},
    }
    security = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-15",
        members=[add],
    )
    marginal = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add],
        competitors=[{"competitor_type": "ADD", "symbol": "94320", "accepted_weight": 0.0, "status": "REJECTED"}],
        cash_evidence=_cash(),
        market_candidate_cash_interaction={"capital_competition_winner_type": "CASH_OPTIONALITY"},
    )

    consumer = marginal_capital_value.build_pc_security_opportunity_shadow_consumer(
        business_date="2026-07-15",
        security_opportunity_evidence=security,
        unified_marginal_capital_shadow=marginal,
    )

    assert consumer["add_unknown_reclassification_counts"]["BLOCKED"] == 1
    assert consumer["weak_add_negative_controls"]["status"] == "PASS"
    assert consumer["weak_add_negative_controls"]["rescued_by_security_opportunity_only"] == 0
    assert consumer["failure_isolation"]["consumer_failure_blocks_production"] is False


def test_phase32_eh_missing_security_record_is_diagnostic_only_failure_isolated() -> None:
    new = _member("72030", held=False, rank=1, score=0.82)
    marginal = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[new],
        competitors=[{"competitor_type": "NEW_BUY", "symbol": "72030", "accepted_weight": 0.05, "status": "COMPETITOR_SELECTED"}],
        cash_evidence=_cash(),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "72030"},
    )

    consumer = marginal_capital_value.build_pc_security_opportunity_shadow_consumer(
        business_date="2026-07-15",
        security_opportunity_evidence={"records": [], "security_opportunity_evidence_hash": "missing"},
        unified_marginal_capital_shadow=marginal,
    )

    row = consumer["diagnostic_rows"][0]
    assert row["security_evidence_completeness"] == "MISSING"
    assert consumer["failure_isolation"]["status"] == "PASS"
    assert consumer["failure_isolation"]["consumer_failure_blocks_production"] is False
    assert consumer["production_pc_path_unchanged"] is True
