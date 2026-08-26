from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2022-08-19"


def test_phase31_g42_normal_strong_security_wins_with_cash_present() -> None:
    competition = _competition([_new("11110", quality="STRONG")], risk_pacing_intent="NORMAL_DEPLOYMENT")

    interaction = competition["market_candidate_cash_interaction"]

    assert interaction["schema_version"] == "market_candidate_cash_interaction.v1"
    assert interaction["stage"] == "BEFORE_FINAL_CAPITAL_WINNER"
    assert interaction["capital_competition_winner_type"] == "NEW_BUY"
    assert interaction["capital_competition_winner_symbol"] == "11110"
    assert {item["competitor_type"] for item in interaction["competitor_set"]} == {"NEW_BUY", "CASH_OPTIONALITY"}
    assert competition["capital_competition_winner_symbol"] == "11110"


def test_phase31_g42_normal_comparable_marginal_remains_deploy_eligible() -> None:
    competition = _competition([_new("22220", quality="COMPARABLE_MARGINAL")], risk_pacing_intent="NORMAL_DEPLOYMENT")

    security = _interaction_by_symbol(competition, "22220")

    assert security["interaction_result"] == "DEPLOY_ELIGIBLE"
    assert competition["capital_competition_winner_type"] == "NEW_BUY"
    assert competition["capital_competition_winner_symbol"] == "22220"


def test_phase31_g42_preserve_marginal_candidate_prefers_cash_without_late_target_mutation() -> None:
    competition = _competition([_new("33330", quality="COMPARABLE_MARGINAL")], risk_pacing_intent="PRESERVE_OPTIONALITY")

    security = _interaction_by_symbol(competition, "33330")

    assert competition["competitors"][0]["status"] == "COMPETITOR_SELECTED"
    assert competition["competitors"][0]["accepted_weight"] == 0.1
    assert security["interaction_result"] == "CASH_PREFERRED"
    assert competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert competition["authority"]["legacy_late_risk_pacing_decision_authority_count"] == 0
    assert competition["competitors"][0]["constraint_evidence"]["risk_pacing_decision"]["compatibility_evidence_only"] is True
    assert competition["competitors"][0]["constraint_evidence"]["risk_pacing_decision"]["late_decision_authority_active"] is False


def test_phase31_g42_add_and_new_buy_share_pre_final_competitor_set() -> None:
    competition = _competition(
        [
            _add("44440", quality="COMPARABLE_HIGH", accepted_incremental_weight=0.08, target_weight=0.13),
            _new("55550", quality="STRONG", accepted_buy_new_weight=0.12, target_weight=0.12),
        ],
        risk_pacing_intent="GRADUAL_REDEPLOYMENT",
    )

    interaction = competition["market_candidate_cash_interaction"]

    assert {item["competitor_type"] for item in interaction["competitor_set"]} == {"ADD", "NEW_BUY", "CASH_OPTIONALITY"}
    assert interaction["capital_competition_winner_type"] == "NEW_BUY"
    assert interaction["capital_competition_winner_symbol"] == "55550"
    assert interaction["second_capital_winner_authority"] is False
    assert interaction["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert interaction["pc_computes_share_quantity"] is False


def test_phase31_g42_blocked_and_insufficient_candidates_fail_closed_before_cash_wins() -> None:
    competition = _competition(
        [
            _new("66660", quality="BLOCKED", target_weight=0.0, accepted_buy_new_weight=0.0),
            _new("77770", quality="INSUFFICIENT", target_weight=0.0, accepted_buy_new_weight=0.0),
        ],
        risk_pacing_intent="NORMAL_DEPLOYMENT",
        total_target_weight=0.0,
    )

    blocked = _interaction_by_symbol(competition, "66660")
    insufficient = _interaction_by_symbol(competition, "77770")
    interaction = competition["market_candidate_cash_interaction"]

    assert blocked["interaction_result"] == "BLOCKED"
    assert insufficient["interaction_result"] == "FAIL_CLOSED"
    assert interaction["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert interaction["legacy_marginal_class_used_as_interaction_authority"] is False
    assert all(item["legacy_marginal_class_used_as_authority"] is False for item in interaction["competitor_set"])


def test_phase31_g42_consumes_authoritative_evidence_and_blocks_forbidden_inputs() -> None:
    competition = _competition(
        [_new("88880", quality="STRONG", future_return=10.0, paper_profit=999999, mfe=4.2)],
        risk_pacing_intent="NORMAL_DEPLOYMENT",
    )

    interaction = competition["market_candidate_cash_interaction"]

    assert interaction["canonical_cash_evidence_consumed"] is True
    assert interaction["canonical_opportunity_quality_consumed"] is True
    assert interaction["authoritative_risk_pacing_consumed"] is True
    assert interaction["market_quality_recomputed_in_pc"] is False
    assert interaction["risk_pacing_recomputed_in_pc"] is False
    assert interaction["opportunity_quality_recomputed_in_pc"] is False
    assert interaction["future_information_used"] is False
    assert interaction["historical_outcome_used"] is False
    assert interaction["paper_ledger_input_used"] is False
    assert interaction["mfe_mae_input_used"] is False
    assert interaction["outcome_derived_decision_rule_count"] == 0


def _interaction_by_symbol(competition: dict, symbol: str) -> dict:
    for item in competition["market_candidate_cash_interaction"]["interaction_results"]:
        if item["symbol"] == symbol:
            return item
    raise AssertionError(f"missing interaction result for {symbol}")


def _competition(
    members: list[dict],
    *,
    risk_pacing_intent: str,
    market_quality_state: str = "HEALTHY_EXPANSION",
    total_target_weight: float = 0.1,
) -> dict:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.3,
        total_target_weight=total_target_weight,
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
