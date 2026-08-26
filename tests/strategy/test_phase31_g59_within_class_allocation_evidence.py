from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-07-16"


def test_phase31_g59_within_class_runtime_edge_priority_is_preserved_without_rank_mutation() -> None:
    competition = _competition(
        [
            _new("71010", weight=0.04, quality="COMPARABLE_MARGINAL", score=0.42),
            _new("71020", weight=0.04, quality="COMPARABLE_MARGINAL", score=0.81),
            _new("71030", weight=0.04, quality="COMPARABLE_MARGINAL", score=0.64),
        ],
        available_budget=0.14,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocations = shadow["security_allocations"]

    assert shadow["within_class_differentiation_supported"] is True
    assert shadow["candidate_rank_authority_mutation"] is False
    assert shadow["candidate_rank_authority_mutation_count"] == 0
    assert shadow["comparable_marginal_equal_weight_collapse"] is False
    assert [item["symbol"] for item in allocations] == ["71020", "71030", "71010"]
    assert [item["within_class_allocation_rank"] for item in allocations] == [1, 2, 3]
    assert [item["within_class_allocation_evidence"]["runtime_opportunity_score"] for item in allocations] == [
        0.81,
        0.64,
        0.42,
    ]
    assert all(
        item["within_class_allocation_evidence"]["candidate_rank_authority_mutated"] is False
        for item in allocations
    )


def test_phase31_g59_stronger_quality_and_add_priority_evidence_survive_shadow_allocation() -> None:
    competition = _competition(
        [
            _new("72010", weight=0.03, quality="COMPARABLE_MARGINAL", score=0.88),
            _new("72020", weight=0.03, quality="STRONG", score=0.61),
            _add("72030", weight=0.03, quality="COMPARABLE_HIGH", score=0.74),
        ],
        available_budget=0.12,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocations = shadow["security_allocations"]

    assert [item["symbol"] for item in allocations] == ["72020", "72030", "72010"]
    assert shadow["stronger_edge_capital_priority_preserved"] is True
    assert shadow["add_shared_budget"] is True
    assert shadow["reentry_shared_budget"] is True
    assert {item["competitor_type"] for item in allocations} == {"NEW_BUY", "ADD"}
    assert shadow["capital_conservation"]["status"] == "PASS"
    assert competition["canonical_deployment_set"]["cardinality_contract"] == "SINGLE"
    assert shadow["position_sizing_behavior_change_count"] == 0
    assert shadow["runtime_order_change_count"] == 0


def test_phase31_g59_cash_security_coexistence_and_market_quality_context_only() -> None:
    competition = _competition(
        [
            _new("73010", weight=0.05, quality="STRONG", score=0.77),
            _new("73020", weight=0.04, quality="STRONG", score=0.75),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        market_quality_state="SHORT_TERM_BREADTH_BREAKDOWN",
        available_budget=0.15,
        target_gross_exposure=0.18,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert competition["capital_competition_winner_type"] == "NEW_BUY"
    assert len(shadow["security_allocations"]) == 2
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert shadow["cash_winner_takes_all_contract"] is False
    assert shadow["single_winner_general_contract"] is False
    assert shadow["future_input_count"] == 0
    assert shadow["historical_outcome_input_count"] == 0


def _competition(
    members: list[dict[str, object]],
    *,
    available_budget: float,
    intent: str = "NORMAL_DEPLOYMENT",
    market_quality_state: str = "HEALTHY_EXPANSION",
    target_gross_exposure: float = 0.16,
) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=target_gross_exposure,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(intent, market_quality_state=market_quality_state),
    )


def _risk(intent: str, *, market_quality_state: str) -> dict[str, object]:
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": market_quality_state,
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
            "deployment_capacity_semantic": "ELEVATED_DEPLOYMENT_CAPACITY",
            "bootstrap_or_residual_cash_state": "RESIDUAL_OPTIONALITY_CASH",
            "trading_consumer_connected": False,
            "envelope_hash": f"test-g59-{intent}-{market_quality_state}",
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
        "opportunity_quality_hash": f"test-g59-{symbol}-{quality}",
    }
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": 10,
        "opportunity_buy_rank": 10,
        "runtime_opportunity_score": score,
        "runtime_opportunity_score_authority": {
            "authority": "OPPORTUNITY_RANKING_AUTHORITY",
            "canonical_field": "runtime_opportunity_score",
            "prediction_semantics": "runtime_opportunity_score",
        },
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": 10,
            "marginal_capital_value_class": "ELIGIBLE_STRONG" if quality == "STRONG" else "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
