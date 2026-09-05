from __future__ import annotations

from ai_fund_lab_v2.strategy import marginal_capital_value
from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


def test_phase32_gd_fresh_target_shadow_is_non_authoritative_and_uses_one_ncu_comparator() -> None:
    shadow = _fresh_target([_buy_new("7203", rank=1), _buy_add("9432", rank=2)])

    assert shadow["schema_version"] == "fresh_target_portfolio_shadow.v1"
    assert shadow["authoritative_consumer_count"] == 0
    assert shadow["action_authority"] is False
    assert shadow["quantity_authority"] is False
    assert shadow["order_authority"] is False
    assert shadow["production_allocation_consumer"] is False
    assert shadow["runtime_planning_consumer"] is False
    assert shadow["ncu_comparator_instance_count"] == 1
    assert shadow["contract_flags"]["uses_existing_ncu_comparator"] is True
    assert shadow["zero_tolerance_assertions"]["authoritative_consumer_count"] == 0
    assert shadow["zero_tolerance_assertions"]["runtime_authority_leak_count"] == 0
    assert shadow["zero_tolerance_assertions"]["future_information_used_count"] == 0
    assert shadow["future_information_used"] is False
    assert shadow["historical_outcome_used"] is False


def test_phase32_gd_incumbent_and_flat_same_evidence_receive_same_fresh_target() -> None:
    flat = _buy_new("7203", rank=1)
    held = _buy_add("9432", rank=1)
    held.update(
        {
            "prior_exit_business_date": "2024-01-15",
            "strategy_intelligence_add_history_count": 9,
            "average_cost": 1800.0,
            "old_campaign_pnl": -100000,
            "old_closed_campaign_id": "pc-old",
            "current_weight": 0.02,
        }
    )

    rows = _rows(_fresh_target([flat, held]))

    assert rows["7203"]["fresh_target_weight"] == rows["9432"]["fresh_target_weight"]
    held_history = rows["9432"]["history_safety_adjustment"]
    assert held_history["old_ownership_used_for_target"] is False
    assert held_history["prior_add_count_used_for_target"] is False
    assert held_history["average_cost_used_for_target"] is False
    assert rows["9432"]["current_opportunity_evidence"]["closed_campaign_used_for_target"] is False
    assert rows["9432"]["option_type"] == "BUY_ADD_CONTEXT"
    assert rows["7203"]["option_type"] == "BUY_NEW_CONTEXT"
    assert _fresh_target([flat, held])["zero_tolerance_assertions"]["closed_campaign_leak_count"] == 0
    assert _fresh_target([flat, held])["zero_tolerance_assertions"]["permanent_history_penalty_signal_count"] == 0


def test_phase32_gd_recent_exit_guard_is_bounded_exception_without_old_history_penalty() -> None:
    recent = _buy_new("8306", rank=1)
    recent.update(
        {
            "prior_exit_business_date": "2026-07-14",
            "business_days_since_exit": 1,
            "recent_exit_guard_state": "ACTIVE_RECENT_EXIT_GUARD",
            "recent_exit_guard_status": "REVIEW_REQUIRED",
            "reentry_reason_codes": ["RECENT_EXIT_CHURN_GUARD_ACTIVE"],
        }
    )

    row = _rows(_fresh_target([recent]))["8306"]

    assert row["fresh_target_membership"] is False
    assert row["fresh_target_weight"] == 0.0
    assert row["recent_exit_guard_state"]["bounded_exception_only"] is True
    assert row["recent_exit_guard_state"]["old_ownership_used_for_target"] is False
    assert row["divergence_class"] == "RECENT_EXIT_GUARD"


def test_phase32_gd_winner_protection_and_terminal_deterioration_are_observability_only() -> None:
    winner_hold = _buy_add("9432", rank=1)
    winner_hold.update({"pm_action": "HOLD", "source_pm_reason_codes": ["winner_profit_protection_hold"], "current_weight": 0.20})
    terminal = _buy_add("6758", rank=2)
    terminal.update({"pm_action": "EXIT", "source_pm_reason_codes": ["hard_stop_terminal_exit"]})

    rows = _rows(_fresh_target([winner_hold, terminal]))

    assert rows["9432"]["divergence_class"] == "WINNER_PROTECTION_CONFLICT"
    assert rows["9432"]["winner_protection_adjustment"]["creates_reduce_or_exit_authority"] is False
    assert rows["6758"]["terminal_deterioration_precedence"] == "PM/SAFETY"
    assert rows["6758"]["final_shadow_action"] == "PM_SAFETY_TERMINAL_PRECEDENCE"


def test_phase32_gd_add_safety_display_preserves_g129_and_blocks_bypass_count() -> None:
    blocked_add = _buy_add("9432", rank=1)
    blocked_add["add_investment_evidence"]["incremental_value"] = {"status": "FAIL_CLOSED", "state": "NEGATIVE"}
    blocked_add["phase29_l19_lot_resolution"]["final_quantity_delta"] = 0

    shadow = _fresh_target([blocked_add])
    row = _rows(shadow)["9432"]

    assert row["safety_display"]["g129_increment_scope"] == "ORDER_INCREMENT_SCOPED"
    assert row["safety_display"]["add_safety_bypass"] is False
    assert shadow["diagnostics"]["add_safety_bypass_count"] == 0
    assert shadow["zero_tolerance_assertions"]["add_safety_bypass_count"] == 0
    assert shadow["zero_tolerance_assertions"]["G129_regression_count"] == 0


def test_phase32_gd_cash_row_and_stability_metrics_are_materialized() -> None:
    shadow = _fresh_target([_buy_new("7203", rank=1), _buy_new("8306", rank=2)])
    rows = _rows(shadow)

    assert "CASH" in rows
    assert rows["CASH"]["option_type"] == "CASH"
    assert rows["CASH"]["fresh_target_weight_reason_codes"] == ["CASH_IS_FIRST_CLASS_FRESH_TARGET_ROW"]
    assert "membership_flip_count" in shadow["diagnostics"]
    assert "weight_direction_flip_count" in shadow["diagnostics"]
    assert "turnover_pressure" in shadow["diagnostics"]


def test_phase32_gd_pc_integration_preserves_production_competition_and_embeds_shadow() -> None:
    members = [_buy_new("7203", rank=1, accepted=0.04), _buy_add("9432", rank=2, accepted=0.02)]
    result = build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.8,
        total_target_weight=0.06,
        business_date="2026-07-15",
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
    )

    competitors = {(row["competitor_type"], row["symbol"]): row for row in result["competitors"]}
    assert competitors[("NEW_BUY", "7203")]["accepted_weight"] == 0.04
    assert competitors[("ADD", "9432")]["accepted_weight"] == 0.02
    assert result["authority"]["fresh_target_portfolio_shadow_authoritative_consumer_count"] == 0
    assert result["authority"]["fresh_target_portfolio_shadow_production_consumer"] is False
    shadow = result["fresh_target_portfolio_shadow"]
    assert shadow["schema_version"] == "fresh_target_portfolio_shadow.v1"
    assert shadow["zero_tolerance_assertions"]["runtime_authority_leak_count"] == 0


def _fresh_target(members: list[dict[str, object]]) -> dict[str, object]:
    unified = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=members,
        competitors=[
            _production_competitor("NEW_BUY", row["symbol"], accepted=float(row.get("accepted_buy_new_weight") or 0.0))
            for row in members
            if not row.get("current_position")
        ]
        + [
            _production_competitor("ADD", row["symbol"], accepted=float(row.get("accepted_incremental_weight") or 0.0))
            for row in members
            if row.get("current_position")
        ],
        cash_evidence=_cash_evidence(),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
    )
    return marginal_capital_value.build_fresh_target_portfolio_shadow(
        business_date="2026-07-15",
        feature_date="2026-07-15",
        members=members,
        unified_marginal_capital_shadow=unified,
        cash_evidence=_cash_evidence(),
        target_gross_exposure=0.8,
    )


def _rows(shadow: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(row["symbol"]): row for row in shadow["rows"]}  # type: ignore[index]


def _buy_new(code: str, *, rank: int, accepted: float = 0.04) -> dict[str, object]:
    return {
        "security_code": code,
        "symbol": code,
        "business_date": "2026-07-15",
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "semantic_buy_type": "BUY_NEW",
        "source_candidate_id": f"candidate-{code}",
        "source_opportunity_id": f"opportunity-{code}",
        "input_opportunity_rank": rank,
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


def _buy_add(code: str, *, rank: int, accepted: float = 0.02) -> dict[str, object]:
    return {
        "security_code": code,
        "symbol": code,
        "business_date": "2026-07-15",
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "semantic_buy_type": "BUY_ADD",
        "position_campaign_id": f"pc-{code}-0001",
        "current_position_campaign_id": f"pc-{code}-0001",
        "source_pm_decision_ref": f"pm-2026-07-15-{code}-add",
        "source_pm_reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
        "current_quantity": 100,
        "current_weight": 0.03,
        "target_weight": 0.03 + accepted,
        "requested_incremental_weight": 0.03,
        "accepted_incremental_weight": accepted,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_score": 0.72,
        "entry_admission_action": "ADD_ALLOWED",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
        "same_campaign_continuation_status": "PASS",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "input_opportunity_rank": rank,
        "runtime_opportunity_score": 0.8,
        "add_investment_evidence": _add_evidence(code),
        "phase29_l19_lot_resolution": {
            "one_lot_quantity": 100,
            "one_lot_notional": 90000,
            "final_quantity_delta": 100,
            "one_lot_feasibility_status": "PASS",
            "post_trade_weight": 0.05,
            "safety_hard_cap": 0.25,
        },
        "target_weight_authority": {"single_name_weight_cap": 0.18},
        "target_weight_resolution": {"cap_applied": False},
    }


def _production_competitor(competitor_type: str, code: str, *, accepted: float) -> dict[str, object]:
    return {
        "competitor_type": competitor_type,
        "symbol": code,
        "status": "COMPETITOR_SELECTED" if accepted > 0 else "COMPETITOR_REJECTED_RECONSIDERABLE",
        "accepted_weight": accepted,
        "reason_codes": ["COMPETITOR_SELECTED"] if accepted > 0 else ["NO_POSITIVE_DELTA"],
    }


def _add_evidence(code: str) -> dict[str, object]:
    return {
        "business_date": "2026-07-15",
        "position_campaign_id": f"pc-{code}-0001",
        "campaign_continuation": {"status": "PASS", "state": "PASS", "position_campaign_id": f"pc-{code}-0001"},
        "expected_edge": {"status": "PASS", "state": "IMPROVING"},
        "incremental_value": {"status": "PASS", "state": "POSITIVE"},
        "opportunity_cost": {"status": "PASS", "state": "PASS"},
        "no_loss_averaging": {"status": "PASS", "state": "PASS"},
        "temporal_authority": {"future_evidence_used": False, "point_in_time": True},
    }


def _cash_evidence() -> dict[str, object]:
    return {
        "schema_version": "cash_competitor_evidence.v1",
        "business_date": "2026-07-15",
        "cash_competitor_evidence_hash": "cash-hash",
        "evidence_completeness": "COMPLETE",
        "cash_preference_semantic": "VALID_OPTIONALITY",
        "current_cash_weight": 0.5,
        "remaining_cash_weight": 0.1,
        "reason_codes": ["VALID_POLICY_RESERVE"],
    }
