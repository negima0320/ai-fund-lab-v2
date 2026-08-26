from __future__ import annotations

from ai_fund_lab_v2.strategy.portfolio_construction import (
    build_capital_competition_framework,
    promote_final_portfolio_construction_for_production,
)


BUSINESS_DATE = "2026-08-23"


def test_phase31_g61_blocks_lower_priority_implicit_promotion_after_lot_conversion() -> None:
    competition = _competition(
        [
            _new("90010", weight=0.04, quality="STRONG", score=0.90),
            _new("90020", weight=0.04, quality="COMPARABLE_HIGH", score=0.70),
            _new("90030", weight=0.04, quality="COMPARABLE_MARGINAL", score=0.60),
        ],
        available_budget=0.14,
        lot_context={
            "portfolio_value": 1_000_000,
            "trading_unit": 100,
            "single_name_cap": 0.30,
            "symbols": {
                "90010": {"reference_price": 1_200},
                "90020": {"reference_price": 200},
                "90030": {"reference_price": 180},
            },
        },
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    compatibility = shadow["lot_aware_allocation_to_sizing_compatibility"]
    rows = compatibility["compatibility_rows"]

    assert [row["symbol"] for row in rows] == ["90010", "90020", "90030"]
    assert rows[0]["compatibility_state"] == "LOT_INFEASIBLE_RESIDUAL_REQUIRED"
    assert rows[1]["executable_before_residual_reallocation"] is True
    assert rows[1]["lower_priority_execution_requires_explicit_residual_resolution"] is True
    assert rows[1]["implicit_priority_promotion_allowed"] is False
    assert compatibility["priority_inversion_detected_raw"] is True
    assert compatibility["priority_inversion_after_compatibility"] is False
    assert compatibility["lower_priority_implicit_promotion_allowed"] is False
    assert compatibility["residual_capital_explicit"] is True
    assert shadow["lot_aware_priority_inversion"] is False
    assert shadow["lower_priority_implicit_promotion"] is False
    assert shadow["top_priority_preservation_materially_improved"] is True
    assert shadow["position_sizing_behavior_change_count"] == 0
    assert shadow["runtime_order_change_count"] == 0


def test_phase31_g61_preserves_ps_quantity_authority_and_add_compatibility() -> None:
    competition = _competition(
        [
            _add("91010", weight=0.03, quality="COMPARABLE_HIGH", score=0.72),
            _new("91020", weight=0.03, quality="COMPARABLE_MARGINAL", score=0.68),
        ],
        available_budget=0.08,
        lot_context={
            "portfolio_value": 1_000_000,
            "trading_unit": 100,
            "single_name_cap": 0.30,
            "symbols": {
                "91010": {"reference_price": 250, "current_weight": 0.05},
                "91020": {"reference_price": 220},
            },
        },
    )

    compatibility = competition["canonical_multi_allocation_deployment_set"][
        "lot_aware_allocation_to_sizing_compatibility"
    ]

    assert compatibility["add_compatibility"] == "PASS"
    assert compatibility["capital_conservation"]["status"] == "PASS"
    assert compatibility["executable_multi_security"] is True
    assert compatibility["all_zero_collapse"] is False
    assert all(row["position_sizing_quantity_authority_preserved"] is True for row in compatibility["compatibility_rows"])
    assert all(row["pc_quantity_authority"] is False for row in compatibility["compatibility_rows"])
    assert competition["canonical_deployment_set"]["cardinality_contract"] == "SINGLE"


def test_phase31_g61_missing_lot_context_fails_closed_without_trading_behavior_change() -> None:
    competition = _competition(
        [_new("92010", weight=0.04, quality="STRONG", score=0.80)],
        available_budget=0.05,
        lot_context={},
    )

    compatibility = competition["canonical_multi_allocation_deployment_set"][
        "lot_aware_allocation_to_sizing_compatibility"
    ]
    row = compatibility["compatibility_rows"][0]

    assert row["compatibility_state"] == "INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED"
    assert compatibility["priority_inversion_after_compatibility"] is False
    assert compatibility["runtime_order_change_count"] == 0
    assert compatibility["position_sizing_behavior_change_count"] == 0


def test_phase31_g65_g61_consumes_existing_member_lot_resolution_context() -> None:
    member = _new("94340", weight=0.033636, quality="COMPARABLE_MARGINAL", score=0.24)
    member["reference_price"] = 144.1
    member["target_weight_authority"] = {
        "lot_aware_final_reallocation": {
            "phase29_l19_lot_resolution": {
                "one_lot_weight": 0.01441,
                "one_lot_quantity": 100,
                "safety_hard_cap_weight": 0.25,
                "strategy_cap_weight": 0.18,
                "current_weight": 0.0,
                "executable_quantity_delta": 200,
            }
        }
    }

    competition = _competition(
        [member],
        available_budget=0.74,
        lot_context={},
    )

    compatibility = competition["canonical_multi_allocation_deployment_set"][
        "lot_aware_allocation_to_sizing_compatibility"
    ]
    row = compatibility["compatibility_rows"][0]

    assert compatibility["all_zero_collapse"] is False
    assert compatibility["lot_executable_count"] == 1
    assert row["compatibility_state"] == "LOT_EXECUTABLE_COMPATIBLE"
    assert row["minimum_executable_weight"] == 0.01441
    assert row["cap_headroom_weight"] == 0.25
    assert row["projected_quantity_delta_evidence_only"] == 200
    assert row["position_sizing_quantity_authority_preserved"] is True
    assert row["pc_quantity_authority"] is False


def test_phase31_g66_production_publishes_lot_aware_competition_top_level() -> None:
    pre_lot = _competition(
        [_new("94340", weight=0.033636, quality="COMPARABLE_MARGINAL", score=0.24)],
        available_budget=0.74,
        lot_context={},
    )
    lot_aware = _competition(
        [_g65_lot_resolved_new("94340", weight=0.033636)],
        available_budget=0.74,
        lot_context={},
    )

    promoted = promote_final_portfolio_construction_for_production(
        {
            "producer_result_status": "PASS",
            "reason_codes": [],
            "capital_competition": pre_lot,
            "lot_aware_final_reallocation": {
                "status": "PASS",
                "capital_competition": lot_aware,
            },
        }
    )

    top_level_g61 = promoted["capital_competition"]["canonical_multi_allocation_deployment_set"][
        "lot_aware_allocation_to_sizing_compatibility"
    ]
    previous_g61 = promoted["pre_lot_capital_competition"]["canonical_multi_allocation_deployment_set"][
        "lot_aware_allocation_to_sizing_compatibility"
    ]

    assert promoted["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert top_level_g61["lot_executable_count"] == 1
    assert top_level_g61["compatibility_rows"][0]["compatibility_state"] == "LOT_EXECUTABLE_COMPATIBLE"
    assert previous_g61["compatibility_rows"][0]["compatibility_state"] == "INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED"
    assert "G66_LOT_AWARE_MULTI_ALLOCATION_PUBLISHED_TOP_LEVEL" in promoted["reason_codes"]


def _competition(
    members: list[dict[str, object]],
    *,
    available_budget: float,
    lot_context: dict[str, object],
) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.20,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        lot_sizing_context_evidence=lot_context,
        risk_pacing_evidence=_risk(),
    )


def _risk() -> dict[str, object]:
    return {
        "risk_pacing_intent": "NORMAL_DEPLOYMENT",
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
            "envelope_hash": "test-g61-envelope",
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


def _g65_lot_resolved_new(symbol: str, *, weight: float) -> dict[str, object]:
    member = _new(symbol, weight=weight, quality="COMPARABLE_MARGINAL", score=0.24)
    member["reference_price"] = 144.1
    member["target_weight_authority"] = {
        "lot_aware_final_reallocation": {
            "phase29_l19_lot_resolution": {
                "one_lot_weight": 0.01441,
                "one_lot_quantity": 100,
                "safety_hard_cap_weight": 0.25,
                "strategy_cap_weight": 0.18,
                "current_weight": 0.0,
                "executable_quantity_delta": 200,
            }
        }
    }
    return member


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
        "opportunity_quality_hash": f"test-g61-{symbol}-{quality}",
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
