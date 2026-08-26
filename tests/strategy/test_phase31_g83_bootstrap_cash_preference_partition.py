from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-08-25"


def test_phase31_g83_bootstrap_cash_preferred_allows_reduced_participation() -> None:
    competition = _competition(
        [
            _new("94340", weight=0.033636, quality="COMPARABLE_MARGINAL", score=0.24),
            _new("37820", weight=0.033636, quality="COMPARABLE_MARGINAL", score=-0.16),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.10,
        cash_state="EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP",
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert shadow["bootstrap_cash_preferred_participation_allowed"] is True
    assert shadow["bootstrap_cash_preferred_participation_count"] == 2
    assert shadow["security_allocation_count"] == 2
    assert shadow["cash_preferred_security_deferral_count"] == 0
    assert all(row["interaction_result"] == "CASH_PREFERRED" for row in shadow["security_allocations"])
    assert all(row["bootstrap_reduced_risk_participation"] is True for row in shadow["security_allocations"])
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g83_already_deployed_cash_preferred_still_defers_weak_tail() -> None:
    competition = _competition(
        [
            _new("14910", weight=0.075, quality="COMPARABLE_MARGINAL", score=-0.56),
            _new("47070", weight=0.0205, quality="COMPARABLE_MARGINAL", score=-0.59),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.15,
        cash_state="RESIDUAL_OPTIONALITY_CASH",
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["bootstrap_cash_preferred_participation_allowed"] is False
    assert shadow["security_allocations"] == []
    assert shadow["cash_preferred_security_deferral_count"] == 2
    assert all(row["authorized_allocation_weight"] == 0.0 for row in shadow["cash_preferred_security_deferrals"])
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.15
    assert shadow["weak_tail_positive_allocation_preserved_when_cash_preferred"] is False
    assert shadow["lower_priority_implicit_promotion"] is False


def test_phase31_g83_no_valid_bootstrap_opportunity_remains_cash() -> None:
    competition = _competition(
        [_new("40010", weight=0.0, quality="INSUFFICIENT", score=-1.0)],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.10,
        cash_state="EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP",
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["bootstrap_cash_preferred_participation_allowed"] is False
    assert shadow["security_allocations"] == []
    assert shadow["cash_preferred_security_deferrals"] == []
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.10
    assert shadow["capital_conservation"]["status"] == "PASS"


def _competition(
    members: list[dict[str, object]],
    *,
    intent: str,
    available_budget: float,
    cash_state: str,
) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.30,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(intent, cash_state=cash_state),
    )


def _risk(intent: str, *, cash_state: str) -> dict[str, object]:
    return {
        "risk_pacing_intent": intent,
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
            "bootstrap_or_residual_cash_state": cash_state,
            "trading_consumer_connected": False,
            "envelope_hash": f"test-g83-{intent}-{cash_state}",
            "reason_codes": [
                "CAPITAL_BUDGET_STATE_SELECTIVE_DEPLOYMENT_CAPACITY",
                f"CASH_STATE_{cash_state}",
                "DEPLOYMENT_INTENSITY_NOT_SECURITY_ADMISSION",
                "EXPLORATION_PARTICIPATION_RISK_PRESERVED",
                "PROFIT_ENGINE_PRESERVATION_CONTEXT",
                "RISK_PACING_CAUTIOUS",
            ],
        },
    }


def _new(symbol: str, *, weight: float, quality: str, score: float) -> dict[str, object]:
    return {
        **_base(symbol, quality=quality, score=score),
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE" if weight > 0 else "EXCLUDE",
        "pm_action": "NEW" if weight > 0 else "",
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
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
        "opportunity_quality_hash": f"test-g83-{symbol}-{quality}",
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
            "marginal_capital_value_class": "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
