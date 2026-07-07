"""Pending Order Plan lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState


@dataclass(frozen=True)
class PendingTransition:
    from_state: PendingPlanState
    to_state: PendingPlanState
    reason: str
    allowed: bool
    requires_review: bool = False


ALLOWED_PENDING_TRANSITIONS = frozenset(
    {
        (PendingPlanState.PENDING_APPROVAL, PendingPlanState.APPROVED),
        (PendingPlanState.PENDING_APPROVAL, PendingPlanState.BLOCKED),
        (PendingPlanState.PENDING_APPROVAL, PendingPlanState.REVIEW_REQUIRED),
        (PendingPlanState.APPROVED, PendingPlanState.SUBMITTING),
        (PendingPlanState.APPROVED, PendingPlanState.EXPIRED),
        (PendingPlanState.APPROVED, PendingPlanState.BLOCKED),
        (PendingPlanState.APPROVED, PendingPlanState.REVIEW_REQUIRED),
        (PendingPlanState.SUBMITTING, PendingPlanState.SUBMITTED),
        (PendingPlanState.SUBMITTING, PendingPlanState.POST_SEND_UNKNOWN),
        (PendingPlanState.SUBMITTING, PendingPlanState.REVIEW_REQUIRED),
        (PendingPlanState.SUBMITTED, PendingPlanState.CONSUMED),
        (PendingPlanState.SUBMITTED, PendingPlanState.REVIEW_REQUIRED),
        (PendingPlanState.POST_SEND_UNKNOWN, PendingPlanState.CONSUMED),
        (PendingPlanState.POST_SEND_UNKNOWN, PendingPlanState.REVIEW_REQUIRED),
        (PendingPlanState.EXPIRED, PendingPlanState.CONSUMED),
        (PendingPlanState.BLOCKED, PendingPlanState.REVIEW_REQUIRED),
    }
)


def is_pending_transition_allowed(
    from_state: PendingPlanState,
    to_state: PendingPlanState,
) -> bool:
    return (_coerce_state(from_state), _coerce_state(to_state)) in ALLOWED_PENDING_TRANSITIONS


def validate_pending_transition(
    from_state: PendingPlanState,
    to_state: PendingPlanState,
    reason: str = "",
) -> PendingTransition:
    normalized_from = _coerce_state(from_state)
    normalized_to = _coerce_state(to_state)
    return PendingTransition(
        from_state=normalized_from,
        to_state=normalized_to,
        reason=reason,
        allowed=is_pending_transition_allowed(normalized_from, normalized_to),
        requires_review=normalized_to == PendingPlanState.REVIEW_REQUIRED,
    )


def _coerce_state(state: PendingPlanState) -> PendingPlanState:
    if isinstance(state, PendingPlanState):
        return state
    return PendingPlanState(state)
