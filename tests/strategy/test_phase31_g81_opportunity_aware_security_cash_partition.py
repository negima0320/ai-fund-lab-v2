from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-08-24"


def test_phase31_g81_cash_preferred_rows_defer_to_optional_cash() -> None:
    competition = _competition(
        [
            _new("14910", weight=0.155596, quality="COMPARABLE_MARGINAL", score=0.31),
            _new("71270", weight=0.075019, quality="COMPARABLE_MARGINAL", score=0.28),
            _new("94340", weight=0.020537, quality="COMPARABLE_MARGINAL", score=0.24),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.298642,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    deferrals = shadow["cash_preferred_security_deferrals"]

    assert shadow["security_allocations"] == []
    assert shadow["cash_preferred_security_deferral_count"] == 3
    assert {row["symbol"] for row in deferrals} == {"14910", "71270", "94340"}
    assert all(row["interaction_result"] == "CASH_PREFERRED" for row in deferrals)
    assert all(row["authorized_allocation_weight"] == 0.0 for row in deferrals)
    assert all(row["requested_allocation_weight"] > 0 for row in deferrals)
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.298642
    assert shadow["unallocated_residual"] == 0.0
    assert shadow["capital_conservation"]["status"] == "PASS"
    assert "CASH_PREFERRED_BINDING_AT_FINAL_ALLOCATION" in shadow["reason_codes"]


def test_phase31_g81_cash_preferred_tail_does_not_consume_security_sleeve() -> None:
    competition = _competition(
        [
            _new("44440", weight=0.07, quality="STRONG", score=0.92),
            _new("14910", weight=0.05, quality="COMPARABLE_MARGINAL", score=0.31),
            _new("71270", weight=0.04, quality="COMPARABLE_MARGINAL", score=0.28),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.20,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocations = shadow["security_allocations"]
    deferrals = shadow["cash_preferred_security_deferrals"]

    assert [row["symbol"] for row in allocations] == ["44440"]
    assert allocations[0]["interaction_result"] == "SELECTIVE_COMPETITION"
    assert shadow["cash_preferred_security_deferral_count"] == 2
    assert {row["symbol"] for row in deferrals} == {"14910", "71270"}
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.13
    assert shadow["weak_tail_positive_allocation_preserved_when_cash_preferred"] is False
    assert shadow["lower_priority_implicit_promotion"] is False


def test_phase31_g81_normal_marginal_participation_is_not_blanket_blocked() -> None:
    competition = _competition(
        [
            _new("20010", weight=0.05, quality="COMPARABLE_MARGINAL", score=0.77),
            _new("20020", weight=0.04, quality="COMPARABLE_MARGINAL", score=0.75),
        ],
        intent="NORMAL_DEPLOYMENT",
        available_budget=0.15,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert {row["symbol"] for row in shadow["security_allocations"]} == {"20010", "20020"}
    assert all(row["interaction_result"] == "DEPLOY_ELIGIBLE" for row in shadow["security_allocations"])
    assert shadow["cash_preferred_security_deferral_count"] == 0
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.06
    assert shadow["candidate_eligibility_mutation_count"] == 0


def test_phase31_g81_add_and_selective_competition_are_preserved() -> None:
    competition = _competition(
        [
            _add("40520", weight=0.03, quality="STRONG", score=0.84),
            _new("59350", weight=0.04, quality="STRONG", score=0.80),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.10,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocations = shadow["security_allocations"]

    assert {row["competitor_type"] for row in allocations} == {"ADD", "NEW_BUY"}
    assert all(row["interaction_result"] == "SELECTIVE_COMPETITION" for row in allocations)
    assert shadow["add_shared_budget"] is True
    assert shadow["cash_preferred_security_deferral_count"] == 0
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.03
    assert shadow["position_sizing_behavior_change_count"] == 0
    assert shadow["runtime_order_change_count"] == 0


def _competition(
    members: list[dict[str, object]],
    *,
    intent: str,
    available_budget: float,
) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.30,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(intent),
    )


def _risk(intent: str) -> dict[str, object]:
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": "SHORT_TERM_BREADTH_BREAKDOWN"
            if intent == "CAUTIOUS_DEPLOYMENT"
            else "HEALTHY_EXPANSION",
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
            "bootstrap_or_residual_cash_state": "RESIDUAL_OPTIONALITY_CASH",
            "trading_consumer_connected": False,
            "envelope_hash": f"test-g81-{intent}",
        },
    }


def _new(symbol: str, *, weight: float, quality: str, score: float) -> dict[str, object]:
    return {
        **_base(symbol, quality=quality, score=score),
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
    }


def _add(symbol: str, *, weight: float, quality: str, score: float) -> dict[str, object]:
    return {
        **_base(symbol, quality=quality, score=score),
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "current_weight": 0.05,
        "target_weight": round(0.05 + weight, 6),
        "accepted_incremental_weight": weight,
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
    }


def _base(symbol: str, *, quality: str, score: float) -> dict[str, object]:
    evidence = {
        "schema_version": "opportunity_quality.v1",
        "business_date": BUSINESS_DATE,
        "as_of_business_date": BUSINESS_DATE,
        "symbol": symbol,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "opportunity_quality_reason_codes": [f"test_{quality.lower()}"],
        "evidence_completeness": "COMPLETE",
        "future_information_used": False,
        "historical_outcome_used": False,
        "opportunity_quality_hash": f"test-g81-{symbol}-{quality}",
    }
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": int(symbol[:2]),
        "opportunity_buy_rank": int(symbol[:2]),
        "runtime_opportunity_score": score,
        "runtime_opportunity_score_authority": {
            "authority": "OPPORTUNITY_RANKING_AUTHORITY",
            "canonical_field": "runtime_opportunity_score",
            "prediction_semantics": "runtime_opportunity_score",
        },
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": int(symbol[:2]),
            "marginal_capital_value_class": "ELIGIBLE_STRONG" if quality == "STRONG" else "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
