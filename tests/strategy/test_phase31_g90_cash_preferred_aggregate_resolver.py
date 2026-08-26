from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


BUSINESS_DATE = "2026-08-27"
POST_G86_RUN = "runtime-test-historical-extended-smoke-20260824T032350824281Z"
PRE_G81_RUN = "runtime-test-historical-extended-smoke-20260823T140946562431Z"


def test_phase31_g90_january_actual_rows_no_frontier_only_bottleneck() -> None:
    expected_multi_participation = {
        "2023-01-17": {"59860", "65370"},
        "2023-01-18": {"59860", "65370", "42630"},
        "2023-01-19": {"65370", "29980", "38140"},
    }

    for business_date, expected_symbols in expected_multi_participation.items():
        competition = _competition_from_run(POST_G86_RUN, business_date)
        shadow = competition["canonical_multi_allocation_deployment_set"]
        allocations = shadow["security_allocations"]
        deferrals = shadow["cash_preferred_security_deferrals"]
        valid_cash_preferred = [
            row
            for row in allocations
            if row.get("participation_deferral_resolution") == "CASH_PREFERRED_PARTICIPATION_VALID"
        ]

        assert expected_symbols <= {row["symbol"] for row in allocations}
        assert len(valid_cash_preferred) > 1
        assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
        assert deferrals
        assert all(
            (row.get("participation_deferral_resolution_evidence") or {}).get("non_frontier_automatic_deferral")
            is False
            for row in [*valid_cash_preferred, *deferrals]
            if row.get("participation_deferral_resolution_evidence")
        )
        assert any(
            (row.get("participation_deferral_resolution_evidence") or {}).get("opportunity_set_frontier")
            is False
            for row in valid_cash_preferred
        )
        assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g90_g80_actual_weak_tail_rows_remain_deferred() -> None:
    expected_deferrals_by_date = {
        "2023-07-21": {"14390"},
        "2023-07-24": {"69320"},
        "2023-08-01": {"37600", "87500"},
    }

    for business_date, expected_symbols in expected_deferrals_by_date.items():
        competition = _competition_from_run(PRE_G81_RUN, business_date)
        shadow = competition["canonical_multi_allocation_deployment_set"]
        deferrals = {row["symbol"]: row for row in shadow["cash_preferred_security_deferrals"]}

        assert expected_symbols <= set(deferrals)
        assert all(deferrals[symbol]["authorized_allocation_weight"] == 0.0 for symbol in expected_symbols)
        assert all(
            deferrals[symbol]["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER"
            for symbol in expected_symbols
        )
        assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
        assert shadow["weak_tail_positive_allocation_preserved_when_cash_preferred"] is False
        assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g90_mixed_same_class_keeps_multiple_credible_rows_and_cash() -> None:
    competition = _competition(
        [
            _member("10010", weight=0.05, quality="COMPARABLE_MARGINAL", confidence=0.90),
            _member("20010", weight=0.04, quality="COMPARABLE_MARGINAL", confidence=0.80),
            _member("30010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.76),
            _member("90010", weight=0.02, quality="COMPARABLE_MARGINAL", confidence=0.20),
        ],
        available_budget=0.20,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocations = {row["symbol"]: row for row in shadow["security_allocations"]}
    deferrals = {row["symbol"]: row for row in shadow["cash_preferred_security_deferrals"]}

    assert allocations["10010"]["participation_deferral_resolution"] == "CASH_PREFERRED_PARTICIPATION_VALID"
    assert allocations["20010"]["participation_deferral_resolution"] == "CASH_PREFERRED_PARTICIPATION_VALID"
    assert len(allocations) > 1
    assert deferrals["30010"]["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER"
    assert deferrals["90010"]["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER"
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g90_aggregate_pressure_does_not_keep_all_or_only_frontier() -> None:
    competition = _competition(
        [
            _member("10010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.90),
            _member("20010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.80),
            _member("30010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.70),
            _member("40010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.66),
            _member("50010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.30),
            _member("60010", weight=0.03, quality="COMPARABLE_MARGINAL", confidence=0.20),
        ],
        available_budget=0.30,
    )

    shadow = competition["canonical_multi_allocation_deployment_set"]
    allocation_symbols = {row["symbol"] for row in shadow["security_allocations"]}
    deferral_symbols = {row["symbol"] for row in shadow["cash_preferred_security_deferrals"]}

    assert {"10010", "20010", "30010"} <= allocation_symbols
    assert {"40010", "50010", "60010"} <= deferral_symbols
    assert len(allocation_symbols) > 1
    assert len(deferral_symbols) > 0
    assert shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert shadow["capital_conservation"]["status"] == "PASS"


def test_phase31_g90_bootstrap_actual_path_preserved() -> None:
    strategy_dir = (
        Path("reports/runtime_tests/runs")
        / "runtime-test-historical-extended-smoke-20260824T032350824281Z"
        / "daily"
        / "2022-10-03"
        / "strategy"
    )
    actual_pc = json.loads((strategy_dir / "portfolio_construction.json").read_text())
    actual_shadow = actual_pc["capital_competition"]["canonical_multi_allocation_deployment_set"]
    assert actual_shadow["security_allocation_count"] > 0
    assert actual_shadow["authorized_cash_allocation"]["authorized_allocation_weight"] > 0

    competition = _competition_from_run(
        "runtime-test-historical-extended-smoke-20260823T230627195532Z",
        "2022-10-03",
    )
    shadow = competition["canonical_multi_allocation_deployment_set"]

    assert shadow["bootstrap_cash_preferred_participation_allowed"] is True
    assert shadow["security_allocation_count"] > 0
    assert shadow["bootstrap_cash_preferred_participation_count"] > 0


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


def _competition(members: list[dict[str, object]], *, available_budget: float) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.50,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(),
    )


def _risk() -> dict[str, object]:
    return {
        "risk_pacing_intent": "CAUTIOUS_DEPLOYMENT",
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
            "envelope_hash": "test-g90-risk",
        },
    }


def _member(symbol: str, *, weight: float, quality: str, confidence: float) -> dict[str, object]:
    evidence = {
        "schema_version": "opportunity_quality.v1",
        "business_date": BUSINESS_DATE,
        "as_of_business_date": BUSINESS_DATE,
        "symbol": symbol,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "comparison_sufficiency": "SUFFICIENT",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "entry_admission_action": "BUY_NEW_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "evidence_completeness": "COMPLETE",
        "future_information_used": False,
        "historical_outcome_used": False,
        "opportunity_quality_hash": f"test-g90-{symbol}-{quality}-{confidence}",
    }
    priority = int(symbol[:2])
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": priority,
        "opportunity_buy_rank": priority,
        "runtime_opportunity_score": confidence - 0.5,
        "confidence": confidence,
        "quality_score": confidence,
        "entry_admission_action": "BUY_NEW_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "momentum_trajectory_classification": "MIXED_OR_UNRESOLVED",
        "strategy_intelligence_relative_strength_state": "MIXED",
        "selection_quality_tier": "CAUTION_CONTINUATION",
        "quality_status": "PASS",
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": priority,
            "marginal_capital_value_class": "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
    }
