from __future__ import annotations

from typing import Any, Mapping

from ai_fund_lab_v2.strategy.portfolio_construction import (
    apply_lot_aware_final_reallocation,
    build_capital_competition_framework,
    promote_final_portfolio_construction_for_production,
)
from ai_fund_lab_v2.strategy.shadow_runtime import _runtime_test_context_from_portfolio_construction_draft


RUN_A = "runtime-test-run-a"
RUN_B = "runtime-test-run-b"
BUSINESS_DATE = "2026-07-15"


def test_phase32_gh_lot_aware_rebuilds_preserve_runtime_run_binding() -> None:
    promoted = _promoted_final(run_id=RUN_A, member_run_id=RUN_A)

    for shadow in _fresh_target_layers(promoted):
        assert shadow["run_id"] == RUN_A
        assert shadow["runtime_test_run_id"] == RUN_A
        assert shadow["run_evidence_root"].endswith(RUN_A)
        assert shadow["pit_status"] == "PASS"
        assert shadow["run_evidence_root_binding"]["status"] == "PASS"
        assert shadow["zero_tolerance_assertions"]["stale_cross_run_evidence_accepted_count"] == 0
        assert shadow["authoritative_consumer_count"] == 0
        assert shadow["action_authority"] is False
        assert shadow["quantity_authority"] is False
        assert shadow["order_authority"] is False


def test_phase32_gh_cross_run_evidence_rejects_all_lot_aware_layers() -> None:
    promoted = _promoted_final(run_id=RUN_A, member_run_id=RUN_B)

    for shadow in _fresh_target_layers(promoted):
        assert shadow["run_id"] == RUN_A
        assert shadow["pit_status"] == "FAIL_CLOSED"
        assert shadow["run_evidence_root_binding"]["status"] == "FAIL_CLOSED"
        assert "FRESH_TARGET_CROSS_RUN_SOURCE_EVIDENCE_REJECTED" in shadow["run_evidence_root_binding"]["reason_codes"]
        assert shadow["zero_tolerance_assertions"]["stale_cross_run_evidence_accepted_count"] == 0
        assert shadow["zero_tolerance_assertions"]["stale_cross_run_evidence_rejected_count"] >= 1


def test_phase32_gh_missing_finalizer_context_fails_closed_instead_of_silent_empty_run_id() -> None:
    recovered = _runtime_test_context_from_portfolio_construction_draft({}, business_date=BUSINESS_DATE)
    reallocation = apply_lot_aware_final_reallocation(
        members=[_buy_new("7203", run_id="", accepted=0.04)],
        lot_feasibility_rows=[],
        target_gross_exposure=0.8,
        single_name_cap=0.18,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        final_capital_competition_risk_pacing_evidence=_risk_pacing(),
        runtime_test_context=recovered,
    )

    shadow = reallocation["evidence"]["capital_competition"]["fresh_target_portfolio_shadow"]
    assert shadow["run_id"] == ""
    assert shadow["pit_status"] == "FAIL_CLOSED"
    assert shadow["run_evidence_root_binding"]["status"] == "FAIL_CLOSED"
    assert "FRESH_TARGET_RUNTIME_RUN_ID_MISSING" in shadow["run_evidence_root_binding"]["reason_codes"]
    assert shadow["zero_tolerance_assertions"]["runtime_run_id_missing_count"] == 1


def test_phase32_gh_runtime_context_does_not_change_fresh_target_logic_or_production_members() -> None:
    members = [_buy_new("7203", run_id=RUN_A, accepted=0.04), _winner_hold("9432", run_id=RUN_A)]
    with_context = _reallocation(members=members, run_id=RUN_A)
    without_context = apply_lot_aware_final_reallocation(
        members=[dict(row) for row in members],
        lot_feasibility_rows=[],
        target_gross_exposure=0.8,
        single_name_cap=0.18,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        final_capital_competition_risk_pacing_evidence=_risk_pacing(),
    )

    assert with_context["members"] == without_context["members"]
    assert with_context["reason_codes"] == without_context["reason_codes"]
    context_shadow = with_context["evidence"]["capital_competition"]["fresh_target_portfolio_shadow"]
    no_context_shadow = without_context["evidence"]["capital_competition"]["fresh_target_portfolio_shadow"]
    assert _fresh_logic_signature(context_shadow) == _fresh_logic_signature(no_context_shadow)
    assert context_shadow["run_id"] == RUN_A
    assert no_context_shadow["run_id"] == ""


def test_phase32_gh_winner_conflict_and_history_neutrality_observability_survive() -> None:
    promoted = _promoted_final(run_id=RUN_A, member_run_id=RUN_A, members=[_winner_hold("9432", run_id=RUN_A)])
    row = _row_by_symbol(promoted["capital_competition"]["fresh_target_portfolio_shadow"], "9432")

    assert row["divergence_class"] == "WINNER_PROTECTION_CONFLICT"
    assert row["winner_protection_adjustment"]["creates_reduce_or_exit_authority"] is False
    assert row["history_safety_adjustment"]["old_ownership_used_for_target"] is False
    assert row["history_safety_adjustment"]["old_closed_campaign_used_for_target"] is False
    assert row["history_safety_adjustment"]["prior_add_count_used_for_target"] is False
    assert row["history_safety_adjustment"]["prior_exit_count_used_for_target"] is False
    assert row["history_safety_adjustment"]["average_cost_used_for_target"] is False
    assert row["safety_display"]["add_safety_bypass"] is False
    assert row["safety_display"]["g129_increment_scope"] == "ORDER_INCREMENT_SCOPED"


def _promoted_final(
    *,
    run_id: str,
    member_run_id: str,
    members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = members or [_buy_new("7203", run_id=member_run_id, accepted=0.04), _winner_hold("9432", run_id=member_run_id)]
    draft_competition = build_capital_competition_framework(
        members=rows,
        target_gross_exposure=0.8,
        total_target_weight=0.24,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence=_risk_pacing(),
        runtime_test_context=_context(run_id),
    )
    reallocation = _reallocation(members=rows, run_id=run_id)
    return promote_final_portfolio_construction_for_production(
        {
            "producer_result_status": "PASS",
            "reason_codes": [],
            "capital_competition": draft_competition,
            "lot_aware_final_reallocation": reallocation["evidence"],
        }
    )


def _reallocation(*, members: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    return apply_lot_aware_final_reallocation(
        members=[dict(row) for row in members],
        lot_feasibility_rows=[],
        target_gross_exposure=0.8,
        single_name_cap=0.18,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        final_capital_competition_risk_pacing_evidence=_risk_pacing(),
        runtime_test_context=_context(run_id),
    )


def _fresh_target_layers(promoted: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        promoted["capital_competition"]["fresh_target_portfolio_shadow"],
        promoted["lot_aware_final_reallocation"]["capital_competition"]["fresh_target_portfolio_shadow"],
        promoted["pre_lot_capital_competition"]["fresh_target_portfolio_shadow"],
    ]


def _fresh_logic_signature(shadow: Mapping[str, Any]) -> list[dict[str, Any]]:
    signature = []
    for row in shadow.get("rows") or []:
        signature.append(
            {
                "symbol": row.get("symbol"),
                "fresh_target_membership": row.get("fresh_target_membership"),
                "fresh_target_weight": row.get("fresh_target_weight"),
                "fresh_target_weight_reason_codes": row.get("fresh_target_weight_reason_codes"),
                "proposed_semantic_delta": row.get("proposed_semantic_delta"),
                "divergence_class": row.get("divergence_class"),
                "divergence_reason_codes": row.get("divergence_reason_codes"),
                "winner_protection_adjustment": row.get("winner_protection_adjustment"),
                "recent_exit_guard_state": row.get("recent_exit_guard_state"),
                "history_safety_adjustment": row.get("history_safety_adjustment"),
                "safety_display": row.get("safety_display"),
            }
        )
    return signature


def _row_by_symbol(shadow: Mapping[str, Any], symbol: str) -> Mapping[str, Any]:
    for row in shadow.get("rows") or []:
        if str(row.get("symbol") or "") == symbol:
            return row
    raise AssertionError(f"missing row: {symbol}")


def _buy_new(code: str, *, run_id: str, accepted: float) -> dict[str, Any]:
    return {
        "security_code": code,
        "symbol": code,
        "runtime_test_run_id": run_id,
        "business_date": BUSINESS_DATE,
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


def _winner_hold(code: str, *, run_id: str) -> dict[str, Any]:
    return {
        "security_code": code,
        "symbol": code,
        "runtime_test_run_id": run_id,
        "business_date": BUSINESS_DATE,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "HOLD",
        "semantic_buy_type": "BUY_ADD",
        "position_campaign_id": f"pc-{code}-0001",
        "current_quantity": 100,
        "current_weight": 0.2,
        "target_weight": 0.2,
        "input_opportunity_rank": 2,
        "runtime_opportunity_score": 0.75,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_score": 0.72,
        "entry_admission_action": "ADD_ALLOWED",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "expected_edge_improvement_state": "IMPROVING",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "source_pm_reason_codes": ["winner_profit_protection_hold", "strong_trend_continuation"],
        "add_investment_evidence": {
            "business_date": BUSINESS_DATE,
            "position_campaign_id": f"pc-{code}-0001",
            "incremental_value": {"status": "PASS", "state": "POSITIVE"},
            "no_loss_averaging": {"status": "PASS", "state": "PASS"},
        },
        "phase29_l19_lot_resolution": {
            "one_lot_quantity": 100,
            "one_lot_notional": 100000,
            "final_quantity_delta": 0,
            "one_lot_feasibility_status": "PASS",
            "post_trade_weight": 0.2,
            "safety_hard_cap": 0.25,
        },
        "target_weight_authority": {"single_name_weight_cap": 0.18},
        "target_weight_resolution": {"cap_applied": False},
    }


def _context(run_id: str) -> dict[str, str]:
    return {
        "run_id": run_id,
        "evidence_root": f"reports/runtime_tests/runs/{run_id}",
        "business_date": BUSINESS_DATE,
    }


def _risk_pacing() -> dict[str, str]:
    return {"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"}
