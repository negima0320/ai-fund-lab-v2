from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2022-08-19"


def test_phase31_g41_cash_evidence_exists_with_deployable_competitors() -> None:
    competition = _competition([_new("11110", quality="STRONG")], risk_pacing_intent="NORMAL_DEPLOYMENT")

    cash = competition["canonical_cash_competitor_evidence"]

    assert competition["competitors"][0]["status"] == "COMPETITOR_SELECTED"
    assert competition["cash_competitor"]["status"] == "COMPETITOR_SELECTED"
    assert cash["schema_version"] == "cash_competitor_evidence.v1"
    assert cash["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert cash["competitor_type"] == "CASH_OPTIONALITY"
    assert cash["available_deployable_competitor_count"] == 1
    assert cash["best_opportunity_quality_class"] == "STRONG"
    assert cash["cash_preference_semantic"] == "OPTIONALITY_LOW"
    assert cash["current_final_winner_rule_changed"] is False


def test_phase31_g41_cash_responds_to_market_quality_with_same_opportunity_set() -> None:
    members = [_new("11110", quality="COMPARABLE_MARGINAL")]

    normal = _competition(members, risk_pacing_intent="NORMAL_DEPLOYMENT", market_quality_state="HEALTHY_EXPANSION")
    cautious = _competition(members, risk_pacing_intent="CAUTIOUS_DEPLOYMENT", market_quality_state="SHORT_TERM_BREADTH_BREAKDOWN")
    gradual = _competition(members, risk_pacing_intent="GRADUAL_REDEPLOYMENT", market_quality_state="RECOVERY_CONFIRMATION_INCOMPLETE")
    preserve = _competition(members, risk_pacing_intent="PRESERVE_OPTIONALITY", market_quality_state="INSUFFICIENT_EVIDENCE")

    assert normal["canonical_cash_competitor_evidence"]["cash_preference_semantic"] == "OPTIONALITY_NEUTRAL"
    assert cautious["canonical_cash_competitor_evidence"]["cash_preference_semantic"] == "OPTIONALITY_ELEVATED"
    assert gradual["canonical_cash_competitor_evidence"]["cash_preference_semantic"] == "OPTIONALITY_ELEVATED"
    assert preserve["canonical_cash_competitor_evidence"]["cash_preference_semantic"] == "OPTIONALITY_PREFERRED"
    assert "CAUTIOUS_MARKET_OPTIONALITY_ELEVATED" in cautious["canonical_cash_competitor_evidence"]["reason_codes"]
    assert "RECOVERY_INCOMPLETE_OPTIONALITY_ELEVATED" in gradual["canonical_cash_competitor_evidence"]["reason_codes"]
    assert "PRESERVE_OPTIONALITY_PREFERRED" in preserve["canonical_cash_competitor_evidence"]["reason_codes"]


def test_phase31_g41_cash_responds_to_opportunity_set_with_same_market() -> None:
    strong = _competition([_new("11110", quality="STRONG")], risk_pacing_intent="CAUTIOUS_DEPLOYMENT")
    marginal = _competition([_new("22220", quality="COMPARABLE_MARGINAL"), _new("33330", quality="WEAK_VALID")], risk_pacing_intent="CAUTIOUS_DEPLOYMENT")

    strong_cash = strong["canonical_cash_competitor_evidence"]
    marginal_cash = marginal["canonical_cash_competitor_evidence"]

    assert strong_cash["cash_preference_semantic"] == "OPTIONALITY_NEUTRAL"
    assert marginal_cash["cash_preference_semantic"] == "OPTIONALITY_ELEVATED"
    assert "STRONG_OPPORTUNITY_PRESENT" in strong_cash["reason_codes"]
    assert "MARGINAL_OPPORTUNITY_SET" in marginal_cash["reason_codes"]


def test_phase31_g41_add_is_included_in_cash_competitor_context() -> None:
    competition = _competition([_add("94320", quality="COMPARABLE_HIGH"), _new("11110", quality="WEAK_VALID")], risk_pacing_intent="GRADUAL_REDEPLOYMENT")

    cash = competition["canonical_cash_competitor_evidence"]

    assert cash["opportunity_quality_distribution"]["COMPARABLE_HIGH"] == 1
    assert cash["opportunity_quality_distribution"]["WEAK_VALID"] == 1
    assert {item["competitor_type"] for item in competition["competitors"]} == {"ADD", "NEW_BUY"}
    assert competition["cash_competitor"]["canonical_cash_competitor_evidence"]["cash_competitor_evidence_hash"] == cash["cash_competitor_evidence_hash"]


def test_phase31_g41_missing_market_or_risk_pacing_fails_cash_evidence_closed() -> None:
    competition = build_capital_competition_framework(
        members=[_new("11110", quality="STRONG")],
        target_gross_exposure=0.2,
        total_target_weight=0.1,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence={},
    )
    cash = competition["canonical_cash_competitor_evidence"]

    assert cash["evidence_completeness"] == "INCOMPLETE_FAIL_CLOSED"
    assert cash["cash_preference_semantic"] == "OPTIONALITY_PREFERRED"
    assert "CASH_EVIDENCE_MISSING_INPUT_FAIL_CLOSED" in cash["reason_codes"]


def test_phase31_g41_forbidden_inputs_and_quantity_boundary() -> None:
    competition = _competition(
        [
            _new(
                "11110",
                quality="STRONG",
                future_return=0.8,
                mfe=0.2,
                fill_outcome="WIN",
            )
        ],
        risk_pacing_intent="NORMAL_DEPLOYMENT",
    )
    cash = competition["canonical_cash_competitor_evidence"]

    assert cash["future_information_used"] is False
    assert cash["historical_outcome_used"] is False
    assert cash["paper_ledger_input_used"] is False
    assert cash["audit_result_input_used"] is False
    assert cash["fixed_exposure_target_created"] is False
    assert cash["fixed_buy_count_created"] is False
    assert cash["quantity_authority_owner"] == "POSITION_SIZING"
    assert cash["cash_recomputes_quantity"] is False
    assert cash["cash_creates_alpha_feature"] is False


def test_phase31_g41_current_pc_winner_equivalence() -> None:
    before_shape = _competition([_new("11110", quality="STRONG"), _new("22220", quality="WEAK_VALID")], risk_pacing_intent="NORMAL_DEPLOYMENT")
    after_shape = _competition([_new("11110", quality="STRONG"), _new("22220", quality="WEAK_VALID")], risk_pacing_intent="NORMAL_DEPLOYMENT")

    assert [(item["symbol"], item["status"], item["accepted_weight"]) for item in before_shape["competitors"]] == [
        (item["symbol"], item["status"], item["accepted_weight"]) for item in after_shape["competitors"]
    ]
    assert before_shape["final_no_deployable_opportunity"] == after_shape["final_no_deployable_opportunity"]
    assert before_shape["canonical_cash_competitor_evidence"]["current_final_winner_rule_changed"] is False


def _competition(members: list[dict], *, risk_pacing_intent: str, market_quality_state: str = "HEALTHY_EXPANSION") -> dict:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.3,
        total_target_weight=0.1,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing(risk_pacing_intent, market_quality_state=market_quality_state),
    )


def _risk_pacing(intent: str, *, market_quality_state: str) -> dict:
    completeness = "INSUFFICIENT" if market_quality_state == "INSUFFICIENT_EVIDENCE" else "COMPLETE"
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": completeness,
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": market_quality_state,
            "market_quality_evidence_completeness": completeness,
            "market_quality_reason_codes": [market_quality_state],
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }


def _new(symbol: str, *, quality: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "target_weight": 0.1,
        "accepted_buy_new_weight": 0.1,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "future_information_used": False,
        },
    }
    row.update(overrides)
    return row


def _add(symbol: str, *, quality: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": True,
        "pm_action": "ADD",
        "current_weight": 0.05,
        "target_weight": 0.15,
        "accepted_incremental_weight": 0.1,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "future_information_used": False,
        },
    }
    row.update(overrides)
    return row
