from ai_fund_lab_v2.runtime_v2.pending.lifecycle import (
    is_pending_transition_allowed,
    validate_pending_transition,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState


def test_allowed_pending_transitions():
    assert is_pending_transition_allowed(
        PendingPlanState.APPROVED,
        PendingPlanState.SUBMITTING,
    )
    assert is_pending_transition_allowed(
        PendingPlanState.SUBMITTING,
        PendingPlanState.SUBMITTED,
    )
    assert is_pending_transition_allowed(
        PendingPlanState.SUBMITTING,
        PendingPlanState.POST_SEND_UNKNOWN,
    )
    assert is_pending_transition_allowed(
        PendingPlanState.SUBMITTED,
        PendingPlanState.CONSUMED,
    )
    assert is_pending_transition_allowed(
        PendingPlanState.POST_SEND_UNKNOWN,
        PendingPlanState.CONSUMED,
    )


def test_forbidden_pending_transitions():
    assert not is_pending_transition_allowed(
        PendingPlanState.CONSUMED,
        PendingPlanState.SUBMITTING,
    )
    assert not is_pending_transition_allowed(
        PendingPlanState.POST_SEND_UNKNOWN,
        PendingPlanState.SUBMITTING,
    )
    assert not is_pending_transition_allowed(
        PendingPlanState.REVIEW_REQUIRED,
        PendingPlanState.APPROVED,
    )


def test_validate_pending_transition_reports_invalid_transition():
    transition = validate_pending_transition(
        PendingPlanState.CONSUMED,
        PendingPlanState.SUBMITTING,
        reason="re-submit must be blocked",
    )

    assert transition.allowed is False

