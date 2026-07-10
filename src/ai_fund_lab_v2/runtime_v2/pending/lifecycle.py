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
        (PendingPlanState.CREATED, PendingPlanState.PENDING_REVIEW),
        (PendingPlanState.CREATED, PendingPlanState.PENDING_APPROVAL),
        (PendingPlanState.PENDING_REVIEW, PendingPlanState.PENDING_APPROVAL),
        (PendingPlanState.PENDING_REVIEW, PendingPlanState.REVIEW_REQUIRED),
        (PendingPlanState.APPROVED, PendingPlanState.SUBMITTING),
        (PendingPlanState.APPROVED, PendingPlanState.EXPIRED),
        (PendingPlanState.APPROVED, PendingPlanState.CANCELLED),
        (PendingPlanState.APPROVED, PendingPlanState.SUPERSEDED),
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
        (PendingPlanState.REVIEW_REQUIRED, PendingPlanState.CANCELLED),
    }
)

TERMINAL_PENDING_STATES = frozenset(
    {
        PendingPlanState.CONSUMED,
        PendingPlanState.EXPIRED,
        PendingPlanState.CANCELLED,
        PendingPlanState.REJECTED,
        PendingPlanState.SUPERSEDED,
        PendingPlanState.EMPTY,
    }
)

SUBMIT_ALLOWED_STATES = frozenset({PendingPlanState.APPROVED})


PENDING_STATE_CONTRACT = {
    "CREATED": {
        "meaning": "Pending shell created but not ready for approval.",
        "allowed_next_states": ("PENDING_REVIEW", "PENDING_APPROVAL"),
        "terminal": False,
        "submit_allowed": False,
    },
    "PENDING_REVIEW": {
        "meaning": "Pending requires Operator or policy review before approval.",
        "allowed_next_states": ("PENDING_APPROVAL", "REVIEW_REQUIRED"),
        "terminal": False,
        "submit_allowed": False,
    },
    "APPROVED": {
        "meaning": "Approval exists, but submit also requires date, freshness, policy, safety, and unknown-outcome checks.",
        "allowed_next_states": ("SUBMITTING", "EXPIRED", "CANCELLED", "SUPERSEDED", "BLOCKED", "REVIEW_REQUIRED"),
        "terminal": False,
        "submit_allowed": True,
    },
    "REJECTED": {
        "meaning": "Approval rejected this Pending.",
        "allowed_next_states": (),
        "terminal": True,
        "submit_allowed": False,
    },
    "CONSUMED": {
        "meaning": "Pending was consumed by submit/ledger evidence.",
        "allowed_next_states": (),
        "terminal": True,
        "submit_allowed": False,
    },
    "EXPIRED": {
        "meaning": "Pending expired without submit attempt evidence.",
        "allowed_next_states": (),
        "terminal": True,
        "submit_allowed": False,
    },
    "CANCELLED": {
        "meaning": "Operator cancelled Pending through regular lifecycle path.",
        "allowed_next_states": (),
        "terminal": True,
        "submit_allowed": False,
    },
    "SUPERSEDED": {
        "meaning": "Pending was superseded by a newer explicit plan.",
        "allowed_next_states": (),
        "terminal": True,
        "submit_allowed": False,
    },
    "REVIEW_REQUIRED": {
        "meaning": "Pending has unresolved evidence or possible unknown outcome.",
        "allowed_next_states": ("CANCELLED",),
        "terminal": False,
        "submit_allowed": False,
    },
    "EMPTY": {
        "meaning": "No active Pending is present in the current slot.",
        "allowed_next_states": (),
        "terminal": True,
        "submit_allowed": False,
    },
}


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
