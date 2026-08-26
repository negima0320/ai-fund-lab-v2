from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


TARGET_RUN = "runtime-test-historical-extended-smoke-20260824T055234719725Z"
G80_REFERENCE_RUN = "runtime-test-historical-extended-smoke-20260823T140946562431Z"
BUSINESS_DATE = "2026-08-27"


def test_phase31_g95_actual_0405_0406_rows_receive_terminal_shadow_competition() -> None:
    expected_symbols = {
        "2023-04-05": {"83060", "59350", "77760", "44440"},
        "2023-04-06": {"83060", "59350", "43880", "94340", "77760"},
    }

    for business_date, symbols in expected_symbols.items():
        shadow = _shadow_from_run(TARGET_RUN, business_date)
        rows = {row["symbol"]: row for row in shadow["shadow_rows"]}

        assert shadow["schema_version"] == "canonical_residual_reconsideration_shadow.v1"
        assert shadow["authoritative"] is False
        assert shadow["shadow_only"] is True
        assert shadow["production_binding"] is False
        assert shadow["feeds_canonical_multi_allocation_deployment_set"] is False
        assert shadow["shadow_row_lineage_complete"] is True
        assert shadow["reconsideration_auto_authorization"] is False
        assert symbols <= set(rows)
        assert all(rows[symbol]["shadow_outcome"] != "PENDING_RECONSIDERATION" for symbol in symbols)
        assert all(rows[symbol]["g90_shadow_classification"] for symbol in symbols)
        assert all(rows[symbol]["requested_shadow_weight"] > 0 for symbol in symbols)
        assert all(rows[symbol]["authorized_for_position_sizing"] is False for symbol in symbols)
        assert all(rows[symbol]["authorized_for_runtime_order"] is False for symbol in symbols)


def test_phase31_g95_actual_0406_safety_terminal_not_resurrected() -> None:
    shadow = _shadow_from_run(TARGET_RUN, "2023-04-06")
    rows = {row["symbol"]: row for row in shadow["shadow_rows"]}

    assert rows["67310"]["shadow_outcome"] == "SHADOW_SAFETY_TERMINAL"
    assert rows["67310"]["authorized_shadow_weight"] == 0.0
    assert shadow["safety_terminal_resurrection_count"] == 0


def test_phase31_g95_known_weak_tail_dates_do_not_revive_security_shadow() -> None:
    expected_weak_tail_symbols = {
        "2023-07-21": {"14390"},
        "2023-07-24": {"69320"},
        "2023-08-01": {"37600", "87500"},
    }
    resurrected = 0
    for business_date, weak_tail_symbols in expected_weak_tail_symbols.items():
        shadow = _shadow_from_run(G80_REFERENCE_RUN, business_date)
        rows = {row["symbol"]: row for row in shadow["shadow_rows"]}
        resurrected += sum(
            1
            for symbol in weak_tail_symbols
            if rows.get(symbol, {}).get("shadow_outcome") == "SHADOW_SECURITY_PARTICIPATION_VALID"
        )

    assert resurrected == 0


def test_phase31_g95_strong_reconsiderable_row_can_survive_shadow_competition() -> None:
    competition = build_capital_competition_framework(
        members=[_member("10010", quality="STRONG", target_weight=0.05, confidence=0.96)],
        target_gross_exposure=0.50,
        total_target_weight=0.05,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.10},
        lot_reallocation_evidence={
            "skipped": [
                {
                    "symbol": "10010",
                    "canonical_sizing_evidence": {
                        "constraint_reason_codes": ["NO_POSITIVE_QUANTITY_DELTA"],
                        "terminality": "RECONSIDERABLE",
                    },
                }
            ]
        },
        risk_pacing_evidence=_risk(intent="NORMAL_DEPLOYMENT"),
    )

    shadow = competition["canonical_residual_reconsideration_shadow"]
    rows = {row["symbol"]: row for row in shadow["shadow_rows"]}

    assert shadow["shadow_security_positive_rows"] == 1
    assert rows["10010"]["shadow_outcome"] == "SHADOW_SECURITY_PARTICIPATION_VALID"
    assert rows["10010"]["interaction_result"] == "DEPLOY_ELIGIBLE"
    assert rows["10010"]["authorized_shadow_weight"] == 0.05
    binding = competition["canonical_multi_allocation_deployment_set"][
        "residual_reconsideration_authoritative_binding_evidence"
    ]
    assert binding["shadow_to_authoritative_semantic_equivalence"] is True
    assert binding["positive_authoritative_count"] == 1


def _shadow_from_run(run_id: str, business_date: str) -> dict[str, object]:
    strategy_dir = Path("reports/runtime_tests/runs") / run_id / "daily" / business_date / "strategy"
    pc = json.loads((strategy_dir / "portfolio_construction.json").read_text())
    risk_pacing_evidence = (pc.get("portfolio_policy_allocation_authority") or {}).get("risk_pacing_evidence") or {}
    multi = pc["capital_competition"]["canonical_multi_allocation_deployment_set"]
    competition = build_capital_competition_framework(
        members=pc["portfolio_members"],
        target_gross_exposure=pc.get("target_gross_exposure"),
        total_target_weight=pc.get("total_target_weight")
        or sum(float(row.get("target_weight") or 0.0) for row in pc["portfolio_members"]),
        business_date=business_date,
        incremental_budget_evidence={"available_incremental_budget": multi.get("available_incremental_budget")},
        lot_reallocation_evidence=pc.get("lot_aware_final_reallocation") or {},
        risk_pacing_evidence=risk_pacing_evidence,
    )
    return competition["canonical_residual_reconsideration_shadow"]


def _risk(*, intent: str) -> dict[str, object]:
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
            "deployment_capacity_semantic": "NORMAL_DEPLOYMENT_CAPACITY",
            "bootstrap_or_residual_cash_state": "NORMAL_INVESTED_PORTFOLIO",
            "trading_consumer_connected": False,
            "envelope_hash": "test-g95-risk",
        },
    }


def _member(symbol: str, *, quality: str, target_weight: float, confidence: float) -> dict[str, object]:
    evidence = {
        "schema_version": "opportunity_quality.v1",
        "business_date": BUSINESS_DATE,
        "as_of_business_date": BUSINESS_DATE,
        "symbol": symbol,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "comparison_sufficiency": "SUFFICIENT",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "evidence_completeness": "COMPLETE",
        "future_information_used": False,
        "historical_outcome_used": False,
        "opportunity_quality_hash": f"test-g95-{symbol}-{quality}",
    }
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": 1,
        "opportunity_buy_rank": 1,
        "runtime_opportunity_score": confidence,
        "confidence": confidence,
        "quality_score": confidence,
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "momentum_trajectory_classification": "HEALTHY_CONTINUATION",
        "strategy_intelligence_relative_strength_state": "SUPPORTIVE",
        "selection_quality_tier": "HIGH_QUALITY_CONTINUATION",
        "quality_status": "PASS",
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": 1,
            "marginal_capital_value_class": "ELIGIBLE_STRONG",
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "normal_target_weight": target_weight,
        "requested_buy_new_weight": target_weight,
        "accepted_buy_new_weight": target_weight,
        "target_weight": target_weight,
        "lot_aware_accepted_buy_new_weight": 0.0,
    }
