from ai_fund_lab_v2.runtime_v2.state_machine.models import RuntimeState
from ai_fund_lab_v2.runtime_v2.state_machine.transitions import (
    is_transition_allowed,
    validate_transition,
)


def test_standard_transitions_are_allowed():
    standard_path = (
        (RuntimeState.IDLE, RuntimeState.MARKET_DATA_READY),
        (RuntimeState.MARKET_DATA_READY, RuntimeState.FEATURE_READY),
        (RuntimeState.FEATURE_READY, RuntimeState.CURRENT_STATE_LOADED),
        (RuntimeState.CURRENT_STATE_LOADED, RuntimeState.AI_INFERENCE_DONE),
        (RuntimeState.AI_INFERENCE_DONE, RuntimeState.DAILY_PLAN_CREATED),
        (RuntimeState.DAILY_PLAN_CREATED, RuntimeState.PENDING_PROMOTED),
        (RuntimeState.PENDING_PROMOTED, RuntimeState.APPROVAL_PENDING),
        (RuntimeState.APPROVAL_PENDING, RuntimeState.APPROVED),
        (RuntimeState.APPROVED, RuntimeState.SUBMITTING),
        (RuntimeState.SUBMITTING, RuntimeState.SUBMITTED),
        (RuntimeState.SUBMITTED, RuntimeState.MONITORING_FILL),
        (RuntimeState.MONITORING_FILL, RuntimeState.LEDGER_UPDATED),
        (RuntimeState.LEDGER_UPDATED, RuntimeState.RECONCILED),
        (RuntimeState.RECONCILED, RuntimeState.REPORT_READY),
        (RuntimeState.REPORT_READY, RuntimeState.IDLE),
    )

    for from_state, to_state in standard_path:
        assert is_transition_allowed(from_state, to_state)


def test_invalid_transition_is_detected():
    transition = validate_transition(
        RuntimeState.IDLE,
        RuntimeState.SUBMITTING,
        reason="must not skip preflight",
    )

    assert transition.allowed is False
    assert transition.side_effect_boundary is True


def test_post_send_unknown_to_submitting_is_forbidden():
    assert not is_transition_allowed(
        RuntimeState.POST_SEND_UNKNOWN,
        RuntimeState.SUBMITTING,
    )


def test_submitted_to_submitting_is_forbidden():
    assert not is_transition_allowed(RuntimeState.SUBMITTED, RuntimeState.SUBMITTING)


def test_idle_to_submitting_is_forbidden():
    assert not is_transition_allowed(RuntimeState.IDLE, RuntimeState.SUBMITTING)


def test_review_required_and_blocked_can_halt():
    assert is_transition_allowed(RuntimeState.REVIEW_REQUIRED, RuntimeState.HALT)
    assert is_transition_allowed(RuntimeState.BLOCKED, RuntimeState.HALT)


def test_consumed_is_not_a_runtime_state():
    assert "CONSUMED" not in RuntimeState.__members__

