from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import (
    apply_lot_aware_final_reallocation,
    build_capital_competition_framework,
)


BUSINESS_DATE = "2022-08-19"


def test_phase31_g44_add_binding_mandatory_cases() -> None:
    cautious_strong = _competition([_add("11110", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    cautious_marginal = _competition([_add("11120", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")
    gradual_high = _competition([_add("11130", quality="COMPARABLE_HIGH")], "GRADUAL_REDEPLOYMENT")
    gradual_marginal = _competition([_add("11140", quality="COMPARABLE_MARGINAL")], "GRADUAL_REDEPLOYMENT")
    weak_cautious = _competition([_add("11150", quality="WEAK_VALID")], "CAUTIOUS_DEPLOYMENT")

    assert cautious_strong["capital_competition_winner_type"] == "ADD"
    assert _cash_wins(cautious_marginal)
    assert gradual_high["capital_competition_winner_type"] == "ADD"
    assert _record(gradual_high, "11130")["interaction_result"] == "SELECTIVE_COMPETITION"
    assert _cash_wins(gradual_marginal)
    assert _cash_wins(weak_cautious)
    assert _record(cautious_strong, "11110")["canonical_opportunity_quality_class"] == "STRONG"
    assert _record(cautious_marginal, "11120")["binding_reason_codes"] == [
        "CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED",
        "CAUTIOUS_MARGINAL_LOST_TO_CASH",
    ]


def test_phase31_g44_add_new_buy_cash_true_competition() -> None:
    strong_new = _competition(
        [_new("22210", quality="STRONG", preserve_exception=True), _add("22220", quality="COMPARABLE_MARGINAL")],
        "CAUTIOUS_DEPLOYMENT",
    )
    strong_add = _competition(
        [_add("22230", quality="STRONG", preserve_exception=True), _new("22240", quality="COMPARABLE_MARGINAL")],
        "CAUTIOUS_DEPLOYMENT",
    )
    both_marginal = _competition(
        [_add("22250", quality="COMPARABLE_MARGINAL"), _new("22260", quality="COMPARABLE_MARGINAL")],
        "CAUTIOUS_DEPLOYMENT",
    )

    assert strong_new["capital_competition_winner_type"] == "NEW_BUY"
    assert strong_new["capital_competition_winner_symbol"] == "22210"
    assert strong_add["capital_competition_winner_type"] == "ADD"
    assert strong_add["capital_competition_winner_symbol"] == "22230"
    assert _cash_wins(both_marginal)
    assert strong_new["authority"]["add_automatic_priority"] is False
    assert strong_new["authority"]["new_buy_automatic_priority"] is False


def test_phase31_g44_reentry_uses_standard_buy_new_matrix() -> None:
    normal = _competition([_reentry("33310", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT")
    cautious = _competition([_reentry("33310", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")
    cautious_strong = _competition([_reentry("33320", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    blocked = _competition([_reentry("33330", quality="BLOCKED", target_weight=0.0, accepted_buy_new_weight=0.0)], "NORMAL_DEPLOYMENT")

    assert normal["capital_competition_winner_type"] == "NEW_BUY"
    assert normal["capital_competition_winner_symbol"] == "33310"
    assert _cash_wins(cautious)
    assert cautious_strong["capital_competition_winner_symbol"] == "33320"
    assert _record(blocked, "33330")["interaction_result"] == "BLOCKED"
    assert _record(normal, "33310")["competitor_type"] == "NEW_BUY"
    assert _record(normal, "33310")["canonical_opportunity_quality_class"] == "COMPARABLE_MARGINAL"


def test_phase31_g44_lot_reconsideration_security_a_infeasible_security_b_wins() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _new("44410", quality="STRONG", preserve_exception=True, priority=1, target_weight=0.18, accepted_buy_new_weight=0.18),
            _new("44420", quality="STRONG", preserve_exception=True, priority=2, target_weight=0.08, accepted_buy_new_weight=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "44410", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "canonical_sizing_evidence": _sizing("44410", "LOT_INFEASIBLE")},
            {"symbol": "44420", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08, "canonical_sizing_evidence": _sizing("44420", "EXECUTABLE")},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing("NORMAL_DEPLOYMENT"),
    )

    competition = result["evidence"]["capital_competition"]
    integration = result["evidence"]["lot_reconsideration_binding_integration"]

    assert result["members"][0]["lot_aware_accepted_buy_new_weight"] == 0.0
    assert result["members"][1]["lot_aware_accepted_buy_new_weight"] == 0.08
    assert competition["capital_competition_winner_symbol"] == "44420"
    assert integration["canonical_g43_binding_matrix_reused"] is True
    assert integration["cash_present_during_reconsideration"] is True
    assert integration["forces_security_deployment"] is False
    assert integration["second_discrete_quantity_engine_created"] is False
    assert integration["g43_binding_matrix_bypass_count"] == 0


def test_phase31_g44_lot_reconsideration_cash_can_win_after_infeasible_security() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _new("44510", quality="STRONG", preserve_exception=True, priority=1, target_weight=0.18, accepted_buy_new_weight=0.18),
            _new("44520", quality="COMPARABLE_MARGINAL", priority=2, target_weight=0.08, accepted_buy_new_weight=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "44510", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "canonical_sizing_evidence": _sizing("44510", "LOT_INFEASIBLE")},
            {"symbol": "44520", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08, "canonical_sizing_evidence": _sizing("44520", "EXECUTABLE")},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing("CAUTIOUS_DEPLOYMENT"),
    )

    competition = result["evidence"]["capital_competition"]
    skipped_reasons = {str(row.get("reason") or "") for row in result["evidence"]["skipped"]}

    assert result["members"][0]["lot_aware_accepted_buy_new_weight"] == 0.0
    assert result["members"][1]["lot_aware_accepted_buy_new_weight"] == 0.08
    assert _record(competition, "44520")["interaction_result"] == "CASH_PREFERRED"
    assert "g43_binding_cash_preferred" not in skipped_reasons
    assert result["evidence"]["lot_reconsideration_binding_integration"]["residual_capital_binding_bypass_count"] == 0


def test_phase31_g44_add_lot_infeasible_reconsiders_new_buy_or_cash() -> None:
    new_buy_wins = apply_lot_aware_final_reallocation(
        members=[
            _add("44610", quality="STRONG", preserve_exception=True, priority=1, target_weight=0.18, accepted_incremental_weight=0.13),
            _new("44620", quality="STRONG", preserve_exception=True, priority=2, target_weight=0.08, accepted_buy_new_weight=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "44610", "intent_type": "BUY_ADD", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "canonical_sizing_evidence": _sizing("44610", "LOT_INFEASIBLE")},
            {"symbol": "44620", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08, "canonical_sizing_evidence": _sizing("44620", "EXECUTABLE")},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing("NORMAL_DEPLOYMENT"),
    )
    cash_wins = apply_lot_aware_final_reallocation(
        members=[
            _add("44710", quality="STRONG", preserve_exception=True, priority=1, target_weight=0.18, accepted_incremental_weight=0.13),
            _new("44720", quality="COMPARABLE_MARGINAL", priority=2, target_weight=0.08, accepted_buy_new_weight=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "44710", "intent_type": "BUY_ADD", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "canonical_sizing_evidence": _sizing("44710", "LOT_INFEASIBLE")},
            {"symbol": "44720", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08, "canonical_sizing_evidence": _sizing("44720", "EXECUTABLE")},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing("CAUTIOUS_DEPLOYMENT"),
    )

    assert new_buy_wins["evidence"]["capital_competition"]["capital_competition_winner_symbol"] == "44620"
    assert cash_wins["evidence"]["capital_competition"]["capital_competition_winner_type"] == "CASH_OPTIONALITY"


def _competition(members: list[dict], intent: str) -> dict:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.3,
        total_target_weight=0.1,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing(intent),
    )


def _risk_pacing(intent: str) -> dict:
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": "HEALTHY_EXPANSION",
            "market_quality_evidence_completeness": "COMPLETE",
            "market_quality_reason_codes": ["HEALTHY_EXPANSION"],
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }


def _new(symbol: str, *, quality: str, priority: int = 1, target_weight: float = 0.1, accepted_buy_new_weight: float = 0.1, preserve_exception: bool = False) -> dict:
    return _member(
        symbol,
        quality=quality,
        current_position=False,
        priority=priority,
        target_weight=target_weight,
        fields={"membership_intent": "ADD_CANDIDATE", "accepted_buy_new_weight": accepted_buy_new_weight},
        preserve_exception=preserve_exception,
    )


def _reentry(symbol: str, *, quality: str, target_weight: float = 0.1, accepted_buy_new_weight: float = 0.1, preserve_exception: bool = False) -> dict:
    row = _new(symbol, quality=quality, target_weight=target_weight, accepted_buy_new_weight=accepted_buy_new_weight, preserve_exception=preserve_exception)
    row.update(
        {
            "semantic_buy_type": "REENTRY",
            "reentry_semantic_status": "PASS" if quality != "BLOCKED" else "FAIL_CLOSED",
            "reentry_semantic_state": "REENTRY_ELIGIBLE" if quality != "BLOCKED" else "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE",
        }
    )
    return row


def _add(symbol: str, *, quality: str, priority: int = 1, target_weight: float = 0.15, accepted_incremental_weight: float = 0.1, preserve_exception: bool = False) -> dict:
    return _member(
        symbol,
        quality=quality,
        current_position=True,
        priority=priority,
        target_weight=target_weight,
        fields={
            "pm_action": "ADD",
            "current_weight": 0.05,
            "accepted_incremental_weight": accepted_incremental_weight,
            "expected_edge_improvement_state": "IMPROVING",
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
            "add_allocation_eligibility_status": "PASS",
            "same_campaign_continuation_status": "CONTINUING",
        },
        preserve_exception=preserve_exception,
    )


def _member(
    symbol: str,
    *,
    quality: str,
    current_position: bool,
    priority: int,
    target_weight: float,
    fields: dict,
    preserve_exception: bool,
) -> dict:
    reasons = [f"test_{quality.lower()}"]
    if preserve_exception:
        reasons.append("OPPORTUNITY_QUALITY_EXPLICIT_POSITIVE_ADD_EVIDENCE")
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
        "source_evidence": {},
        "future_information_used": False,
        "historical_outcome_used": False,
        "opportunity_quality_hash": f"test-{symbol}-{quality}",
    }
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": current_position,
        "construction_priority": priority,
        "target_weight": target_weight,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
    row.update(fields)
    return row


def _sizing(symbol: str, evidence_class: str) -> dict:
    terminality = "RECONSIDERABLE" if evidence_class == "LOT_INFEASIBLE" else "EXECUTABLE"
    return {
        "schema_version": "position_sizing.canonical_lot_residual_evidence.v1",
        "symbol": symbol,
        "evidence_class": evidence_class,
        "terminality": terminality,
        "executable_quantity": 0 if evidence_class == "LOT_INFEASIBLE" else 100,
        "constraint_reason_codes": [evidence_class],
        "quantity_authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
    }


def _record(competition: dict, symbol: str) -> dict:
    for item in competition["market_candidate_cash_interaction"]["interaction_results"]:
        if item["symbol"] == symbol:
            return item
    raise AssertionError(f"missing interaction result for {symbol}")


def _cash_wins(competition: dict) -> bool:
    return competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
