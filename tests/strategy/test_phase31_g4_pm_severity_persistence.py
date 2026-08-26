from __future__ import annotations

from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy.sell_semantic_state import (
    FIRST_OBSERVATION,
    HEALTHY_OR_RECOVERING,
    PM_SEVERITY_CAUTION,
    PM_SEVERITY_DEFENSIVE,
    PM_SEVERITY_EXIT_CANDIDATE,
    PM_SEVERITY_NORMAL,
    PM_SEVERITY_UNRESOLVED,
    PERSISTENT,
    RECOVERED,
    REPEATED_OBSERVATION,
    UNRESOLVED,
    WEAKENING_BUT_INTACT,
)


def test_phase31_g4_profitable_temporary_weakening_is_caution_without_exit() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            current_campaign_relative_return=0.08,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == WEAKENING_BUT_INTACT
    assert row["pm_severity"] == PM_SEVERITY_CAUTION
    assert row["persistence_state"] == FIRST_OBSERVATION
    assert row["pm_severity_evidence"]["campaign_economics"]["direct_exit_rule_applied"] is False
    assert row["pm_severity_evidence"]["missing_evidence_auto_exit"] is False


def test_phase31_g4_recovery_deescalates_and_resets_stale_debt() -> None:
    row = _apply(
        _position(
            action="HOLD",
            intensity="NONE",
            reasons=["structured_hold_worthiness_pass", "trend_continuation"],
            prior_reduce_count=3,
            hold_status="PASS",
            current_campaign_relative_return=0.04,
        )
    )

    evidence = row["pm_severity_evidence"]
    assert row["action"] == "HOLD"
    assert row["canonical_sell_state"] == HEALTHY_OR_RECOVERING
    assert row["pm_severity"] == PM_SEVERITY_NORMAL
    assert row["persistence_state"] == RECOVERED
    assert evidence["recovery_deescalation_evidence"]["deescalated"] is True


def test_phase31_g4_persistent_discrete_loser_reaches_exit_candidate_and_pm_gate() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=1,
            current_campaign_relative_return=-0.07,
        )
    )

    assert row["action"] == "EXIT"
    assert row["pm_severity"] == PM_SEVERITY_EXIT_CANDIDATE
    assert row["persistence_state"] == PERSISTENT
    assert "strict_prior_persistence_present" in row["pm_severity_reasons"]
    assert row["pm_severity_evidence"]["severity_action_authority"] == "PM_ONLY"


def test_phase31_g4_repeated_reduce_count_alone_does_not_exit_profitable_winner() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=3,
            current_campaign_relative_return=0.12,
            current_quantity=1000,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == WEAKENING_BUT_INTACT
    assert row["pm_severity"] == PM_SEVERITY_CAUTION
    assert row["persistence_state"] == REPEATED_OBSERVATION
    assert row["pm_severity_evidence"]["persistence_evidence"]["reduce_count_direct_exit_rule_applied"] is False


def test_phase31_g4_regime_only_adversity_cannot_force_exit() -> None:
    row = _apply(
        _position(
            action="HOLD",
            intensity="NONE",
            reasons=["structured_hold_worthiness_pass"],
            hold_status="PASS",
            current_campaign_relative_return=0.02,
            market_context_regime="BEAR",
        )
    )

    assert row["action"] == "HOLD"
    assert row["pm_severity"] == PM_SEVERITY_NORMAL
    assert row["pm_severity_evidence"]["regime_modifier"]["direct_exit_rule_applied"] is False


def test_phase31_g4_same_day_self_count_remains_first_observation() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=0,
            current_campaign_relative_return=-0.03,
        )
    )

    evidence = row["pm_severity_evidence"]
    assert row["action"] == "REDUCE"
    assert row["pm_severity"] == PM_SEVERITY_DEFENSIVE
    assert row["persistence_state"] == FIRST_OBSERVATION
    assert evidence["persistence_evidence"]["same_day_self_count"] == 0


def test_phase31_g4_cross_campaign_history_is_not_leaked() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=0,
            current_campaign_relative_return=-0.05,
            position_campaign_id="campaign-61750-new",
        )
    )

    evidence = row["pm_severity_evidence"]
    assert row["action"] == "REDUCE"
    assert row["persistence_state"] == FIRST_OBSERVATION
    assert evidence["persistence_evidence"]["cross_campaign_history_leak"] == 0


def test_phase31_g4_missing_evidence_is_unresolved_without_auto_exit() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=[],
            campaign_identity_status="UNRESOLVED",
            current_campaign_relative_return=None,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == UNRESOLVED
    assert row["pm_severity"] == PM_SEVERITY_UNRESOLVED
    assert row["pm_severity_evidence"]["missing_evidence_auto_exit"] is False


def _apply(position: dict) -> dict:
    positions, reasons = position_management._apply_canonical_sell_semantics([position], business_date="2022-09-14")
    if positions[0]["action"] != "EXIT":
        assert reasons == []
    return positions[0]


def _position(
    *,
    action: str,
    intensity: str = "LIGHT",
    reasons: list[str] | None = None,
    prior_reduce_count: int = 0,
    hold_status: str = "REVIEW_REQUIRED",
    campaign_identity_status: str = "COMPLETE",
    position_state_as_of: str = "2022-09-14",
    current_campaign_relative_return: float | None = None,
    current_quantity: int = 100,
    position_campaign_id: str = "campaign-61750",
    market_context_regime: str | None = None,
) -> dict:
    return {
        "position_id": "pm-61750",
        "security_code": "61750",
        "position_campaign_id": position_campaign_id,
        "action": action,
        "intensity": intensity,
        "confidence": 0.7,
        "reason_codes": reasons or [],
        "market_context_regime": market_context_regime,
        "adapter_source_contract": {
            "business_date": "2022-09-14",
            "position_state_as_of": position_state_as_of,
            "valuation_date": "2022-09-14",
            "quantity": current_quantity,
        },
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "strategy_intelligence_profit_protection_status": "OBSERVED",
        "strategy_intelligence_current_campaign_relative_return": current_campaign_relative_return,
        "strategy_intelligence_profit_protection_evidence": {
            "status": "OBSERVED",
            "continuation_deterioration_connection": ["WEAK"] if action == "REDUCE" else [],
            "downside_risk_rise_connection": ["ELEVATED_RISK"] if action == "REDUCE" else [],
            "future_information_used": False,
        },
        "strategy_intelligence_hold_worthiness_evidence": {
            "status": hold_status,
            "campaign_identity_authority_status": campaign_identity_status,
            "reduce_history_summary": {"event_count": prior_reduce_count},
            "reason_codes": [],
            "future_information_used": False,
        },
        "strategy_intelligence_add_worthiness_evidence": {
            "status": "NO_ADD",
            "campaign_identity_authority_status": campaign_identity_status,
            "reduce_history_summary": {"event_count": prior_reduce_count},
            "reason_codes": [],
            "future_information_used": False,
        },
        "strategy_intelligence_not_action_authority": True,
        "strategy_intelligence_production_evidence": True,
    }
