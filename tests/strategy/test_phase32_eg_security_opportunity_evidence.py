from __future__ import annotations

from ai_fund_lab_v2.strategy import marginal_capital_value


def _member(symbol: str, *, held: bool, rank: int = 4, score: float = 0.42, pm_action: str = "") -> dict[str, object]:
    return {
        "symbol": symbol,
        "security_code": symbol,
        "business_date": "2026-07-15",
        "current_position": held,
        "current_quantity": 300 if held else 0,
        "current_weight": 0.04 if held else 0.0,
        "target_weight": 0.05,
        "position_campaign_id": f"pc-{symbol}-0001" if held else "",
        "membership_intent": "RETAIN" if held else "ADD_CANDIDATE",
        "pm_action": pm_action,
        "semantic_buy_type": "BUY_ADD" if held else "BUY_NEW",
        "source_candidate_id": f"candidate-{symbol}",
        "source_opportunity_id": f"opportunity-{symbol}",
        "input_opportunity_rank": rank,
        "runtime_opportunity_score": score,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_score": 0.7,
        "quality_status": "PASS",
        "entry_admission_action": "ADD_ALLOWED" if held else "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "selection_quality_tier": "TOP_TIER",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "strategy_intelligence_relative_strength_state": "STRONG",
        "tick_normalized_trend_state": "ROBUST",
        "momentum_confidence_state": "CONFIRMED",
        "liquidity_capacity_status": "PASS",
        "rolling_median_traded_value_20": 200000000,
    }


def test_phase32_eg_security_opportunity_is_shadow_only_and_action_neutral() -> None:
    result = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-15",
        members=[_member("94320", held=True, pm_action="ADD"), _member("72030", held=False, rank=2, score=0.8)],
    )

    assert result["schema_version"] == "security_opportunity_evidence.v1"
    assert result["authority_type"] == "SECURITY_OPPORTUNITY_SHADOW_AUTHORITY"
    assert result["shadow_only"] is True
    assert result["authoritative_consumer_count"] == 0
    assert result["action_authority"] is False
    assert result["target_weight_authority"] is False
    assert result["quantity_authority"] is False
    assert result["production_allocation_consumer"] is False
    assert result["position_relationship_separate_from_opportunity"] is True

    held = next(record for record in result["records"] if record["symbol"] == "94320")
    intrinsic = held["intrinsic_security_evidence"]
    assert "current_weight" not in intrinsic
    assert "current_quantity" not in intrinsic
    assert "position_campaign_id" not in intrinsic
    assert held["position_relationship"]["relationship_state"] == "HELD"
    assert held["normalized_security_opportunity"]["ownership_status_intrinsic_score_effect"] == "NONE"
    assert held["normalized_security_opportunity"]["evidence_completeness_class"] == "COMPLETE"


def test_phase32_eg_ownership_does_not_change_intrinsic_score_or_rank() -> None:
    flat = _member("94320", held=False, rank=3, score=0.61)
    flat["reentry_semantic_state"] = "REENTRY_NOT_APPLICABLE"
    held = _member("94320", held=True, rank=3, score=0.61, pm_action="ADD")

    flat_record = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-15",
        members=[flat],
    )["records"][0]
    held_record = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-16",
        members=[held],
    )["records"][0]

    assert flat_record["intrinsic_security_evidence"]["runtime_opportunity_score"] == held_record["intrinsic_security_evidence"]["runtime_opportunity_score"]
    assert flat_record["intrinsic_security_evidence"]["input_opportunity_rank"] == held_record["intrinsic_security_evidence"]["input_opportunity_rank"]
    assert flat_record["position_relationship"]["relationship_state"] == "FLAT_NEVER_HELD_OR_UNKNOWN"
    assert flat_record["position_relationship"]["relationship_state"] != held_record["position_relationship"]["relationship_state"]
    assert held_record["normalized_security_opportunity"]["position_relationship_used_for_intrinsic_score"] is False


def test_phase32_eg_add_unknown_state_remains_action_specific_ref_not_intrinsic() -> None:
    member = _member("94320", held=True, pm_action="ADD")
    member["add_investment_evidence"] = {
        "incremental_value": {"state": "UNKNOWN"},
        "expected_edge": {"state": "IMPROVING"},
        "opportunity_cost": {"state": "NEW_BUY_SUPERIOR"},
    }

    record = marginal_capital_value.build_security_opportunity_evidence(
        business_date="2026-07-15",
        members=[member],
    )["records"][0]

    assert "add_incremental_investment_value_state" not in record["intrinsic_security_evidence"]
    assert record["action_specific_evidence_refs"]["add_incremental_investment_value_state"] == "UNKNOWN"
    assert record["normalized_security_opportunity"]["evidence_completeness_class"] == "COMPLETE"
