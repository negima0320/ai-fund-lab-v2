from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.safety_phase11.guards import (
    BrokerDivergenceGuard,
    CashBufferGuard,
    DailyLossGuard,
    DuplicateOrderGuard,
    EmergencyStopGuard,
    IndividualCrashGuard,
    MarketCrashGuard,
    MarketRecoveryGuard,
    MaxExposureGuard,
    QuoteStaleGuard,
    SafetyGuard,
)
from ai_fund_lab_v2.safety_phase11.models import (
    HumanReviewItem,
    SafetyCheckInput,
    SafetyCheckResult,
    SafetyDecision,
    SafetyEvent,
    SafetySeverity,
    SafetyState,
)
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine, coerce_state


DEFAULT_GUARDS: tuple[SafetyGuard, ...] = (
    EmergencyStopGuard(),
    BrokerDivergenceGuard(),
    DuplicateOrderGuard(),
    MarketCrashGuard(),
    QuoteStaleGuard(),
    CashBufferGuard(),
    MaxExposureGuard(),
    DailyLossGuard(),
    IndividualCrashGuard(),
    MarketRecoveryGuard(),
)


@dataclass(frozen=True)
class SafetyManagerResult:
    current_state: SafetyState
    overall_decision: SafetyDecision
    state_candidate: SafetyState
    transition_allowed: bool
    transition_reason: str
    guard_results: tuple[SafetyCheckResult, ...]
    events: tuple[SafetyEvent, ...]
    review_items: tuple[HumanReviewItem, ...]

    @property
    def triggered_guards(self) -> tuple[str, ...]:
        return tuple(result.guard_name.value for result in self.guard_results if result.decision is not SafetyDecision.ALLOW)


@dataclass(frozen=True)
class SafetyManager:
    guards: tuple[SafetyGuard, ...] = DEFAULT_GUARDS

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyManagerResult:
        current_state = coerce_state(check_input.current_state)
        results = tuple(guard.evaluate(check_input) for guard in self.guards)
        overall = _overall_decision(results)
        candidate = _state_candidate(current_state, overall, results)
        transition = SafetyStateMachine(current_state=current_state).validate_transition(current_state, candidate)
        events = tuple(event for result in results for event in result.events)
        review_items = tuple(item for result in results for item in result.review_items)
        if not transition.allowed and overall is SafetyDecision.ALLOW:
            overall = SafetyDecision.REVIEW_REQUIRED
        return SafetyManagerResult(
            current_state=current_state,
            overall_decision=overall,
            state_candidate=transition.to_state if transition.allowed else current_state,
            transition_allowed=transition.allowed,
            transition_reason=transition.reason,
            guard_results=results,
            events=events,
            review_items=review_items,
        )


def _overall_decision(results: tuple[SafetyCheckResult, ...]) -> SafetyDecision:
    decisions = [result.decision for result in results]
    if SafetyDecision.EMERGENCY_STOP in decisions:
        return SafetyDecision.EMERGENCY_STOP
    if SafetyDecision.BLOCK in decisions:
        return SafetyDecision.BLOCK
    if SafetyDecision.REVIEW_REQUIRED in decisions:
        return SafetyDecision.REVIEW_REQUIRED
    return SafetyDecision.ALLOW


def _state_candidate(
    current_state: SafetyState,
    overall: SafetyDecision,
    results: tuple[SafetyCheckResult, ...],
) -> SafetyState:
    if overall is SafetyDecision.EMERGENCY_STOP:
        return SafetyState.SYSTEM_EMERGENCY_STOP
    candidates = [result.state_after for result in results if result.state_after is not None]
    if SafetyState.SYSTEM_EMERGENCY_STOP in candidates:
        return SafetyState.SYSTEM_EMERGENCY_STOP
    if SafetyState.EMERGENCY_STOP in candidates:
        return SafetyState.EMERGENCY_STOP
    if SafetyState.BUY_OPPORTUNITY_REVIEW in candidates:
        return SafetyState.BUY_OPPORTUNITY_REVIEW
    if SafetyState.BUY_REVIEW_REQUIRED in candidates:
        return SafetyState.BUY_REVIEW_REQUIRED
    if SafetyState.MARKET_STRESS in candidates:
        return SafetyState.MARKET_STRESS
    if SafetyState.BUY_STOP in candidates:
        return SafetyState.BUY_STOP
    if SafetyState.RECOVERY_CANDIDATE in candidates:
        return SafetyState.RECOVERY_CANDIDATE
    if SafetyState.MANUAL_APPROVED in candidates:
        return SafetyState.MANUAL_APPROVED
    if SafetyState.WARNING in candidates:
        return SafetyState.WARNING
    if any(result.severity is SafetySeverity.WARNING for result in results):
        return SafetyState.WARNING
    return current_state
