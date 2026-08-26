from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


TARGET_RUN = "runtime-test-historical-extended-smoke-20260824T055234719725Z"
G80_REFERENCE_RUN = "runtime-test-historical-extended-smoke-20260823T140946562431Z"
BUSINESS_DATE = "2026-08-28"


def test_phase31_g97_0405_0406_reconsiderable_rows_authoritative_cash_defer() -> None:
    expected = {
        "2023-04-05": {"83060", "59350", "77760", "44440"},
        "2023-04-06": {"83060", "59350", "43880", "94340", "77760"},
    }

    for business_date, symbols in expected.items():
        multi = _multi_from_run(TARGET_RUN, business_date)
        allocations = {
            row["symbol"]
            for row in multi["security_allocations"]
            if row.get("residual_reconsideration_authoritative_binding")
        }
        deferrals = {
            row["symbol"]: row
            for row in multi["cash_preferred_security_deferrals"]
            if row.get("residual_reconsideration_authoritative_binding")
        }

        assert symbols.isdisjoint(allocations)
        assert symbols <= set(deferrals)
        assert all(deferrals[symbol]["authorized_allocation_weight"] == 0.0 for symbol in symbols)
        assert all(deferrals[symbol]["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER" for symbol in symbols)
        assert multi["authorized_cash_allocation"]["authorized_allocation_weight"] > 0.0
        assert multi["capital_conservation"]["status"] == "PASS"


def test_phase31_g97_positive_shadow_anchors_enter_authoritative_pc_allocation() -> None:
    anchors = {
        "2023-03-22": {"94320"},
        "2023-04-14": {"94320"},
        "2023-04-18": {"59350"},
    }

    for business_date, symbols in anchors.items():
        multi = _multi_from_run(TARGET_RUN, business_date)
        allocations = {
            row["symbol"]: row
            for row in multi["security_allocations"]
            if row.get("residual_reconsideration_authoritative_binding")
        }

        assert symbols <= set(allocations)
        assert all(allocations[symbol]["authorized_allocation_weight"] > 0.0 for symbol in symbols)
        assert all(allocations[symbol]["authorized_for_position_sizing"] is True for symbol in symbols)
        assert all(allocations[symbol]["authorized_for_runtime_order"] is False for symbol in symbols)
        assert multi["capital_conservation"]["status"] == "PASS"


def test_phase31_g97_multi_security_reconsideration_coexists_with_cash() -> None:
    multi = _multi_from_run(TARGET_RUN, "2023-04-07")
    allocations = {
        row["symbol"]: row
        for row in multi["security_allocations"]
        if row.get("residual_reconsideration_authoritative_binding")
    }

    assert {"83060", "77760", "44440"} <= set(allocations)
    assert len(allocations) > 1
    assert multi["authorized_cash_allocation"]["authorized_allocation_weight"] > 0.0
    assert multi["single_winner_general_contract"] is False
    assert multi["capital_conservation"]["status"] == "PASS"


def test_phase31_g97_safety_terminal_and_g80_weak_tail_not_resurrected() -> None:
    multi = _multi_from_run(TARGET_RUN, "2023-04-06")
    allocations = {
        row["symbol"]
        for row in multi["security_allocations"]
        if row.get("residual_reconsideration_authoritative_binding")
    }
    terminals = {
        row["symbol"]: row
        for row in multi["residual_reconsideration_authoritative_binding_evidence"]["terminal_rows"]
    }

    assert "67310" not in allocations
    assert terminals["67310"]["source_shadow_outcome"] == "SHADOW_SAFETY_TERMINAL"
    assert multi["residual_reconsideration_authoritative_binding_evidence"]["safety_terminal_resurrection_count"] == 0

    weak_tail_symbols = {
        "2023-07-21": {"14390"},
        "2023-07-24": {"69320"},
        "2023-08-01": {"37600", "87500"},
    }
    resurrected = 0
    for business_date, symbols in weak_tail_symbols.items():
        weak_multi = _multi_from_run(G80_REFERENCE_RUN, business_date)
        weak_allocations = {
            row["symbol"]
            for row in weak_multi["security_allocations"]
            if row.get("residual_reconsideration_authoritative_binding")
        }
        resurrected += len(symbols & weak_allocations)

    assert resurrected == 0


def test_phase31_g97_add_competition_preserved_without_new_buy_bonus() -> None:
    competition = build_capital_competition_framework(
        members=[
            _add_member("20010", increment=0.06, priority=1),
            _new_buy_member("10010", target_weight=0.05, priority=2),
        ],
        target_gross_exposure=0.50,
        total_target_weight=0.11,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.08},
        lot_reallocation_evidence={
            "phase29_l19_allocation_iterations": [{"symbol": "20010"}],
            "skipped": [
                {
                    "symbol": "10010",
                    "canonical_sizing_evidence": {
                        "constraint_reason_codes": ["NO_POSITIVE_QUANTITY_DELTA"],
                        "terminality": "RECONSIDERABLE",
                    },
                }
            ],
        },
        risk_pacing_evidence=_risk(intent="NORMAL_DEPLOYMENT"),
    )
    multi = competition["canonical_multi_allocation_deployment_set"]
    allocations = {row["symbol"]: row for row in multi["security_allocations"]}

    assert "20010" in allocations
    assert allocations["20010"]["competitor_type"] == "ADD"
    assert allocations["20010"].get("residual_reconsideration_authoritative_binding") is not True
    assert allocations["20010"]["authorized_allocation_weight"] == 0.06
    assert "10010" in allocations
    assert allocations["10010"]["residual_reconsideration_authoritative_binding"] is True
    assert allocations["10010"]["authorized_allocation_weight"] == 0.02
    assert multi["residual_reconsideration_authoritative_binding_evidence"]["reconsideration_auto_authorization"] is False
    assert multi["capital_conservation"]["status"] == "PASS"


def test_phase31_g97_dominated_lot_and_no_redecision_contracts() -> None:
    competition = build_capital_competition_framework(
        members=[
            _new_buy_member("30010", target_weight=0.08, priority=1, selected=True),
            _new_buy_member("40010", target_weight=0.05, priority=2),
        ],
        target_gross_exposure=0.50,
        total_target_weight=0.13,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.08},
        lot_reallocation_evidence={
            "phase29_l19_allocation_iterations": [{"symbol": "30010"}],
            "skipped": [
                {
                    "symbol": "40010",
                    "canonical_sizing_evidence": {
                        "constraint_reason_codes": ["NO_POSITIVE_QUANTITY_DELTA"],
                        "terminality": "RECONSIDERABLE",
                    },
                }
            ],
        },
        risk_pacing_evidence=_risk(intent="NORMAL_DEPLOYMENT"),
    )
    binding = competition["canonical_multi_allocation_deployment_set"][
        "residual_reconsideration_authoritative_binding_evidence"
    ]

    assert binding["terminal_rows"][0]["source_shadow_outcome"] == "SHADOW_DOMINATED_BY_STRONGER_SECURITY"
    assert binding["ps_reconsideration_authority"] is False
    assert binding["ps_priority_redecision"] is False
    assert binding["runtime_reconsideration_authority"] is False
    assert binding["runtime_priority_redecision"] is False
    assert binding["synthetic_quantity_created_by_pc"] is False
    assert binding["unresolved_count"] == 0
    assert competition["canonical_multi_allocation_deployment_set"]["capital_conservation"]["status"] == "PASS"


def _multi_from_run(run_id: str, business_date: str) -> dict[str, object]:
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
    return competition["canonical_multi_allocation_deployment_set"]


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
            "envelope_hash": "test-g97-risk",
        },
    }


def _new_buy_member(
    symbol: str,
    *,
    target_weight: float,
    priority: int,
    quality: str = "STRONG",
    selected: bool = False,
) -> dict[str, object]:
    member = _base_member(symbol, priority=priority, quality=quality)
    member.update(
        {
            "current_position": False,
            "membership_intent": "ADD_CANDIDATE",
            "pm_action": "NEW",
            "normal_target_weight": target_weight,
            "requested_buy_new_weight": target_weight,
            "accepted_buy_new_weight": target_weight,
            "target_weight": target_weight,
            "lot_aware_accepted_buy_new_weight": target_weight if selected else 0.0,
        }
    )
    return member


def _add_member(symbol: str, *, increment: float, priority: int) -> dict[str, object]:
    member = _base_member(symbol, priority=priority, quality="STRONG")
    member.update(
        {
            "current_position": True,
            "current_weight": 0.10,
            "membership_intent": "ADD_CANDIDATE",
            "pm_action": "ADD",
            "target_weight": 0.10 + increment,
            "requested_incremental_weight": increment,
            "accepted_incremental_weight": increment,
            "lot_aware_accepted_incremental_weight": increment,
            "add_investment_evidence": {
                "incremental_value": {"status": "PASS", "state": "POSITIVE"},
                "opportunity_cost": {"status": "PASS", "state": "PASS"},
            },
        }
    )
    return member


def _base_member(symbol: str, *, priority: int, quality: str) -> dict[str, object]:
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
        "opportunity_quality_hash": f"test-g97-{symbol}-{quality}",
    }
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "construction_priority": priority,
        "opportunity_buy_rank": priority,
        "runtime_opportunity_score": 1.0 - priority / 100.0,
        "confidence": 0.95,
        "quality_score": 0.95,
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
            "canonical_marginal_capital_priority_index": priority,
            "marginal_capital_value_class": "ELIGIBLE_STRONG",
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
    }
