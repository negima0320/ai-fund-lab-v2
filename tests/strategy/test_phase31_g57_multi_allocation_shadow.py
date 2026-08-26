from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-07-15"


def test_phase31_g57_normal_multiple_security_and_cash_shadow_allocation() -> None:
    competition = _competition(
        [
            _new("10010", weight=0.08, quality="STRONG"),
            _new("10020", weight=0.06, quality="COMPARABLE_HIGH"),
        ],
        "NORMAL_DEPLOYMENT",
        available_budget=0.20,
        total_target_weight=0.14,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["schema_version"] == "canonical_multi_allocation_deployment_set.v1"
    assert shadow["authority_status"] == "SHADOW_NON_AUTHORITATIVE"
    assert shadow["status"] == "PASS"
    assert len(shadow["security_allocations"]) == 2
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert shadow["capital_conservation"]["status"] == "PASS"
    assert shadow["single_winner_general_contract"] is False
    assert shadow["cash_winner_takes_all_contract"] is False
    assert competition["canonical_deployment_set"]["cardinality_contract"] == "SINGLE"
    assert shadow["position_sizing_behavior_change_count"] == 0
    assert shadow["runtime_order_change_count"] == 0


def test_phase31_g57_cautious_marginal_is_not_automatic_zero_and_can_share_with_cash() -> None:
    competition = _competition(
        [
            _new("20010", weight=0.05, quality="COMPARABLE_MARGINAL"),
            _new("20020", weight=0.04, quality="COMPARABLE_MARGINAL"),
        ],
        "CAUTIOUS_DEPLOYMENT",
        available_budget=0.15,
        total_target_weight=0.09,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    deferrals = shadow["cash_preferred_security_deferrals"]
    symbols = {item["symbol"] for item in deferrals}

    assert competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert shadow["cautious_marginal_automatic_zero"] is False
    assert shadow["security_allocations"] == []
    assert shadow["cash_preferred_security_deferral_count"] == 2
    assert symbols == {"20010", "20020"}
    assert all(item["interaction_result"] == "CASH_PREFERRED" for item in deferrals)
    assert all(item["authorized_allocation_weight"] == 0.0 for item in deferrals)
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.15
    assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g57_cautious_strong_and_bootstrap_participation_supported() -> None:
    competition = _competition(
        [_new("30010", weight=0.07, quality="STRONG")],
        "CAUTIOUS_DEPLOYMENT",
        available_budget=0.12,
        total_target_weight=0.07,
        capacity_state="CAUTIOUS_BOOTSTRAP_CAPACITY",
        cash_state="BOOTSTRAP_CASH",
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["bootstrap_participation_supported"] is True
    assert shadow["security_allocations"][0]["symbol"] == "30010"
    assert shadow["security_allocations"][0]["authorized_allocation_weight"] > 0
    assert shadow["budget_envelope"]["bootstrap_or_residual_cash_state"] == "BOOTSTRAP_CASH"
    assert shadow["trading_consumer_connected"] is False


def test_phase31_g57_no_valid_opportunities_can_allocate_all_cash() -> None:
    competition = _competition(
        [_new("40010", weight=0.0, quality="INSUFFICIENT")],
        "NORMAL_DEPLOYMENT",
        available_budget=0.10,
        total_target_weight=0.0,
        target_gross_exposure=0.10,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["security_allocations"] == []
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.10
    assert shadow["capital_conservation"]["allocated_plus_cash_plus_residual"] == 0.10
    assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g57_add_and_reentry_share_budget_without_trading_authority() -> None:
    competition = _competition(
        [
            _add("50010", weight=0.05, quality="STRONG"),
            _new("50020", weight=0.04, quality="COMPARABLE_HIGH"),
        ],
        "NORMAL_DEPLOYMENT",
        available_budget=0.12,
        total_target_weight=0.14,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    types = {item["competitor_type"] for item in shadow["security_allocations"]}

    assert types == {"ADD", "NEW_BUY"}
    assert shadow["add_shared_budget"] is True
    assert shadow["reentry_shared_budget"] is True
    assert shadow["new_buy_shared_budget"] is True
    assert shadow["authoritative_consumer_count"] == 0
    assert shadow["single_path_remains_only_authoritative_trading_path"] is True
    assert competition["authority"]["dual_capital_authority"] is False


def test_phase31_g57_missing_or_malformed_budget_envelope_fail_closed_shadow_only() -> None:
    missing = build_capital_competition_framework(
        members=[_new("60010", weight=0.05, quality="STRONG")],
        target_gross_exposure=0.1,
        total_target_weight=0.05,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk("NORMAL_DEPLOYMENT", include_envelope=False),
    )
    malformed = build_capital_competition_framework(
        members=[_new("60020", weight=0.05, quality="STRONG")],
        target_gross_exposure=0.1,
        total_target_weight=0.05,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence={
            **_risk("NORMAL_DEPLOYMENT"),
            "incremental_capital_budget_envelope": {
                **_envelope(),
                "authority_status": "EVIDENCE_ONLY_NON_AUTHORITATIVE",
            },
        },
    )

    assert missing["canonical_multi_allocation_deployment_set"]["status"] == "FAIL_CLOSED"
    assert malformed["canonical_multi_allocation_deployment_set"]["status"] == "FAIL_CLOSED"
    assert missing["capital_competition_winner_symbol"] == "60010"
    assert malformed["capital_competition_winner_symbol"] == "60020"


def _competition(
    members: list[dict[str, object]],
    intent: str,
    *,
    available_budget: float,
    total_target_weight: float,
    target_gross_exposure: float = 0.20,
    capacity_state: str = "NORMAL_DEPLOYMENT_CAPACITY",
    cash_state: str = "RESIDUAL_CASH",
) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=target_gross_exposure,
        total_target_weight=total_target_weight,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(intent, capacity_state=capacity_state, cash_state=cash_state),
    )


def _risk(
    intent: str,
    *,
    capacity_state: str = "NORMAL_DEPLOYMENT_CAPACITY",
    cash_state: str = "RESIDUAL_CASH",
    include_envelope: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": "HEALTHY_EXPANSION",
            "market_quality_evidence_completeness": "COMPLETE",
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }
    if include_envelope:
        payload["incremental_capital_budget_envelope"] = _envelope(
            capacity_state=capacity_state,
            cash_state=cash_state,
        )
    return payload


def _envelope(
    *,
    capacity_state: str = "NORMAL_DEPLOYMENT_CAPACITY",
    cash_state: str = "RESIDUAL_CASH",
) -> dict[str, object]:
    return {
        "schema_version": "incremental_capital_budget_envelope.v1",
        "owner": "PORTFOLIO_POLICY",
        "authority_status": "AUTHORITATIVE",
        "business_date": BUSINESS_DATE,
        "market_quality_as_of": BUSINESS_DATE,
        "risk_pacing_as_of": BUSINESS_DATE,
        "deployment_capacity_semantic": capacity_state,
        "bootstrap_or_residual_cash_state": cash_state,
        "trading_consumer_connected": False,
        "envelope_hash": f"test-envelope-{capacity_state}-{cash_state}",
    }


def _new(symbol: str, *, weight: float, quality: str) -> dict[str, object]:
    return {
        **_base(symbol, quality=quality),
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
    }


def _add(symbol: str, *, weight: float, quality: str) -> dict[str, object]:
    return {
        **_base(symbol, quality=quality),
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


def _base(symbol: str, *, quality: str) -> dict[str, object]:
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
        "opportunity_quality_hash": f"test-{symbol}-{quality}",
    }
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": int(symbol[:2]),
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
