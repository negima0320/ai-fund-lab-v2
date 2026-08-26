from __future__ import annotations

from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy.sell_semantic_state import (
    ESCALATION_REASON_CODE,
    EXIT_GRADE,
    HEALTHY_OR_RECOVERING,
    PERSISTENT_DETERIORATION,
    UNRESOLVED,
    WEAKENING_BUT_INTACT,
)


def test_phase31_f1f_first_one_lot_weakening_reduce_does_not_exit() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                action="REDUCE",
                reasons=["risk_increased_but_trend_not_broken"],
                prior_reduce_count=0,
            )
        ],
        business_date="2022-09-14",
    )

    row = positions[0]
    assert reasons == []
    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == WEAKENING_BUT_INTACT
    assert ESCALATION_REASON_CODE not in row["reason_codes"]


def test_phase31_f1f_persistent_discrete_lot_reduce_escalates_inside_pm() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                action="REDUCE",
                reasons=["risk_increased_but_trend_not_broken"],
                prior_reduce_count=1,
            )
        ],
        business_date="2022-09-14",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == [ESCALATION_REASON_CODE]
    assert row["action"] == "EXIT"
    assert row["intensity"] == "NONE"
    assert row["canonical_sell_state"] == PERSISTENT_DETERIORATION
    assert row["reason_codes"] == [
        ESCALATION_REASON_CODE,
        "risk_increased_but_trend_not_broken",
    ]
    assert evidence["original_pm_action"] == "REDUCE"
    assert evidence["final_pm_action"] == "EXIT"
    assert evidence["escalation_decision"] == "PM_EXIT"
    assert evidence["representability_family"] == "DISCRETE_LOT"
    assert evidence["minimum_notional_flag"] is False
    assert evidence["pit_proof"]["pit_validation_state"] == "PASS"


def test_phase31_f1f_recovery_reset_blocks_reduce_to_exit_escalation() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                action="HOLD",
                intensity="NONE",
                reasons=["structured_hold_worthiness_pass", "trend_continuation"],
                prior_reduce_count=2,
                hold_status="PASS",
            )
        ],
        business_date="2022-09-15",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == []
    assert row["action"] == "HOLD"
    assert row["canonical_sell_state"] == HEALTHY_OR_RECOVERING
    assert evidence["recovery_state"] == "RECOVERY_PRESENT"
    assert evidence["parameter_resolution_status"] == "RESET"
    assert evidence["final_pm_action"] == "HOLD"


def test_phase31_f1f_existing_pm_exit_is_preserved() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [_position(action="EXIT", intensity="NONE", reasons=["trend_and_opportunity_broken"])],
        business_date="2022-09-14",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == []
    assert row["action"] == "EXIT"
    assert row["canonical_sell_state"] == EXIT_GRADE
    assert evidence["escalation_decision"] == "PRESERVE_BASELINE"


def test_phase31_f1f_minimum_notional_reduce_is_unresolved_and_not_escalated() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                action="REDUCE",
                reasons=[
                    "risk_increased_but_trend_not_broken",
                    "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL",
                ],
                prior_reduce_count=1,
            )
        ],
        business_date="2022-09-14",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == []
    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == UNRESOLVED
    assert evidence["representability_family"] == "MINIMUM_NOTIONAL"
    assert evidence["parameter_resolution_status"] == "MINIMUM_NOTIONAL_POLICY_UNRESOLVED"


def test_phase31_f1f_missing_pit_proof_fails_closed_without_exit() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                action="REDUCE",
                reasons=["risk_increased_but_trend_not_broken"],
                prior_reduce_count=1,
                position_state_as_of="2022-09-15",
            )
        ],
        business_date="2022-09-14",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == []
    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == UNRESOLVED
    assert evidence["pit_proof"]["pit_validation_state"] == "FAIL_FUTURE_DATED_EVIDENCE"
    assert evidence["parameter_resolution_status"] == "PIT_PROOF_FAILED"


def test_phase31_f1f_ambiguous_campaign_fails_closed_without_exit() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                action="REDUCE",
                reasons=["risk_increased_but_trend_not_broken"],
                prior_reduce_count=1,
                campaign_identity_status="UNRESOLVED",
            )
        ],
        business_date="2022-09-14",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == []
    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == UNRESOLVED
    assert evidence["campaign_identity_valid"] is False
    assert evidence["parameter_resolution_status"] == "CAMPAIGN_IDENTITY_UNRESOLVED"


def _position(
    *,
    action: str,
    intensity: str = "LIGHT",
    reasons: list[str] | None = None,
    prior_reduce_count: int = 0,
    hold_status: str = "REVIEW_REQUIRED",
    campaign_identity_status: str = "COMPLETE",
    position_state_as_of: str = "2022-09-14",
) -> dict:
    return {
        "position_id": "pm-61750",
        "security_code": "61750",
        "position_campaign_id": "campaign-61750",
        "action": action,
        "intensity": intensity,
        "confidence": 0.7,
        "reason_codes": reasons or [],
        "adapter_source_contract": {
            "business_date": "2022-09-14",
            "position_state_as_of": position_state_as_of,
            "valuation_date": "2022-09-14",
            "quantity": 100,
        },
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "strategy_intelligence_profit_protection_status": "OBSERVED",
        "strategy_intelligence_profit_protection_evidence": {
            "status": "OBSERVED",
            "continuation_deterioration_connection": ["WEAK"],
            "downside_risk_rise_connection": ["ELEVATED_RISK"],
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
