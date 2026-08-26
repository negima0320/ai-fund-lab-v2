from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-08-26"
PRE_G81_RUN = "runtime-test-historical-extended-smoke-20260823T140946562431Z"
POST_G83_RUN = "runtime-test-historical-extended-smoke-20260823T232301910860Z"


def test_phase31_g86_actual_normal_cash_preferred_participation_restored() -> None:
    expected_symbols_by_date = {
        "2022-10-13": {"94340"},
        "2022-10-14": {"94320"},
        "2022-10-17": {"94320"},
        "2022-10-18": {"94320"},
    }

    for business_date, expected_symbols in expected_symbols_by_date.items():
        competition = _competition_from_run(POST_G83_RUN, business_date)
        shadow = competition["canonical_multi_allocation_deployment_set"]
        allocations = shadow["security_allocations"]
        allocated_symbols = {row["symbol"] for row in allocations}

        assert expected_symbols <= allocated_symbols
        assert shadow["cash_preferred_interaction_action_separated"] is True
        assert shadow["pc_participation_deferral_authority"] is True
        assert shadow["cash_preferred_participation_valid_count"] > 0
        assert shadow["cash_preferred_defer_count"] > 0
        assert shadow["aggregate_participation_resolution_active"] is True
        assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
        assert any(
            row["interaction_result"] == "CASH_PREFERRED"
            and row["participation_deferral_resolution"] == "CASH_PREFERRED_PARTICIPATION_VALID"
            for row in allocations
        )
        assert shadow["lot_aware_allocation_to_sizing_compatibility"]["lot_executable_count"] > 0


def test_phase31_g86_actual_weak_tail_cash_preferred_examples_defer() -> None:
    expected_deferrals_by_date = {
        "2023-07-21": {"14390"},
        "2023-07-24": {"69320"},
        "2023-08-01": {"37600", "87500"},
    }

    for business_date, expected_symbols in expected_deferrals_by_date.items():
        competition = _competition_from_run(PRE_G81_RUN, business_date)
        shadow = competition["canonical_multi_allocation_deployment_set"]
        deferrals = shadow["cash_preferred_security_deferrals"]
        deferred_symbols = {row["symbol"] for row in deferrals}

        assert expected_symbols <= deferred_symbols
        assert all(row["authorized_allocation_weight"] == 0.0 for row in deferrals if row["symbol"] in expected_symbols)
        assert all(row["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER" for row in deferrals if row["symbol"] in expected_symbols)
        assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
        assert shadow["aggregate_participation_resolution_active"] is True
        assert shadow["weak_tail_positive_allocation_preserved_when_cash_preferred"] is False
        assert shadow["lower_priority_implicit_promotion"] is False


def test_phase31_g86_mixed_day_multi_destination_partition() -> None:
    competition = _competition(
        [
            _member("10010", weight=0.05, quality="STRONG", participation="strong"),
            _member("20010", weight=0.04, quality="COMPARABLE_MARGINAL", participation="valid"),
            _member("90010", weight=0.03, quality="COMPARABLE_MARGINAL", participation="weak"),
        ],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.15,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocations = {row["symbol"]: row for row in shadow["security_allocations"]}
    deferrals = {row["symbol"]: row for row in shadow["cash_preferred_security_deferrals"]}

    assert allocations["10010"]["interaction_result"] == "SELECTIVE_COMPETITION"
    assert allocations["20010"]["interaction_result"] == "CASH_PREFERRED"
    assert allocations["20010"]["participation_deferral_resolution"] == "CASH_PREFERRED_PARTICIPATION_VALID"
    assert deferrals["90010"]["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER"
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert shadow["capital_conservation"]["status"] == "PASS"
    assert shadow["aggregate_participation_resolution_active"] is True


def test_phase31_g86_no_valid_opportunity_remains_all_cash() -> None:
    competition = _competition(
        [_member("90010", weight=0.0, quality="INSUFFICIENT", participation="weak")],
        intent="CAUTIOUS_DEPLOYMENT",
        available_budget=0.10,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["security_allocations"] == []
    assert shadow["cash_preferred_security_deferrals"] == []
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] == 0.10
    assert shadow["capital_conservation"]["status"] == "PASS"


def _competition_from_run(run_id: str, business_date: str) -> dict[str, object]:
    strategy_dir = Path("reports/runtime_tests/runs") / run_id / "daily" / business_date / "strategy"
    pc = json.loads((strategy_dir / "portfolio_construction.json").read_text())
    risk_pacing_evidence = (pc.get("portfolio_policy_allocation_authority") or {}).get("risk_pacing_evidence") or {}
    multi = pc["capital_competition"]["canonical_multi_allocation_deployment_set"]
    return build_capital_competition_framework(
        members=pc["portfolio_members"],
        target_gross_exposure=pc.get("target_gross_exposure"),
        total_target_weight=pc.get("total_target_weight")
        or sum(float(row.get("target_weight") or 0.0) for row in pc["portfolio_members"]),
        business_date=business_date,
        incremental_budget_evidence={"available_incremental_budget": multi.get("available_incremental_budget")},
        risk_pacing_evidence=risk_pacing_evidence,
    )


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
            "bootstrap_or_residual_cash_state": "NORMAL_INVESTED_PORTFOLIO",
            "trading_consumer_connected": False,
            "envelope_hash": f"test-g86-{intent}",
        },
    }


def _member(symbol: str, *, weight: float, quality: str, participation: str) -> dict[str, object]:
    evidence = {
        "schema_version": "opportunity_quality.v1",
        "business_date": BUSINESS_DATE,
        "as_of_business_date": BUSINESS_DATE,
        "symbol": symbol,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "comparison_sufficiency": "SUFFICIENT" if participation in {"valid", "strong"} else "INSUFFICIENT",
        "entry_admission_evidence_sufficiency": "SUFFICIENT" if participation in {"valid", "strong"} else "INSUFFICIENT",
        "entry_admission_action": "BUY_NEW_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "evidence_completeness": "COMPLETE",
        "future_information_used": False,
        "historical_outcome_used": False,
        "opportunity_quality_hash": f"test-g86-{symbol}-{quality}-{participation}",
    }
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": int(symbol[:2]),
        "opportunity_buy_rank": int(symbol[:2]),
        "runtime_opportunity_score": 0.25 if participation in {"valid", "strong"} else -0.25,
        "confidence": 0.9 if participation in {"valid", "strong"} else 0.2,
        "quality_score": 0.75 if participation in {"valid", "strong"} else 0.45,
        "entry_admission_action": "BUY_NEW_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": evidence["entry_admission_evidence_sufficiency"],
        "momentum_trajectory_classification": "HEALTHY_CONTINUATION" if participation == "strong" else "MIXED_OR_UNRESOLVED",
        "strategy_intelligence_relative_strength_state": "SUPPORTIVE" if participation in {"valid", "strong"} else "WEAK",
        "selection_quality_tier": "CAUTION_CONTINUATION",
        "quality_status": "PASS",
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
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE" if weight > 0 else "EXCLUDE",
        "pm_action": "NEW" if weight > 0 else "",
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
    }
