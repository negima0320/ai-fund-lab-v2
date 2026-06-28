from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine


def test_state_machine_allows_normal_to_warning_and_buy_stop_to_recovery():
    machine = SafetyStateMachine(SafetyState.NORMAL)
    next_machine, result = machine.transition_to(SafetyState.WARNING)
    assert result.allowed is True
    assert next_machine.current_state is SafetyState.WARNING

    machine = SafetyStateMachine(SafetyState.BUY_STOP)
    next_machine, result = machine.transition_to(SafetyState.RECOVERY_CANDIDATE)
    assert result.allowed is True
    assert next_machine.current_state is SafetyState.RECOVERY_CANDIDATE


def test_buy_stop_cannot_go_directly_to_normal():
    machine = SafetyStateMachine(SafetyState.BUY_STOP)
    next_machine, result = machine.transition_to(SafetyState.NORMAL)
    assert result.allowed is False
    assert result.decision is SafetyDecision.REVIEW_REQUIRED
    assert next_machine.current_state is SafetyState.BUY_STOP


def test_emergency_stop_cannot_go_directly_to_normal():
    machine = SafetyStateMachine(SafetyState.EMERGENCY_STOP)
    next_machine, result = machine.transition_to(SafetyState.NORMAL)
    assert result.allowed is False
    assert result.decision is SafetyDecision.REVIEW_REQUIRED
    assert next_machine.current_state is SafetyState.EMERGENCY_STOP


def test_any_state_can_go_to_emergency_stop():
    for state in SafetyState:
        machine = SafetyStateMachine(state)
        next_machine, result = machine.transition_to(SafetyState.EMERGENCY_STOP)
        assert result.allowed is True
        assert result.decision is SafetyDecision.EMERGENCY_STOP
        assert next_machine.current_state is SafetyState.EMERGENCY_STOP


def test_unknown_state_becomes_emergency_stop():
    machine = SafetyStateMachine(SafetyState.NORMAL)
    next_machine, result = machine.transition_to("NOT_A_STATE")
    assert result.allowed is True
    assert result.decision is SafetyDecision.EMERGENCY_STOP
    assert next_machine.current_state is SafetyState.EMERGENCY_STOP


def test_recovery_requires_manual_approved_before_normal():
    machine = SafetyStateMachine(SafetyState.RECOVERY_CANDIDATE)
    machine, result = machine.transition_to(SafetyState.MANUAL_APPROVED)
    assert result.allowed is True
    assert machine.current_state is SafetyState.MANUAL_APPROVED

    machine, result = machine.transition_to(SafetyState.NORMAL)
    assert result.allowed is True
    assert machine.current_state is SafetyState.NORMAL
