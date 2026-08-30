from __future__ import annotations

from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy.sell_semantic_state import (
    CONFIRMED_DETERIORATION,
    DEFENSIVE_ONLY,
    ESCALATION_REASON_CODE,
    EXIT_GRADE,
    HEALTHY_OR_RECOVERING,
    PERSISTENT_DETERIORATION,
    SOFT_DETERIORATION_ACTIVE,
    SOFT_DETERIORATION_CLOSED,
    SOFT_DETERIORATION_PERSISTENT,
    TERMINAL_BREAKDOWN,
    WEAKENING_BUT_INTACT,
)


def test_phase32_x_65500_shape_recovery_closes_old_episode_before_new_reduce() -> None:
    recovery = _apply(_position("65500", action="HOLD", prior_dates=["2022-10-11"], reset_date=None))
    assert recovery["action"] == "HOLD"
    assert recovery["canonical_sell_state"] == HEALTHY_OR_RECOVERING
    assert recovery["soft_deterioration_episode_state"] == SOFT_DETERIORATION_CLOSED
    assert recovery["prior_soft_deterioration_cleared"] is True

    new_reduce = _apply(
        _position(
            "65500",
            action="REDUCE",
            prior_dates=["2022-10-11"],
            reset_date="2022-10-21",
            current_campaign_relative_return=-0.04,
        )
    )
    assert new_reduce["action"] == "REDUCE"
    assert new_reduce["canonical_sell_state"] == WEAKENING_BUT_INTACT
    assert new_reduce["soft_deterioration_episode_state"] == SOFT_DETERIORATION_ACTIVE
    assert new_reduce["prior_unrepresentable_reduce_count"] == 0


def test_phase32_x_91070_shape_new_episode_requires_fresh_confirmation() -> None:
    row = _apply(
        _position(
            "91070",
            action="REDUCE",
            prior_dates=["2022-10-17"],
            reset_date="2022-10-20",
            current_campaign_relative_return=0.05,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["soft_deterioration_episode_state"] == SOFT_DETERIORATION_ACTIVE
    assert row["exit_confirmation_state"] == DEFENSIVE_ONLY
    assert ESCALATION_REASON_CODE not in row["reason_codes"]


def test_phase32_x_45840_shape_long_hold_recovery_keeps_old_episode_inactive() -> None:
    row = _apply(
        _position(
            "45840",
            action="REDUCE",
            prior_dates=["2022-11-15"],
            reset_date="2022-11-29",
            current_campaign_relative_return=0.03,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["prior_soft_deterioration_cleared"] is True
    assert row["prior_unrepresentable_reduce_count"] == 0
    assert row["soft_deterioration_episode_id"].endswith(":2022-09-14")


def test_phase32_x_15180_shape_later_soft_deterioration_gets_new_episode_identity() -> None:
    old = _apply(_position("15180", action="REDUCE", prior_dates=[], current_campaign_relative_return=0.01))
    later = _apply(
        _position(
            "15180",
            action="REDUCE",
            prior_dates=["2022-11-15"],
            reset_date="2022-11-18",
            current_campaign_relative_return=0.04,
        ),
        business_date="2022-11-21",
    )

    assert old["soft_deterioration_episode_id"] != later["soft_deterioration_episode_id"]
    assert later["soft_deterioration_episode_state"] == SOFT_DETERIORATION_ACTIVE
    assert later["exit_confirmation_state"] == DEFENSIVE_ONLY


def test_phase32_x_61440_shape_december_episode_does_not_authorize_january_exit() -> None:
    row = _apply(
        _position(
            "61440",
            action="REDUCE",
            prior_dates=["2022-12-21"],
            reset_date="2023-01-06",
            current_campaign_relative_return=0.02,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["prior_unrepresentable_reduce_count"] == 0
    assert row["soft_deterioration_episode_state"] == SOFT_DETERIORATION_ACTIVE
    assert row["exit_confirmation_state"] == DEFENSIVE_ONLY


def test_phase32_x_89180_hard_stop_exits_immediately() -> None:
    row = _apply(_position("89180", action="EXIT", reasons=["hard_stop_current_return"], current_campaign_relative_return=-0.10))

    assert row["action"] == "EXIT"
    assert row["canonical_sell_state"] == EXIT_GRADE
    assert row["hard_deterioration_present"] is True
    assert row["exit_confirmation_state"] == TERMINAL_BREAKDOWN


def test_phase32_x_terminal_safety_broker_and_corporate_action_bypass_recovery_logic() -> None:
    for reason in ("safety_hard_constraint", "broker_block", "corporate_action_block", "severe_liquidity_failure"):
        row = _apply(
            _position(
                "89180",
                action="EXIT",
                reasons=[reason],
                prior_dates=["2022-10-03"],
                reset_date="2022-10-04",
                current_campaign_relative_return=0.03,
            )
        )

        assert row["action"] == "EXIT"
        assert row["hard_deterioration_present"] is True
        assert row["exit_confirmation_state"] == TERMINAL_BREAKDOWN


def test_phase32_x_33580_shape_no_recovery_confirmed_persistent_exit_remains_valid() -> None:
    row = _apply(
        _position(
            "33580",
            action="REDUCE",
            prior_dates=["2022-10-18"],
            current_campaign_relative_return=-0.05,
        )
    )

    assert row["action"] == "EXIT"
    assert row["canonical_sell_state"] == PERSISTENT_DETERIORATION
    assert row["soft_deterioration_episode_state"] == SOFT_DETERIORATION_PERSISTENT
    assert row["exit_confirmation_state"] == CONFIRMED_DETERIORATION


def test_phase32_x_59860_shape_reduce_to_exit_without_recovery_still_possible() -> None:
    row = _apply(
        _position(
            "59860",
            action="REDUCE",
            prior_dates=["2022-10-17"],
            current_campaign_relative_return=-0.02,
        )
    )

    assert row["action"] == "EXIT"
    assert row["exit_confirmation_state"] == CONFIRMED_DETERIORATION
    assert ESCALATION_REASON_CODE in row["reason_codes"]


def test_phase32_x_zero_lot_reduce_records_episode_without_terminal_authority() -> None:
    row = _apply(_position("76470", action="REDUCE", current_campaign_relative_return=0.01))

    assert row["action"] == "REDUCE"
    assert row["soft_deterioration_episode_state"] == SOFT_DETERIORATION_ACTIVE
    assert row["zero_lot_reduce_persistence_scope"] == "ACTIVE_SOFT_EPISODE_ONLY"
    assert row["exit_confirmation_state"] == DEFENSIVE_ONLY
    assert row["canonical_sell_semantic_evidence"]["representability_family"] == "DISCRETE_LOT"


def test_phase32_x_executed_reduce_is_distinguishable_from_zero_lot_persistence() -> None:
    row = _apply(_position("94320", action="REDUCE", current_quantity=1000, current_campaign_relative_return=-0.03))

    assert row["action"] == "REDUCE"
    assert row["canonical_sell_semantic_evidence"]["representability_family"] == "REPRESENTABLE"
    assert row["zero_lot_reduce_persistence_scope"] == "NOT_APPLICABLE"
    assert row["soft_deterioration_episode_state"] == SOFT_DETERIORATION_ACTIVE


def test_phase32_x_pm_add_closes_episode_without_downstream_buy_add_fill() -> None:
    row = _apply(
        _position(
            "99840",
            action="ADD",
            reasons=["strong_trend_continuation", "opportunity_rank_still_high"],
            prior_dates=["2022-10-31"],
            hold_status="PASS",
            add_status="PASS",
            current_campaign_relative_return=0.12,
        )
    )

    assert row["action"] == "ADD"
    assert row["soft_deterioration_episode_state"] == SOFT_DETERIORATION_CLOSED
    assert row["episode_deescalation_reason"] == "RENEWED_STRENGTH_CONFIRMED"
    assert row["canonical_sell_semantic_evidence"]["future_information_used"] is False


def _apply(position: dict, *, business_date: str = "2022-09-14") -> dict:
    positions, _ = position_management._apply_canonical_sell_semantics([position], business_date=business_date)
    return positions[0]


def _position(
    symbol: str,
    *,
    action: str,
    reasons: list[str] | None = None,
    prior_dates: list[str] | None = None,
    reset_date: str | None = None,
    hold_status: str = "PASS",
    add_status: str = "NO_ADD",
    current_campaign_relative_return: float | None = None,
    current_quantity: int = 100,
) -> dict:
    reasons = reasons or (
        ["structured_hold_worthiness_pass", "trend_continuation"]
        if action == "HOLD"
        else ["strong_trend_continuation", "opportunity_rank_still_high"]
        if action == "ADD"
        else ["risk_increased_but_trend_not_broken"]
    )
    prior_dates = prior_dates or []
    prior_summary = {
        "event_count": len(prior_dates),
        "prior_unrepresentable_reduce_dates": prior_dates,
        "last_reduce_date": prior_dates[-1] if prior_dates else None,
        "last_recovery_reset_date": reset_date,
        "decision_evidence_not_execution": True,
        "future_information_used": False,
    }
    return {
        "position_id": f"pm-{symbol}",
        "security_code": symbol,
        "position_campaign_id": f"campaign-{symbol}",
        "action": action,
        "intensity": "NONE" if action in {"HOLD", "ADD", "EXIT"} else "LIGHT",
        "confidence": 0.7,
        "reason_codes": reasons,
        "adapter_source_contract": {
            "business_date": "2022-09-14",
            "position_state_as_of": "2022-09-14",
            "valuation_date": "2022-09-14",
            "quantity": current_quantity,
        },
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "strategy_intelligence_current_campaign_relative_return": current_campaign_relative_return,
        "strategy_intelligence_profit_protection_status": "OBSERVED",
        "strategy_intelligence_profit_protection_evidence": {
            "status": "OBSERVED",
            "continuation_deterioration_connection": ["WEAK"] if action == "REDUCE" else [],
            "downside_risk_rise_connection": ["ELEVATED_RISK"] if action == "REDUCE" else [],
            "future_information_used": False,
        },
        "strategy_intelligence_hold_worthiness_evidence": {
            "status": hold_status,
            "campaign_identity_authority_status": "COMPLETE",
            "reduce_history_summary": {"event_count": len(prior_dates)},
            "prior_unrepresentable_reduce_summary": prior_summary,
            "reason_codes": ["structured_hold_worthiness_pass", "trend_continuation"] if action == "HOLD" else [],
            "future_information_used": False,
        },
        "strategy_intelligence_add_worthiness_evidence": {
            "status": add_status,
            "campaign_identity_authority_status": "COMPLETE",
            "reduce_history_summary": {"event_count": len(prior_dates)},
            "prior_unrepresentable_reduce_summary": prior_summary,
            "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high"] if action == "ADD" else [],
            "future_information_used": False,
        },
        "strategy_intelligence_not_action_authority": True,
        "strategy_intelligence_production_evidence": True,
    }
