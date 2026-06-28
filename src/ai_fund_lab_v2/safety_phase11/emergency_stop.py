from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetySeverity, SafetyState
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine


EMERGENCY_REASON_CODES = {
    "MANUAL_EMERGENCY_STOP",
    "BROKER_SNAPSHOT_UNAVAILABLE",
    "BROKER_DUPLICATE_ORDER_RISK",
    "DUPLICATE_ORDER_SYSTEM_EMERGENCY",
    "DUPLICATE_ACTIVE_BUY_ORDER",
    "RUNTIME_STATE_INCONSISTENT",
    "BROKER_DIVERGENCE_DETECTED",
    "MAX_EXPOSURE_SEVERE_VIOLATION",
    "CASH_EXPOSURE_SEVERE_VIOLATION",
    "ORDER_EXECUTION_SEVERE_DIVERGENCE",
    "POSITION_QUANTITY_MISMATCH",
    "UNKNOWN_BROKER_POSITION",
    "SECRET_PERSISTENCE_VIOLATION",
    "RAW_RESPONSE_PERSISTENCE_VIOLATION",
    "UNKNOWN_SEVERE_ERROR",
}

CRITICAL_STALE_REASON_CODES = {"BROKER_SNAPSHOT_MISSING", "BROKER_SNAPSHOT_STALE"}

EMERGENCY_BLOCKED_ACTIONS = (
    "new_buy",
    "new_sell_auto_execution",
    "correction",
    "cancel",
    "retry",
    "automatic_recovery",
    "normal_runtime_progression",
    "broker_order_api",
    "demo_order_submit",
    "production_order_submit",
)

EMERGENCY_ALLOWED_ACTIONS = (
    "read_only_broker_sync",
    "quote_polling",
    "report_generation",
    "audit",
    "human_review",
)


@dataclass(frozen=True)
class EmergencyStopDecision:
    emergency_required: bool
    reason_codes: tuple[str, ...]
    triggered_guards: tuple[str, ...]
    affected_issue_codes: tuple[str, ...]
    recommended_human_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    next_state: SafetyState


@dataclass(frozen=True)
class EmergencyStopEvaluator:
    critical_broker_snapshot_stale: bool = True

    def evaluate(
        self,
        result: Any,
        *,
        manual_flag_active: bool = False,
        persistence_violation_suspected: bool = False,
        unknown_severe_error: bool = False,
    ) -> EmergencyStopDecision:
        reason_codes: list[str] = []
        guards: list[str] = []
        issue_codes: list[str] = []
        actions: list[str] = []

        if manual_flag_active:
            reason_codes.append("MANUAL_EMERGENCY_STOP")
            guards.append("EMERGENCY_STOP")
            actions.append("Keep all order flow stopped until manual review clears the flag.")
        if persistence_violation_suspected:
            reason_codes.append("SECRET_PERSISTENCE_VIOLATION")
            guards.append("EMERGENCY_STOP")
            actions.append("Audit persisted artifacts for secret or raw response leakage.")
        if unknown_severe_error:
            reason_codes.append("UNKNOWN_SEVERE_ERROR")
            guards.append("EMERGENCY_STOP")
            actions.append("Fail closed and investigate the unknown severe error.")

        for check in tuple(getattr(result, "check_results", getattr(result, "guard_results", ()))):
            if _is_emergency_check(check, self.critical_broker_snapshot_stale):
                reason_codes.append(check.reason_code)
                guards.append(check.guard_name.value)
                for event in check.events:
                    if event.issue_code:
                        issue_codes.append(event.issue_code)
                for item in check.review_items:
                    if item.issue_code:
                        issue_codes.append(item.issue_code)
                    actions.append(item.recommended_action)

        if getattr(result, "overall_decision", None) is SafetyDecision.EMERGENCY_STOP:
            reason_codes.append("OVERALL_EMERGENCY_STOP")

        unique_reasons = _unique(reason_codes)
        emergency_required = bool(unique_reasons)
        if emergency_required:
            current_state = getattr(result, "current_state", SafetyState.NORMAL)
            transition = SafetyStateMachine(current_state=current_state).validate_transition(current_state, SafetyState.SYSTEM_EMERGENCY_STOP)
            next_state = transition.to_state
        else:
            next_state = getattr(result, "next_recommended_state", getattr(result, "state_candidate", SafetyState.NORMAL))
        return EmergencyStopDecision(
            emergency_required=emergency_required,
            reason_codes=tuple(unique_reasons),
            triggered_guards=tuple(_unique(guards)),
            affected_issue_codes=tuple(_unique(issue_codes)),
            recommended_human_actions=tuple(_unique(actions)),
            blocked_actions=EMERGENCY_BLOCKED_ACTIONS if emergency_required else (),
            allowed_actions=EMERGENCY_ALLOWED_ACTIONS if emergency_required else (),
            next_state=next_state,
        )


def _is_emergency_check(check: Any, critical_stale: bool) -> bool:
    if check.decision is SafetyDecision.EMERGENCY_STOP:
        return True
    if check.severity is SafetySeverity.EMERGENCY:
        return True
    if check.reason_code in EMERGENCY_REASON_CODES:
        return True
    if critical_stale and check.reason_code in CRITICAL_STALE_REASON_CODES:
        return True
    if str(check.details.get("divergence_severity", "")).upper() in {"HALT", "EMERGENCY", "SEVERE"}:
        return True
    return False


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
