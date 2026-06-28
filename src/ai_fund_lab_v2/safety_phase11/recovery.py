from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ai_fund_lab_v2.safety_phase11.models import SafetyState, decimal_or_none
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine, coerce_state


REQUIRED_RECOVERY_EVIDENCE = (
    "manual_emergency_flag_inactive",
    "severe_market_crash_cleared",
    "market_stable_days_satisfied",
    "candidate_universe_drawdown_improved",
    "crash_issue_ratio_declined",
    "extreme_down_ratio_declined",
    "quotes_fresh",
    "broker_snapshot_fresh",
    "broker_divergence_absent",
    "duplicate_active_order_absent",
    "daily_loss_within_limit",
    "runtime_state_valid",
    "no_secret_or_raw_persistence_violation",
    "latest_safety_report_exists",
)


@dataclass(frozen=True)
class RecoveryCheckInput:
    current_state: SafetyState | str
    manual_emergency_flag_active: bool = False
    market_summary: dict[str, Any] | None = None
    quote_freshness: str = "fresh"
    broker_snapshot_freshness: str = "fresh"
    broker_divergence: str = "none"
    duplicate_active_order_risk: bool = False
    daily_loss_pct: Decimal | str | None = None
    runtime_state_valid: bool = True
    persistence_violation_suspected: bool = False
    latest_safety_report_path: str | None = None


@dataclass(frozen=True)
class RecoveryDecision:
    recovery_candidate: bool
    required_evidence: tuple[str, ...]
    satisfied_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    next_recommended_state: SafetyState
    requires_human_review: bool = True
    auto_recovery_executed: bool = False


@dataclass(frozen=True)
class RecoveryEvaluator:
    required_stable_days: int = 3
    max_daily_loss_pct: Decimal = Decimal("-0.02")

    def evaluate(self, check_input: RecoveryCheckInput) -> RecoveryDecision:
        current_state = coerce_state(check_input.current_state)
        satisfied: list[str] = []
        missing: list[str] = []
        blocking: list[str] = []

        if current_state not in {SafetyState.BUY_STOP, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
            blocking.append("source_state_not_buy_stop_or_emergency_stop")

        _record(not check_input.manual_emergency_flag_active, "manual_emergency_flag_inactive", satisfied, missing)
        market = dict(check_input.market_summary or {})
        _record(not bool(market.get("severe_crash") or market.get("emergency_crash")), "severe_market_crash_cleared", satisfied, missing)
        _record(int(market.get("stable_days") or 0) >= self.required_stable_days, "market_stable_days_satisfied", satisfied, missing)
        _record(bool(market.get("candidate_universe_drawdown_improved")), "candidate_universe_drawdown_improved", satisfied, missing)
        _record(bool(market.get("crash_issue_ratio_declined")), "crash_issue_ratio_declined", satisfied, missing)
        _record(bool(market.get("extreme_down_ratio_declined")), "extreme_down_ratio_declined", satisfied, missing)
        _record(check_input.quote_freshness == "fresh", "quotes_fresh", satisfied, missing)
        _record(check_input.broker_snapshot_freshness == "fresh", "broker_snapshot_fresh", satisfied, missing)
        _record(check_input.broker_divergence in {"", "none", "NONE", "OK", "MATCHED"}, "broker_divergence_absent", satisfied, missing)
        _record(not check_input.duplicate_active_order_risk, "duplicate_active_order_absent", satisfied, missing)

        daily_loss = decimal_or_none(check_input.daily_loss_pct)
        _record(daily_loss is None or daily_loss >= self.max_daily_loss_pct, "daily_loss_within_limit", satisfied, missing)
        _record(check_input.runtime_state_valid, "runtime_state_valid", satisfied, missing)
        _record(not check_input.persistence_violation_suspected, "no_secret_or_raw_persistence_violation", satisfied, missing)
        _record(bool(check_input.latest_safety_report_path), "latest_safety_report_exists", satisfied, missing)

        if missing:
            blocking.append("recovery_evidence_missing")

        candidate = not blocking and set(REQUIRED_RECOVERY_EVIDENCE).issubset(set(satisfied))
        if candidate:
            transition = SafetyStateMachine(current_state=current_state).validate_transition(current_state, SafetyState.RECOVERY_CANDIDATE)
            next_state = transition.to_state if transition.allowed else current_state
        else:
            next_state = current_state
        return RecoveryDecision(
            recovery_candidate=candidate,
            required_evidence=REQUIRED_RECOVERY_EVIDENCE,
            satisfied_evidence=tuple(satisfied),
            missing_evidence=tuple(missing),
            blocking_reasons=tuple(blocking),
            next_recommended_state=next_state,
            requires_human_review=True,
            auto_recovery_executed=False,
        )


def _record(condition: bool, evidence: str, satisfied: list[str], missing: list[str]) -> None:
    if condition:
        satisfied.append(evidence)
    else:
        missing.append(evidence)
