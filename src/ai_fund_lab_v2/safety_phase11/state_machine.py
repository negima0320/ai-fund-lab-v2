from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState


ALLOWED_TRANSITIONS: dict[SafetyState, frozenset[SafetyState]] = {
    SafetyState.NORMAL: frozenset({
        SafetyState.WARNING,
        SafetyState.MARKET_STRESS,
        SafetyState.BUY_REVIEW_REQUIRED,
        SafetyState.BUY_OPPORTUNITY_REVIEW,
        SafetyState.BUY_STOP,
        SafetyState.SYSTEM_EMERGENCY_STOP,
        SafetyState.EMERGENCY_STOP,
    }),
    SafetyState.WARNING: frozenset({
        SafetyState.NORMAL,
        SafetyState.MARKET_STRESS,
        SafetyState.BUY_REVIEW_REQUIRED,
        SafetyState.BUY_OPPORTUNITY_REVIEW,
        SafetyState.BUY_STOP,
        SafetyState.SYSTEM_EMERGENCY_STOP,
        SafetyState.EMERGENCY_STOP,
    }),
    SafetyState.MARKET_STRESS: frozenset({
        SafetyState.NORMAL,
        SafetyState.WARNING,
        SafetyState.BUY_REVIEW_REQUIRED,
        SafetyState.BUY_OPPORTUNITY_REVIEW,
        SafetyState.SYSTEM_EMERGENCY_STOP,
        SafetyState.EMERGENCY_STOP,
    }),
    SafetyState.BUY_REVIEW_REQUIRED: frozenset({
        SafetyState.NORMAL,
        SafetyState.WARNING,
        SafetyState.MARKET_STRESS,
        SafetyState.BUY_OPPORTUNITY_REVIEW,
        SafetyState.SYSTEM_EMERGENCY_STOP,
        SafetyState.EMERGENCY_STOP,
    }),
    SafetyState.BUY_OPPORTUNITY_REVIEW: frozenset({
        SafetyState.NORMAL,
        SafetyState.WARNING,
        SafetyState.MARKET_STRESS,
        SafetyState.BUY_REVIEW_REQUIRED,
        SafetyState.SYSTEM_EMERGENCY_STOP,
        SafetyState.EMERGENCY_STOP,
    }),
    SafetyState.BUY_STOP: frozenset({SafetyState.RECOVERY_CANDIDATE, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}),
    SafetyState.SYSTEM_EMERGENCY_STOP: frozenset({SafetyState.RECOVERY_CANDIDATE}),
    SafetyState.EMERGENCY_STOP: frozenset({SafetyState.RECOVERY_CANDIDATE}),
    SafetyState.RECOVERY_CANDIDATE: frozenset({SafetyState.MANUAL_APPROVED, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}),
    SafetyState.MANUAL_APPROVED: frozenset({
        SafetyState.NORMAL,
        SafetyState.WARNING,
        SafetyState.MARKET_STRESS,
        SafetyState.BUY_REVIEW_REQUIRED,
        SafetyState.BUY_OPPORTUNITY_REVIEW,
        SafetyState.BUY_STOP,
        SafetyState.SYSTEM_EMERGENCY_STOP,
        SafetyState.EMERGENCY_STOP,
    }),
}


@dataclass(frozen=True)
class SafetyTransitionResult:
    from_state: SafetyState
    to_state: SafetyState
    allowed: bool
    decision: SafetyDecision
    reason: str


@dataclass(frozen=True)
class SafetyStateMachine:
    current_state: SafetyState = SafetyState.NORMAL

    def transition_to(self, target: SafetyState | str) -> tuple["SafetyStateMachine", SafetyTransitionResult]:
        result = self.validate_transition(self.current_state, target)
        next_state = result.to_state if result.allowed else self.current_state
        if result.reason == "unknown_state":
            next_state = SafetyState.EMERGENCY_STOP
        return SafetyStateMachine(current_state=next_state), result

    def validate_transition(self, current: SafetyState | str, target: SafetyState | str) -> SafetyTransitionResult:
        current_state = _parse_state(current)
        target_state = _parse_state(target)
        if current_state is None or target_state is None:
            return SafetyTransitionResult(
                from_state=current_state or SafetyState.EMERGENCY_STOP,
                to_state=SafetyState.EMERGENCY_STOP,
                allowed=True,
                decision=SafetyDecision.EMERGENCY_STOP,
                reason="unknown_state",
            )
        if target_state in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
            return SafetyTransitionResult(
                from_state=current_state,
                to_state=target_state,
                allowed=True,
                decision=SafetyDecision.EMERGENCY_STOP,
                reason="system_emergency_stop_allowed_from_any_state",
            )
        if target_state is current_state:
            return SafetyTransitionResult(
                from_state=current_state,
                to_state=target_state,
                allowed=True,
                decision=SafetyDecision.ALLOW,
                reason="same_state",
            )
        if target_state in ALLOWED_TRANSITIONS[current_state]:
            return SafetyTransitionResult(
                from_state=current_state,
                to_state=target_state,
                allowed=True,
                decision=SafetyDecision.ALLOW,
                reason="valid_transition",
            )
        return SafetyTransitionResult(
            from_state=current_state,
            to_state=target_state,
            allowed=False,
            decision=SafetyDecision.REVIEW_REQUIRED,
            reason="invalid_transition_requires_review",
        )


def coerce_state(value: SafetyState | str) -> SafetyState:
    parsed = _parse_state(value)
    return parsed or SafetyState.EMERGENCY_STOP


def _parse_state(value: SafetyState | str) -> SafetyState | None:
    if isinstance(value, SafetyState):
        return value
    try:
        return SafetyState(str(value))
    except ValueError:
        return None
