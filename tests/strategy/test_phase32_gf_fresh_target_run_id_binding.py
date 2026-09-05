from __future__ import annotations

from ai_fund_lab_v2.strategy import marginal_capital_value
from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


def test_phase32_gf_fresh_target_runtime_run_id_binds_same_run_evidence() -> None:
    shadow = _fresh_target(run_id="runtime-test-run-a", member_run_id="runtime-test-run-a")

    assert shadow["run_id"] == "runtime-test-run-a"
    assert shadow["runtime_test_run_id"] == "runtime-test-run-a"
    assert shadow["run_evidence_root"].endswith("runtime-test-run-a")
    assert shadow["pit_status"] == "PASS"
    assert shadow["run_evidence_root_binding"]["status"] == "PASS"
    assert shadow["run_evidence_root_binding"]["source"] == "runtime_test_context"
    assert shadow["run_evidence_root_binding"]["run_id_inferred_from_filesystem_path"] is False
    assert shadow["zero_tolerance_assertions"]["stale_cross_run_evidence_accepted_count"] == 0
    assert shadow["zero_tolerance_assertions"]["runtime_authority_leak_count"] == 0
    assert shadow["authoritative_consumer_count"] == 0


def test_phase32_gf_fresh_target_cross_run_source_evidence_is_rejected() -> None:
    shadow = _fresh_target(run_id="runtime-test-run-a", member_run_id="runtime-test-run-b")

    assert shadow["pit_status"] == "FAIL_CLOSED"
    assert shadow["run_evidence_root_binding"]["status"] == "FAIL_CLOSED"
    assert "FRESH_TARGET_CROSS_RUN_SOURCE_EVIDENCE_REJECTED" in shadow["run_evidence_root_binding"]["reason_codes"]
    assert shadow["zero_tolerance_assertions"]["stale_cross_run_evidence_accepted_count"] == 0
    assert shadow["zero_tolerance_assertions"]["stale_cross_run_evidence_rejected_count"] >= 1
    assert shadow["production_allocation_consumer"] is False
    assert shadow["runtime_planning_consumer"] is False


def test_phase32_gf_fresh_target_missing_runtime_run_id_fails_closed() -> None:
    shadow = _fresh_target(run_id="", member_run_id="", require_run_id=True)

    assert shadow["run_id"] == ""
    assert shadow["pit_status"] == "FAIL_CLOSED"
    assert shadow["run_evidence_root_binding"]["status"] == "FAIL_CLOSED"
    assert "FRESH_TARGET_RUNTIME_RUN_ID_MISSING" in shadow["run_evidence_root_binding"]["reason_codes"]
    assert shadow["zero_tolerance_assertions"]["runtime_run_id_missing_count"] == 1
    assert shadow["zero_tolerance_assertions"]["runtime_authority_leak_count"] == 0


def test_phase32_gf_pc_runtime_context_materializes_fresh_target_run_binding() -> None:
    members = [_member("7203", run_id="runtime-test-run-a", accepted=0.04)]

    result = build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.8,
        total_target_weight=0.04,
        business_date="2026-07-15",
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
        runtime_test_context={
            "run_id": "runtime-test-run-a",
            "evidence_root": "reports/runtime_tests/runs/runtime-test-run-a",
            "business_date": "2026-07-15",
        },
    )

    shadow = result["fresh_target_portfolio_shadow"]
    assert shadow["run_id"] == "runtime-test-run-a"
    assert shadow["run_evidence_root_binding"]["status"] == "PASS"
    assert result["authority"]["fresh_target_portfolio_shadow_authoritative_consumer_count"] == 0
    assert result["authority"]["fresh_target_portfolio_shadow_production_consumer"] is False


def test_phase32_gf_pc_runtime_context_does_not_change_production_competition() -> None:
    members = [_member("7203", run_id="runtime-test-run-a", accepted=0.04)]
    kwargs = {
        "members": members,
        "target_gross_exposure": 0.8,
        "total_target_weight": 0.04,
        "business_date": "2026-07-15",
        "incremental_budget_evidence": {"available_incremental_budget": 0.4},
        "risk_pacing_evidence": {"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
    }

    without_context = build_capital_competition_framework(**kwargs)
    with_context = build_capital_competition_framework(
        **kwargs,
        runtime_test_context={
            "run_id": "runtime-test-run-a",
            "evidence_root": "reports/runtime_tests/runs/runtime-test-run-a",
            "business_date": "2026-07-15",
        },
    )

    assert with_context["competitors"] == without_context["competitors"]
    assert with_context["market_candidate_cash_interaction"] == without_context["market_candidate_cash_interaction"]
    assert with_context["canonical_deployment_set"] == without_context["canonical_deployment_set"]
    assert with_context["capital_competition_winner_type"] == without_context["capital_competition_winner_type"]
    assert with_context["fresh_target_portfolio_shadow"]["run_id"] == "runtime-test-run-a"


def _fresh_target(*, run_id: str, member_run_id: str, require_run_id: bool = True) -> dict[str, object]:
    members = [_member("7203", run_id=member_run_id, accepted=0.04)]
    unified = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=members,
        competitors=[_production_competitor("7203", accepted=0.04)],
        cash_evidence=_cash_evidence(run_id=member_run_id),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
    )
    return marginal_capital_value.build_fresh_target_portfolio_shadow(
        business_date="2026-07-15",
        feature_date="2026-07-15",
        members=members,
        unified_marginal_capital_shadow=unified,
        cash_evidence=_cash_evidence(run_id=member_run_id),
        target_gross_exposure=0.8,
        run_id=run_id,
        evidence_root=f"reports/runtime_tests/runs/{run_id}" if run_id else "reports/runtime_tests/runs/missing-run",
        require_run_id=require_run_id,
    )


def _member(code: str, *, run_id: str, accepted: float) -> dict[str, object]:
    return {
        "security_code": code,
        "symbol": code,
        "runtime_test_run_id": run_id,
        "business_date": "2026-07-15",
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "semantic_buy_type": "BUY_NEW",
        "input_opportunity_rank": 1,
        "runtime_opportunity_score": 0.8,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_score": 0.72,
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "expected_edge_improvement_state": "IMPROVING",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "accepted_buy_new_weight": accepted,
        "target_weight": accepted,
        "phase29_l19_lot_resolution": {
            "one_lot_quantity": 100,
            "one_lot_notional": 100000,
            "final_quantity_delta": 100,
            "one_lot_feasibility_status": "PASS",
        },
    }


def _production_competitor(code: str, *, accepted: float) -> dict[str, object]:
    return {
        "competitor_type": "NEW_BUY",
        "symbol": code,
        "status": "COMPETITOR_SELECTED" if accepted > 0 else "COMPETITOR_REJECTED_RECONSIDERABLE",
        "accepted_weight": accepted,
        "reason_codes": ["COMPETITOR_SELECTED"] if accepted > 0 else ["NO_POSITIVE_DELTA"],
    }


def _cash_evidence(*, run_id: str) -> dict[str, object]:
    return {
        "schema_version": "cash_competitor_evidence.v1",
        "business_date": "2026-07-15",
        "runtime_test_run_id": run_id,
        "current_cash_weight": 0.2,
        "remaining_cash_weight": 0.76,
        "cash_preference_semantic": "OPTIONALITY_RESERVE",
        "evidence_completeness": "COMPLETE",
        "reason_codes": ["VALID_SAFETY_RESERVE"],
        "cash_competitor_evidence_hash": f"cash-{run_id}",
    }
