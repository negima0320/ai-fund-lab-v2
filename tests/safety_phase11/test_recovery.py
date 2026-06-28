from ai_fund_lab_v2.safety_phase11.models import SafetyState
from ai_fund_lab_v2.safety_phase11.recovery import RecoveryCheckInput, RecoveryEvaluator
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine


def _recovery_input(state=SafetyState.BUY_STOP, **overrides):
    data = {
        "current_state": state,
        "manual_emergency_flag_active": False,
        "market_summary": {
            "severe_crash": False,
            "stable_days": 5,
            "candidate_universe_drawdown_improved": True,
            "crash_issue_ratio_declined": True,
            "extreme_down_ratio_declined": True,
        },
        "quote_freshness": "fresh",
        "broker_snapshot_freshness": "fresh",
        "broker_divergence": "none",
        "duplicate_active_order_risk": False,
        "daily_loss_pct": "0.00",
        "runtime_state_valid": True,
        "persistence_violation_suspected": False,
        "latest_safety_report_path": "reports/safety/phase11/2026-06-29_safety_report.json",
    }
    data.update(overrides)
    return RecoveryCheckInput(**data)


def test_buy_stop_can_become_recovery_candidate():
    decision = RecoveryEvaluator().evaluate(_recovery_input(SafetyState.BUY_STOP))
    assert decision.recovery_candidate is True
    assert decision.next_recommended_state is SafetyState.RECOVERY_CANDIDATE
    assert decision.requires_human_review is True
    assert decision.auto_recovery_executed is False


def test_emergency_stop_can_become_recovery_candidate():
    decision = RecoveryEvaluator().evaluate(_recovery_input(SafetyState.EMERGENCY_STOP))
    assert decision.recovery_candidate is True
    assert decision.next_recommended_state is SafetyState.RECOVERY_CANDIDATE


def test_missing_conditions_do_not_create_recovery_candidate():
    decision = RecoveryEvaluator().evaluate(_recovery_input(latest_safety_report_path="", quote_freshness="stale"))
    assert decision.recovery_candidate is False
    assert "latest_safety_report_exists" in decision.missing_evidence
    assert "quotes_fresh" in decision.missing_evidence
    assert "recovery_evidence_missing" in decision.blocking_reasons


def test_recovery_candidate_does_not_auto_return_to_normal():
    decision = RecoveryEvaluator().evaluate(_recovery_input())
    assert decision.next_recommended_state is SafetyState.RECOVERY_CANDIDATE
    machine = SafetyStateMachine(SafetyState.RECOVERY_CANDIDATE)
    next_machine, result = machine.transition_to(SafetyState.NORMAL)
    assert result.allowed is False
    assert next_machine.current_state is SafetyState.RECOVERY_CANDIDATE


def test_forbidden_direct_normal_transitions_remain_blocked():
    for state in (SafetyState.BUY_STOP, SafetyState.EMERGENCY_STOP, SafetyState.RECOVERY_CANDIDATE):
        machine = SafetyStateMachine(state)
        next_machine, result = machine.transition_to(SafetyState.NORMAL)
        assert result.allowed is False
        assert next_machine.current_state is state
