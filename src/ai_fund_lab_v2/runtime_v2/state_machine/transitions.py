"""Allowed transition table for Runtime v2."""

from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.state_machine.models import (
    RuntimeState,
    RuntimeTransition,
)

_STANDARD_TRANSITIONS = frozenset(
    {
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
        (RuntimeState.SUBMITTING, RuntimeState.POST_SEND_UNKNOWN),
        (RuntimeState.SUBMITTING, RuntimeState.REVIEW_REQUIRED),
        (RuntimeState.SUBMITTED, RuntimeState.MONITORING_FILL),
        (RuntimeState.POST_SEND_UNKNOWN, RuntimeState.REVIEW_REQUIRED),
        (RuntimeState.POST_SEND_UNKNOWN, RuntimeState.MONITORING_FILL),
        (RuntimeState.MONITORING_FILL, RuntimeState.LEDGER_UPDATED),
        (RuntimeState.LEDGER_UPDATED, RuntimeState.RECONCILED),
        (RuntimeState.RECONCILED, RuntimeState.REPORT_READY),
        (RuntimeState.REPORT_READY, RuntimeState.IDLE),
        (RuntimeState.REVIEW_REQUIRED, RuntimeState.HALT),
        (RuntimeState.BLOCKED, RuntimeState.HALT),
    }
)

_SAFE_STATES = frozenset(
    {
        RuntimeState.IDLE,
        RuntimeState.MARKET_DATA_READY,
        RuntimeState.FEATURE_READY,
        RuntimeState.CURRENT_STATE_LOADED,
        RuntimeState.AI_INFERENCE_DONE,
        RuntimeState.DAILY_PLAN_CREATED,
        RuntimeState.PENDING_PROMOTED,
        RuntimeState.APPROVAL_PENDING,
        RuntimeState.APPROVED,
        RuntimeState.MONITORING_FILL,
        RuntimeState.LEDGER_UPDATED,
        RuntimeState.RECONCILED,
        RuntimeState.REPORT_READY,
    }
)

_SAFE_FAILURE_TRANSITIONS = frozenset(
    (state, failure_state)
    for state in _SAFE_STATES
    for failure_state in (RuntimeState.BLOCKED, RuntimeState.REVIEW_REQUIRED)
)

ALLOWED_TRANSITIONS = _STANDARD_TRANSITIONS | _SAFE_FAILURE_TRANSITIONS

_SIDE_EFFECT_STATES = frozenset(
    {
        RuntimeState.SUBMITTING,
        RuntimeState.SUBMITTED,
        RuntimeState.POST_SEND_UNKNOWN,
    }
)


def is_transition_allowed(from_state: RuntimeState, to_state: RuntimeState) -> bool:
    """Return whether a Runtime v2 state transition is allowed."""

    return (_coerce_state(from_state), _coerce_state(to_state)) in ALLOWED_TRANSITIONS


def validate_transition(
    from_state: RuntimeState,
    to_state: RuntimeState,
    reason: str = "",
) -> RuntimeTransition:
    """Validate a transition and return an auditable transition model."""

    normalized_from = _coerce_state(from_state)
    normalized_to = _coerce_state(to_state)
    allowed = is_transition_allowed(normalized_from, normalized_to)
    return RuntimeTransition(
        from_state=normalized_from,
        to_state=normalized_to,
        reason=reason,
        allowed=allowed,
        requires_review=normalized_to == RuntimeState.REVIEW_REQUIRED,
        side_effect_boundary=_is_side_effect_boundary(normalized_from, normalized_to),
    )


def _coerce_state(state: RuntimeState) -> RuntimeState:
    if isinstance(state, RuntimeState):
        return state
    return RuntimeState(state)


def _is_side_effect_boundary(from_state: RuntimeState, to_state: RuntimeState) -> bool:
    return from_state in _SIDE_EFFECT_STATES or to_state in _SIDE_EFFECT_STATES
