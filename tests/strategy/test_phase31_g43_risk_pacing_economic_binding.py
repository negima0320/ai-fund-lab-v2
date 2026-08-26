from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2022-08-19"


def test_phase31_g43_full_binding_matrix_core_cases() -> None:
    assert _result(_competition([_new("10010", quality="STRONG")], "NORMAL_DEPLOYMENT"), "10010") == "DEPLOY_ELIGIBLE"
    assert _result(_competition([_new("10020", quality="COMPARABLE_HIGH")], "NORMAL_DEPLOYMENT"), "10020") == "DEPLOY_ELIGIBLE"
    assert _result(_competition([_new("10030", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT"), "10030") == "DEPLOY_ELIGIBLE"
    assert _result(_competition([_new("10040", quality="WEAK_VALID")], "NORMAL_DEPLOYMENT"), "10040") == "SELECTIVE_COMPETITION"

    assert _result(_competition([_new("20010", quality="STRONG")], "GRADUAL_REDEPLOYMENT"), "20010") == "DEPLOY_ELIGIBLE"
    assert _result(_competition([_new("20020", quality="COMPARABLE_HIGH")], "GRADUAL_REDEPLOYMENT"), "20020") == "SELECTIVE_COMPETITION"
    assert _cash_wins(_competition([_new("20030", quality="COMPARABLE_MARGINAL")], "GRADUAL_REDEPLOYMENT"))
    assert _cash_wins(_competition([_new("20040", quality="WEAK_VALID")], "GRADUAL_REDEPLOYMENT"))

    assert _result(_competition([_new("30010", quality="STRONG")], "CAUTIOUS_DEPLOYMENT"), "30010") == "SELECTIVE_COMPETITION"
    assert _cash_wins(_competition([_new("30030", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT"))
    assert _cash_wins(_competition([_new("30040", quality="WEAK_VALID")], "CAUTIOUS_DEPLOYMENT"))

    assert _cash_wins(_competition([_new("40020", quality="COMPARABLE_HIGH", caution_sufficient=True)], "PRESERVE_OPTIONALITY"))
    assert _cash_wins(_competition([_new("40030", quality="COMPARABLE_MARGINAL")], "PRESERVE_OPTIONALITY"))
    assert _cash_wins(_competition([_new("40040", quality="WEAK_VALID")], "PRESERVE_OPTIONALITY"))


def test_phase31_g43_cautious_comparable_high_requires_caution_sufficient_evidence() -> None:
    insufficient = _competition([_new("50010", quality="COMPARABLE_HIGH")], "CAUTIOUS_DEPLOYMENT")
    sufficient = _competition([_new("50020", quality="COMPARABLE_HIGH", caution_sufficient=True)], "CAUTIOUS_DEPLOYMENT")

    assert _result(insufficient, "50010") == "CASH_PREFERRED"
    assert _cash_wins(insufficient)
    assert _result(sufficient, "50020") == "SELECTIVE_COMPETITION"
    assert sufficient["capital_competition_winner_symbol"] == "50020"
    assert "CAUTION_SUFFICIENT_SYMBOL_EVIDENCE" in _record(sufficient, "50020")["binding_reason_codes"]


def test_phase31_g43_strong_preserve_exception_and_caution_override() -> None:
    cautious = _competition([_new("60010", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    preserve = _competition([_new("60020", quality="STRONG", preserve_exception=True)], "PRESERVE_OPTIONALITY")

    assert cautious["capital_competition_winner_symbol"] == "60010"
    assert preserve["capital_competition_winner_symbol"] == "60020"
    assert _result(cautious, "60010") == "SELECTIVE_COMPETITION"
    assert _result(preserve, "60020") == "SELECTIVE_COMPETITION"
    assert "STRONG_CAN_OVERRIDE_CAUTION" in _record(cautious, "60010")["binding_reason_codes"]
    assert "PRESERVE_OPTIONALITY_EXCEPTION_COMPLETE" in _record(preserve, "60020")["binding_reason_codes"]


def test_phase31_g43_same_candidate_different_market_changes_decision() -> None:
    normal = _competition([_new("70010", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT")
    cautious = _competition([_new("70010", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")

    assert normal["capital_competition_winner_symbol"] == "70010"
    assert _result(normal, "70010") == "DEPLOY_ELIGIBLE"
    assert _cash_wins(cautious)
    assert _result(cautious, "70010") == "CASH_PREFERRED"


def test_phase31_g43_same_market_different_candidate_changes_decision() -> None:
    strong = _competition([_new("80010", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    marginal = _competition([_new("80020", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")

    assert strong["capital_competition_winner_symbol"] == "80010"
    assert _cash_wins(marginal)


def test_phase31_g43_gradual_caution_and_preserve_caution_differ() -> None:
    gradual = _competition([_new("90010", quality="COMPARABLE_HIGH")], "GRADUAL_REDEPLOYMENT")
    cautious = _competition([_new("90010", quality="COMPARABLE_HIGH")], "CAUTIOUS_DEPLOYMENT")
    cautious_strong = _competition([_new("90020", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    preserve_strong = _competition([_new("90020", quality="STRONG", preserve_exception=False)], "PRESERVE_OPTIONALITY")

    assert gradual["capital_competition_winner_symbol"] == "90010"
    assert _cash_wins(cautious)
    assert cautious_strong["capital_competition_winner_symbol"] == "90020"
    assert _cash_wins(preserve_strong)


def test_phase31_g43_recovery_redeployment_path_is_date_reevaluated_without_latch() -> None:
    cautious = _competition([_new("91010", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")
    normal = _competition([_new("91010", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT")

    assert _cash_wins(cautious)
    assert normal["capital_competition_winner_symbol"] == "91010"
    assert cautious["market_candidate_cash_interaction"]["risk_pacing_intent"] == "CAUTIOUS_DEPLOYMENT"
    assert normal["market_candidate_cash_interaction"]["risk_pacing_intent"] == "NORMAL_DEPLOYMENT"


def test_phase31_g43_add_uses_same_binding_matrix() -> None:
    strong_add = _competition([_add("92010", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    marginal_add = _competition([_add("92020", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")

    assert strong_add["capital_competition_winner_type"] == "ADD"
    assert strong_add["capital_competition_winner_symbol"] == "92010"
    assert _cash_wins(marginal_add)
    assert _result(marginal_add, "92020") == "CASH_PREFERRED"


def test_phase31_g43_incomplete_market_risk_and_candidate_evidence_fail_closed() -> None:
    missing_risk = build_capital_competition_framework(
        members=[_new("93010", quality="STRONG", preserve_exception=True)],
        target_gross_exposure=0.3,
        total_target_weight=0.1,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence={},
    )
    missing_market = _competition(
        [_new("93020", quality="STRONG", preserve_exception=True)],
        "NORMAL_DEPLOYMENT",
        market_quality_state="INSUFFICIENT_EVIDENCE",
        market_quality_completeness="INSUFFICIENT",
    )
    insufficient_candidate = _competition([_new("93030", quality="INSUFFICIENT")], "NORMAL_DEPLOYMENT")

    assert _result(missing_risk, "93010") == "FAIL_CLOSED"
    assert _result(missing_market, "93020") == "FAIL_CLOSED"
    assert _result(insufficient_candidate, "93030") == "FAIL_CLOSED"
    assert _cash_wins(missing_risk)
    assert _cash_wins(missing_market)
    assert _cash_wins(insufficient_candidate)


def test_phase31_g43_blocked_not_rescued_and_binding_evidence_complete() -> None:
    competition = _competition([_new("94010", quality="BLOCKED")], "NORMAL_DEPLOYMENT")
    record = _record(competition, "94010")
    interaction = competition["market_candidate_cash_interaction"]

    assert record["interaction_result"] == "BLOCKED"
    assert _cash_wins(competition)
    assert record["risk_pacing_intent"] == "NORMAL_DEPLOYMENT"
    assert record["opportunity_quality_class"] == "BLOCKED"
    assert record["cash_preference_semantic"]
    assert record["binding_reason_codes"] == ["BLOCKED_NON_ELIGIBLE"]
    assert record["winner_loser"] == "LOSER"
    assert record["as_of_business_date"] == BUSINESS_DATE
    assert record["lineage"]["risk_pacing_as_of"] == BUSINESS_DATE
    assert interaction["full_risk_pacing_binding_matrix_implemented"] is True
    assert interaction["canonical_binding_decision_evidence_complete"] is True
    assert interaction["binding_reason_codes_implemented"] is True
    assert interaction["second_capital_winner_authority"] is False
    assert interaction["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert interaction["pc_computes_share_quantity"] is False
    assert interaction["legacy_late_risk_pacing_decision_authority_count"] == 0
    assert interaction["legacy_marginal_class_used_as_interaction_authority"] is False
    assert interaction["legacy_cash_winner_override_count"] == 0
    assert interaction["market_quality_recomputed_in_pc"] is False
    assert interaction["risk_pacing_recomputed_in_pc"] is False
    assert interaction["opportunity_quality_recomputed_in_pc"] is False
    assert interaction["future_information_used"] is False
    assert interaction["historical_outcome_used"] is False
    assert interaction["paper_ledger_input_used"] is False
    assert interaction["audit_result_input_used"] is False
    assert interaction["mfe_mae_input_used"] is False
    assert interaction["outcome_derived_decision_rule_count"] == 0


def _competition(
    members: list[dict],
    intent: str,
    *,
    market_quality_state: str = "HEALTHY_EXPANSION",
    market_quality_completeness: str = "COMPLETE",
) -> dict:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.3,
        total_target_weight=0.1,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing(
            intent,
            market_quality_state=market_quality_state,
            market_quality_completeness=market_quality_completeness,
        ),
    )


def _risk_pacing(intent: str, *, market_quality_state: str, market_quality_completeness: str) -> dict:
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": market_quality_completeness,
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": market_quality_state,
            "market_quality_evidence_completeness": market_quality_completeness,
            "market_quality_reason_codes": [market_quality_state],
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }


def _new(
    symbol: str,
    *,
    quality: str,
    caution_sufficient: bool = False,
    preserve_exception: bool | None = None,
) -> dict:
    return _member(
        symbol,
        quality=quality,
        current_position=False,
        competitor_fields={"membership_intent": "ADD_CANDIDATE", "accepted_buy_new_weight": 0.1},
        caution_sufficient=caution_sufficient,
        preserve_exception=preserve_exception,
    )


def _add(
    symbol: str,
    *,
    quality: str,
    caution_sufficient: bool = False,
    preserve_exception: bool | None = None,
) -> dict:
    return _member(
        symbol,
        quality=quality,
        current_position=True,
        competitor_fields={
            "pm_action": "ADD",
            "current_weight": 0.05,
            "target_weight": 0.15,
            "accepted_incremental_weight": 0.1,
            "expected_edge_improvement_state": "IMPROVING",
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
            "add_allocation_eligibility_status": "PASS",
            "same_campaign_continuation_status": "CONTINUING",
        },
        caution_sufficient=caution_sufficient,
        preserve_exception=preserve_exception,
    )


def _member(
    symbol: str,
    *,
    quality: str,
    current_position: bool,
    competitor_fields: dict,
    caution_sufficient: bool,
    preserve_exception: bool | None,
) -> dict:
    reasons = [f"test_{quality.lower()}"]
    source_evidence = {}
    if caution_sufficient:
        reasons.append("CAUTION_SUFFICIENT_SYMBOL_EVIDENCE")
        source_evidence["selection_quality_tier"] = "HIGH_QUALITY_CONTINUATION"
    if preserve_exception or (preserve_exception is None and quality == "STRONG"):
        reasons.append("OPPORTUNITY_QUALITY_EXPLICIT_POSITIVE_BUY_NEW_EVIDENCE")
    evidence = {
        "schema_version": "opportunity_quality.v1",
        "authority_type": "MARGINAL_CAPITAL_VALUE_AUTHORITY",
        "producer": "strategy.marginal_capital_value",
        "business_date": BUSINESS_DATE,
        "as_of_business_date": BUSINESS_DATE,
        "symbol": symbol,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "opportunity_quality_reason_codes": reasons,
        "evidence_completeness": "COMPLETE",
        "source_evidence": source_evidence,
        "future_information_used": False,
        "historical_outcome_used": False,
        "opportunity_quality_hash": f"test-{symbol}-{quality}",
    }
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": current_position,
        "target_weight": 0.1,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
    row.update(competitor_fields)
    return row


def _record(competition: dict, symbol: str) -> dict:
    for item in competition["market_candidate_cash_interaction"]["interaction_results"]:
        if item["symbol"] == symbol:
            return item
    raise AssertionError(f"missing interaction result for {symbol}")


def _result(competition: dict, symbol: str) -> str:
    return _record(competition, symbol)["interaction_result"]


def _cash_wins(competition: dict) -> bool:
    return competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
