from __future__ import annotations

from ai_fund_lab_v2.strategy import marginal_capital_value


def _member(symbol: str = "94320", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": symbol,
        "business_date": "2026-07-15",
        "current_position": True,
        "current_quantity": 300,
        "current_weight": 0.04,
        "target_weight": 0.04,
        "position_campaign_id": f"pc-{symbol}-0001",
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "semantic_buy_type": "BUY_ADD",
        "source_candidate_id": f"candidate-{symbol}",
        "source_opportunity_id": f"opportunity-{symbol}",
        "source_pm_decision_ref": f"pm-{symbol}-add",
        "input_opportunity_rank": 2,
        "runtime_opportunity_score": 0.62,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "entry_admission_action": "ADD_ALLOWED",
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
        "add_investment_evidence": {
            "incremental_value": {"state": "POSITIVE"},
            "expected_edge": {"state": "IMPROVING"},
            "opportunity_cost": {"state": "PASS"},
        },
        "phase29_l19_lot_resolution": {
            "final_allocated_quantity": 100,
            "one_lot_notional": 90000,
            "one_lot_quantity": 100,
            "pc_positive_executable_quantity_authority": {"status": "PASS"},
        },
    }
    payload.update(overrides)
    return payload


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


def _adequacy_for(*members: dict[str, object]) -> dict[str, object]:
    security = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-15",
        members=list(members),
    )
    shadow = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=list(members),
        competitors=[
            {
                "competitor_type": "ADD",
                "symbol": str(member["symbol"]),
                "accepted_weight": 0.02,
                "status": "COMPETITOR_SELECTED",
            }
            for member in members
        ],
        cash_evidence=_cash(),
        market_candidate_cash_interaction={"capital_competition_winner_type": "ADD", "capital_competition_winner_symbol": str(members[0]["symbol"])},
    )
    return marginal_capital_value.build_winner_position_size_adequacy_shadow(
        business_date="2026-07-15",
        security_opportunity_evidence=security,
        unified_marginal_capital_shadow=shadow,
    )


def test_phase32_ej_target_equality_is_control_not_adequacy_label() -> None:
    adequacy = _adequacy_for(_member())

    row = adequacy["diagnostic_rows"][0]
    assert adequacy["authority_type"] == "WINNER_POSITION_SIZE_ADEQUACY_SHADOW"
    assert adequacy["authoritative_consumer_count"] == 0
    assert adequacy["production_allocation_consumer"] is False
    assert adequacy["current_target_used_as_control_not_label"] == "PASS"
    assert adequacy["target_equality_labeled_adequate_by_itself"] == 0
    assert row["current_target_control"]["target_equals_current"] is True
    assert row["current_target_control"]["adequately_sized_from_target_equality_only"] is False
    assert row["position_size_adequacy_class"] != "ADEQUATELY_SIZED"
    assert row["fixed_add_preference"] is False


def test_phase32_ej_positive_next_lot_can_be_potential_undercapitalized() -> None:
    adequacy = _adequacy_for(_member(target_weight=0.06))

    row = adequacy["diagnostic_rows"][0]
    assert row["position_size_adequacy_class"] == "POTENTIAL_UNDERCAPITALIZED"
    assert row["positive_next_lot_requirements"]["complete_security_opportunity"] is True
    assert row["positive_next_lot_requirements"]["next_lot_feasible"] is True
    assert row["positive_next_lot_requirements"]["opportunity_cost_competitive"] is True


def test_phase32_ej_negative_controls_are_not_rescued_by_security_opportunity() -> None:
    bq_blocked = _member("11110", quality_action="BUY_WAIT")
    edge_weak = _member(
        "22220",
        add_investment_evidence={
            "incremental_value": {"state": "UNKNOWN"},
            "expected_edge": {"state": "WEAKENING"},
            "opportunity_cost": {"state": "PASS"},
        },
    )
    new_superior = _member(
        "33330",
        add_investment_evidence={
            "incremental_value": {"state": "UNKNOWN"},
            "expected_edge": {"state": "IMPROVING"},
            "opportunity_cost": {"state": "NEW_BUY_SUPERIOR"},
        },
    )

    adequacy = _adequacy_for(bq_blocked, edge_weak, new_superior)

    classes = {row["symbol"]: row["position_size_adequacy_class"] for row in adequacy["diagnostic_rows"]}
    assert classes["11110"] == "BQ_ENTRY_BLOCKED"
    assert classes["22220"] == "WEAKENING_NO_ADD"
    assert classes["33330"] == "LOSES_TO_OTHER_CAPITAL_USE"
    assert adequacy["negative_controls"]["status"] == "PASS"
    assert adequacy["negative_controls"]["security_opportunity_alone_rescued_rows"] == 0
    assert adequacy["action_neutral_competition"]["status"] == "PASS"
