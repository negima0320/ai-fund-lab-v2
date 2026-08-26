from __future__ import annotations

from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy import sell_semantic_state


def test_phase31_g8_normal_preserves_baseline_action(monkeypatch) -> None:
    monkeypatch.setattr(
        sell_semantic_state,
        "evaluate_position_sell_semantic",
        lambda position, *, business_date: _evidence(
            original_action="HOLD",
            baseline_action="HOLD",
            canonical_state=sell_semantic_state.HEALTHY_OR_RECOVERING,
            severity=sell_semantic_state.PM_SEVERITY_NORMAL,
            persistence=sell_semantic_state.RECOVERED,
            return_side="PROFITABLE",
        ),
    )

    row = _apply(_position(action="HOLD", intensity="NONE"))

    assert row["action"] == "HOLD"
    assert row["intensity"] == "NONE"
    assert row["canonical_sell_semantic_evidence"]["pm_severity_action_mapping_decision"] == "PRESERVE_BASELINE"


def test_phase31_g8_defensive_hold_can_mutate_to_reduce(monkeypatch) -> None:
    monkeypatch.setattr(
        sell_semantic_state,
        "evaluate_position_sell_semantic",
        lambda position, *, business_date: _evidence(
            original_action="HOLD",
            baseline_action="HOLD",
            canonical_state=sell_semantic_state.WEAKENING_BUT_INTACT,
            severity=sell_semantic_state.PM_SEVERITY_DEFENSIVE,
            persistence=sell_semantic_state.FIRST_OBSERVATION,
            return_side="FAILING",
        ),
    )

    row = _apply(_position(action="HOLD", intensity="NONE"))
    evidence = row["canonical_sell_semantic_evidence"]

    assert row["action"] == "REDUCE"
    assert row["intensity"] == "LIGHT"
    assert evidence["baseline_final_pm_action"] == "HOLD"
    assert evidence["final_pm_action"] == "REDUCE"
    assert evidence["pm_severity_action_mapping_connected"] is True
    assert evidence["pm_severity_action_mapping_reason_code"] == position_management.PM_SEVERITY_HOLD_TO_REDUCE_REASON_CODE
    assert position_management.PM_SEVERITY_HOLD_TO_REDUCE_REASON_CODE in row["reason_codes"]


def test_phase31_g8_defensive_first_observation_reduce_does_not_exit(monkeypatch) -> None:
    monkeypatch.setattr(
        sell_semantic_state,
        "evaluate_position_sell_semantic",
        lambda position, *, business_date: _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.WEAKENING_BUT_INTACT,
            severity=sell_semantic_state.PM_SEVERITY_DEFENSIVE,
            persistence=sell_semantic_state.FIRST_OBSERVATION,
            return_side="FAILING",
        ),
    )

    row = _apply(_position(action="REDUCE", intensity="LIGHT"))

    assert row["action"] == "REDUCE"
    assert row["canonical_sell_semantic_evidence"]["pm_severity_action_mapping_decision"] == "PRESERVE_BASELINE"


def test_phase31_g8_exit_candidate_reduce_can_mutate_to_exit_with_canonical_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        sell_semantic_state,
        "evaluate_position_sell_semantic",
        lambda position, *, business_date: _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.EXIT_GRADE,
            severity=sell_semantic_state.PM_SEVERITY_EXIT_CANDIDATE,
            persistence=sell_semantic_state.WORSENING,
            return_side="FAILING",
        ),
    )

    row = _apply(_position(action="REDUCE", intensity="LIGHT"))
    evidence = row["canonical_sell_semantic_evidence"]

    assert row["action"] == "EXIT"
    assert row["intensity"] == "NONE"
    assert evidence["baseline_final_pm_action"] == "REDUCE"
    assert evidence["final_pm_action"] == "EXIT"
    assert evidence["pm_severity_action_mapping_reason_code"] == position_management.PM_SEVERITY_REDUCE_TO_EXIT_REASON_CODE
    assert position_management.PM_SEVERITY_REDUCE_TO_EXIT_REASON_CODE in row["reason_codes"]


def test_phase31_g8_recovery_blocks_stale_exit(monkeypatch) -> None:
    monkeypatch.setattr(
        sell_semantic_state,
        "evaluate_position_sell_semantic",
        lambda position, *, business_date: _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.EXIT_GRADE,
            severity=sell_semantic_state.PM_SEVERITY_EXIT_CANDIDATE,
            persistence=sell_semantic_state.WORSENING,
            return_side="FAILING",
            recovery=True,
        ),
    )

    row = _apply(_position(action="REDUCE", intensity="LIGHT"))

    assert row["action"] == "REDUCE"
    assert row["canonical_sell_semantic_evidence"]["pm_severity_action_mapping_decision"] == "PRESERVE_BASELINE"


def test_phase31_g8_prohibited_deltas_do_not_exit(monkeypatch) -> None:
    cases = [
        _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.WEAKENING_BUT_INTACT,
            severity=sell_semantic_state.PM_SEVERITY_CAUTION,
            persistence=sell_semantic_state.FIRST_OBSERVATION,
            return_side="PROFITABLE",
        ),
        _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.WEAKENING_BUT_INTACT,
            severity=sell_semantic_state.PM_SEVERITY_DEFENSIVE,
            persistence=sell_semantic_state.PERSISTENT,
            return_side="FAILING",
            regime="BEAR",
        ),
        _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.HEALTHY_OR_RECOVERING,
            severity=sell_semantic_state.PM_SEVERITY_DEFENSIVE,
            persistence=sell_semantic_state.WORSENING,
            return_side="FAILING",
        ),
        _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.EXIT_GRADE,
            severity=sell_semantic_state.PM_SEVERITY_EXIT_CANDIDATE,
            persistence=sell_semantic_state.WORSENING,
            return_side="UNKNOWN",
        ),
        _evidence(
            original_action="REDUCE",
            baseline_action="REDUCE",
            canonical_state=sell_semantic_state.EXIT_GRADE,
            severity=sell_semantic_state.PM_SEVERITY_EXIT_CANDIDATE,
            persistence=sell_semantic_state.WORSENING,
            return_side="FAILING",
            campaign_valid=False,
        ),
    ]

    for evidence in cases:
        monkeypatch.setattr(
            sell_semantic_state,
            "evaluate_position_sell_semantic",
            lambda position, *, business_date, evidence=evidence: evidence,
        )
        row = _apply(_position(action="REDUCE", intensity="LIGHT"))
        assert row["action"] == "REDUCE"


def test_phase31_g8_exit_grade_existing_exit_is_preserved() -> None:
    row = _apply(
        _position(
            action="EXIT",
            intensity="NONE",
            reasons=["trend_and_opportunity_broken"],
            current_campaign_relative_return=-0.04,
        )
    )

    assert row["action"] == "EXIT"
    assert row["canonical_sell_state"] == sell_semantic_state.EXIT_GRADE
    assert row["canonical_sell_semantic_evidence"]["pm_severity_action_mapping_decision"] == "PRESERVE_BASELINE"


def test_phase31_g8_profitable_reduce_chain_preserved() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=4,
            current_campaign_relative_return=0.10,
            current_quantity=1000,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["pm_severity"] == sell_semantic_state.PM_SEVERITY_CAUTION
    assert row["canonical_sell_semantic_evidence"]["pm_severity_action_mapping_decision"] == "PRESERVE_BASELINE"


def test_phase31_g8_same_day_and_cross_campaign_protections_remain() -> None:
    same_day = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=0,
            current_campaign_relative_return=-0.03,
        )
    )
    new_campaign = _apply(
        _position(
            action="REDUCE",
            reasons=["risk_increased_but_trend_not_broken"],
            prior_reduce_count=0,
            position_campaign_id="campaign-61750-new",
            current_campaign_relative_return=-0.03,
        )
    )

    assert same_day["action"] == "REDUCE"
    assert same_day["persistence_state"] == sell_semantic_state.FIRST_OBSERVATION
    assert new_campaign["action"] == "REDUCE"
    assert new_campaign["pm_severity_evidence"]["persistence_evidence"]["cross_campaign_history_leak"] == 0


def test_phase31_g8_missing_evidence_no_exit() -> None:
    row = _apply(
        _position(
            action="REDUCE",
            reasons=[],
            campaign_identity_status="UNRESOLVED",
            current_campaign_relative_return=None,
        )
    )

    assert row["action"] == "REDUCE"
    assert row["pm_severity"] == sell_semantic_state.PM_SEVERITY_UNRESOLVED
    assert row["canonical_sell_semantic_evidence"]["pm_severity_action_mapping_decision"] == "PRESERVE_BASELINE"


def _apply(position: dict) -> dict:
    positions, _ = position_management._apply_canonical_sell_semantics([position], business_date="2022-09-14")
    return positions[0]


def _evidence(
    *,
    original_action: str,
    baseline_action: str,
    canonical_state: str,
    severity: str,
    persistence: str,
    return_side: str,
    campaign_valid: bool = True,
    recovery: bool = False,
    pit_state: str = "PASS",
    conflict: bool = False,
    regime: str = "NOT_AVAILABLE",
) -> dict:
    return {
        "contract_version": sell_semantic_state.CONTRACT_VERSION,
        "producer": sell_semantic_state.PRODUCER,
        "business_date": "2022-09-14",
        "symbol": "61750",
        "campaign_id": "campaign-61750",
        "original_pm_action": original_action,
        "canonical_sell_state": canonical_state,
        "canonical_state_reasons": [],
        "recovery_state": "RECOVERY_PRESENT" if recovery else "NO_RECOVERY",
        "recovery_dimensions": {"recovery_present": recovery, "reset_policy": "RESET" if recovery else "PRESERVE"},
        "representability_family": "REPRESENTABLE",
        "minimum_notional_flag": False,
        "campaign_identity_valid": campaign_valid,
        "conflicting_recovery_deterioration_evidence": conflict,
        "pit_proof": {"pit_validation_state": pit_state, "future_information_used": False},
        "parameter_resolution_status": "CANONICAL_EXISTING",
        "pm_severity": severity,
        "pm_severity_reasons": [],
        "persistence_state": persistence,
        "pm_severity_evidence": {
            "contract_version": sell_semantic_state.PM_SEVERITY_CONTRACT_VERSION,
            "producer": sell_semantic_state.PM_SEVERITY_PRODUCER,
            "campaign_economics": {
                "current_campaign_relative_return": -0.03 if return_side == "FAILING" else 0.03 if return_side == "PROFITABLE" else None,
                "campaign_return_side": return_side,
                "direct_exit_rule_applied": False,
            },
            "persistence_evidence": {
                "same_day_self_count": 0,
                "cross_campaign_history_leak": 0,
                "reduce_count_direct_exit_rule_applied": False,
            },
            "recovery_deescalation_evidence": {"deescalated": recovery},
            "regime_modifier": {
                "regime_state": regime,
                "role": "SEVERITY_CONFIRMATION_MODIFIER_ONLY",
                "direct_exit_rule_applied": False,
            },
            "missing_evidence_auto_exit": False,
        },
        "escalation_considered": False,
        "escalation_decision": "PRESERVE_BASELINE",
        "final_pm_action": baseline_action,
        "escalation_reason_code": "",
        "future_information_used": False,
        "outcome_used_for_parameter_selection": False,
    }


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
