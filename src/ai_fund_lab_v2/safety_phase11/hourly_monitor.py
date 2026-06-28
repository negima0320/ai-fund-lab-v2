from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json, write_safety_events
from ai_fund_lab_v2.safety_phase11.guards import (
    BrokerDivergenceGuard,
    DailyLossGuard,
    DuplicateOrderGuard,
    EmergencyStopGuard,
    IndividualCrashGuard,
    MarketCrashGuard,
    MarketRecoveryGuard,
)
from ai_fund_lab_v2.safety_phase11.models import (
    HumanReviewItem,
    SafetyCheckInput,
    SafetyCheckResult,
    SafetyDecision,
    SafetyEvent,
    SafetyGuardName,
    SafetySeverity,
    SafetyState,
    decimal_or_none,
    safety_id,
    utc_now_iso,
)
from ai_fund_lab_v2.safety_phase11.safety_manager import SafetyManagerResult
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine, coerce_state


MONITOR_GUARDS = (
    EmergencyStopGuard(),
    BrokerDivergenceGuard(),
    DuplicateOrderGuard(),
    MarketCrashGuard(),
    DailyLossGuard(),
    IndividualCrashGuard(),
    MarketRecoveryGuard(),
)


@dataclass(frozen=True)
class HourlyMonitorInput:
    business_date: str
    environment: str
    runtime_id: str
    current_safety_state: SafetyState | str = SafetyState.NORMAL
    broker_snapshot: dict[str, Any] = field(default_factory=dict)
    positions: tuple[dict[str, Any], ...] = ()
    quotes: dict[str, dict[str, Any]] = field(default_factory=dict)
    orders: tuple[dict[str, Any], ...] = ()
    executions: tuple[dict[str, Any], ...] = ()
    candidate_universe_market_summary: dict[str, Any] = field(default_factory=dict)
    previous_portfolio_value: Decimal | str | None = None
    current_portfolio_value: Decimal | str | None = None
    manual_emergency_stop: bool = False
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HourlyMonitorResult:
    business_date: str
    environment: str
    runtime_id: str
    current_state: SafetyState
    overall_decision: SafetyDecision
    next_recommended_state: SafetyState
    transition_allowed: bool
    transition_reason: str
    check_results: tuple[SafetyCheckResult, ...]
    events: tuple[SafetyEvent, ...]
    review_items: tuple[HumanReviewItem, ...]
    monitor_summary: dict[str, Any]

    @property
    def triggered_guards(self) -> tuple[str, ...]:
        return tuple(result.guard_name.value for result in self.check_results if result.decision is not SafetyDecision.ALLOW)


@dataclass(frozen=True)
class HourlyPositionMonitor:
    guards: tuple[Any, ...] = MONITOR_GUARDS

    def evaluate(self, monitor_input: HourlyMonitorInput) -> HourlyMonitorResult:
        current_state = coerce_state(monitor_input.current_safety_state)
        check_input = _to_safety_check_input(monitor_input)
        results = [
            _broker_snapshot_freshness_result(monitor_input, current_state),
            _quote_freshness_result(monitor_input, current_state),
            _order_execution_consistency_result(monitor_input, current_state),
        ]
        results.extend(guard.evaluate(check_input) for guard in self.guards)
        check_results = tuple(results)
        overall = _overall_decision(check_results)
        candidate = _state_candidate(current_state, overall, check_results)
        transition = SafetyStateMachine(current_state=current_state).validate_transition(current_state, candidate)
        if not transition.allowed and overall is SafetyDecision.ALLOW:
            overall = SafetyDecision.REVIEW_REQUIRED
        events = tuple(event for result in check_results for event in result.events)
        review_items = tuple(item for result in check_results for item in result.review_items)
        return HourlyMonitorResult(
            business_date=monitor_input.business_date,
            environment=monitor_input.environment,
            runtime_id=monitor_input.runtime_id,
            current_state=current_state,
            overall_decision=overall,
            next_recommended_state=transition.to_state if transition.allowed else current_state,
            transition_allowed=transition.allowed,
            transition_reason=transition.reason,
            check_results=check_results,
            events=events,
            review_items=review_items,
            monitor_summary=_monitor_summary(monitor_input, check_results, overall),
        )

    def write_outputs(
        self,
        result: HourlyMonitorResult,
        *,
        runtime_dir: Path | str = ".runtime",
        reports_dir: Path | str = "reports",
    ) -> tuple[list[Path], Path]:
        event_paths = write_safety_events(result.events, runtime_dir=runtime_dir)
        report_path = write_hourly_monitor_report(result, reports_dir=reports_dir)
        return event_paths, report_path


def build_hourly_monitor_report_payload(result: HourlyMonitorResult) -> dict[str, Any]:
    payload = {
        "schema_version": "phase11_hourly_monitor_report_v1",
        "created_at": utc_now_iso(),
        "business_date": result.business_date,
        "environment": result.environment,
        "runtime_id": result.runtime_id,
        "current_safety_state": result.current_state.value,
        "overall_decision": result.overall_decision.value,
        "next_recommended_state": result.next_recommended_state.value,
        "transition_allowed": result.transition_allowed,
        "transition_reason": result.transition_reason,
        "triggered_guards": list(result.triggered_guards),
        "monitor_summary": result.monitor_summary,
        "review_required_items": [_review_item_payload(item) for item in result.review_items],
        "events": [_event_summary(event) for event in result.events],
        "no_live_order_confirmation": {
            "broker_api_connected": False,
            "websocket_connected": False,
            "demo_order_submitted": False,
            "production_order_submitted": False,
            "clm_kabu_new_order_executed": False,
        },
        "ai_learning_use": {
            "hourly_monitor_creates_ai_training_data": False,
            "forbidden_inputs_remain_forbidden": [
                "Backtest outcome",
                "Paper Ledger",
                "Broker Snapshot",
                "PnL",
                "Portfolio state",
                "Cash",
                "selected / bought / affordable data",
                "Order result",
                "Execution result",
                "Safety result",
                "Audit result",
                "PM multiplier imitation",
            ],
        },
    }
    return _phase11_sanitize(payload)


def write_hourly_monitor_report(result: HourlyMonitorResult, reports_dir: Path | str = "reports") -> Path:
    directory = Path(reports_dir) / "safety" / "phase11" / "hourly_monitor"
    path = directory / f"hourly_monitor_{result.business_date}_{utc_now_iso().replace(':', '').replace('-', '').replace('.', '_')}.json"
    _write_json(path, build_hourly_monitor_report_payload(result))
    return path


def to_safety_manager_result(result: HourlyMonitorResult) -> SafetyManagerResult:
    return SafetyManagerResult(
        current_state=result.current_state,
        overall_decision=result.overall_decision,
        state_candidate=result.next_recommended_state,
        transition_allowed=result.transition_allowed,
        transition_reason=result.transition_reason,
        guard_results=result.check_results,
        events=result.events,
        review_items=result.review_items,
    )


def _to_safety_check_input(monitor_input: HourlyMonitorInput) -> SafetyCheckInput:
    market = dict(monitor_input.candidate_universe_market_summary)
    previous_value = decimal_or_none(monitor_input.previous_portfolio_value)
    current_value = decimal_or_none(monitor_input.current_portfolio_value)
    if previous_value is not None and previous_value > 0 and current_value is not None:
        market.setdefault("daily_loss_pct", str((current_value - previous_value) / previous_value))
    return SafetyCheckInput(
        current_state=monitor_input.current_safety_state,
        runtime_id=monitor_input.runtime_id,
        business_date=monitor_input.business_date,
        environment=monitor_input.environment,
        open_orders=monitor_input.orders,
        positions=monitor_input.positions,
        quotes=monitor_input.quotes,
        market=market,
        broker_snapshot=monitor_input.broker_snapshot,
        config=monitor_input.config,
        manual_emergency_stop=monitor_input.manual_emergency_stop,
    )


def _broker_snapshot_freshness_result(monitor_input: HourlyMonitorInput, state: SafetyState) -> SafetyCheckResult:
    snapshot = monitor_input.broker_snapshot
    if not snapshot:
        return _result(
            monitor_input,
            SafetyGuardName.BROKER_SNAPSHOT_FRESHNESS,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "BROKER_SNAPSHOT_MISSING",
            "Broker snapshot is missing. Broker is source of truth.",
            state,
            recommended_action="Refresh broker snapshot before allowing trading decisions.",
            details={"broker_snapshot_freshness": "missing"},
        )
    if bool(snapshot.get("unavailable")):
        return _result(
            monitor_input,
            SafetyGuardName.BROKER_SNAPSHOT_FRESHNESS,
            SafetyDecision.EMERGENCY_STOP,
            SafetySeverity.EMERGENCY,
            "BROKER_SNAPSHOT_UNAVAILABLE",
            "Broker snapshot is unavailable.",
            state,
            state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
            recommended_action="Fail closed and review broker connectivity before continuing.",
            details={"broker_snapshot_freshness": "unavailable"},
        )
    max_age = decimal_or_none(monitor_input.config.get("max_broker_snapshot_age_seconds")) or Decimal("900")
    age = decimal_or_none(snapshot.get("age_seconds"))
    if bool(snapshot.get("stale")) or (age is not None and age > max_age):
        return _result(
            monitor_input,
            SafetyGuardName.BROKER_SNAPSHOT_FRESHNESS,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "BROKER_SNAPSHOT_STALE",
            "Broker snapshot is stale.",
            state,
            recommended_action="Refresh broker snapshot before continuing.",
            details={"broker_snapshot_freshness": "stale"},
        )
    return SafetyCheckResult.allow(
        SafetyGuardName.BROKER_SNAPSHOT_FRESHNESS,
        state,
        reason_code="BROKER_SNAPSHOT_FRESH",
        message="Broker snapshot freshness passed.",
        details={"broker_snapshot_freshness": "fresh"},
    )


def _quote_freshness_result(monitor_input: HourlyMonitorInput, state: SafetyState) -> SafetyCheckResult:
    max_age = decimal_or_none(monitor_input.config.get("max_quote_age_seconds")) or Decimal("300")
    target_codes = {str(position.get("issue_code") or position.get("symbol") or "") for position in monitor_input.positions}
    target_codes.update(str(order.get("issue_code") or order.get("symbol") or "") for order in monitor_input.orders)
    target_codes = {code for code in target_codes if code}
    missing = sorted(code for code in target_codes if code not in monitor_input.quotes)
    if missing:
        return _result(
            monitor_input,
            SafetyGuardName.QUOTE_STALE,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "QUOTE_MISSING_FOR_MONITOR",
            "Quote is missing for monitored issue codes.",
            state,
            state_after=SafetyState.BUY_REVIEW_REQUIRED,
            recommended_action="Do not infer prices. Refresh quotes before monitoring or trading.",
            details={"quote_freshness": "missing", "missing_issue_codes": missing, "refined_classification": "BUY_REVIEW_REQUIRED"},
        )
    stale_codes: list[str] = []
    for code in sorted(target_codes):
        quote = monitor_input.quotes.get(code, {})
        age = decimal_or_none(quote.get("age_seconds"))
        if bool(quote.get("stale")) or age is None or age > max_age:
            stale_codes.append(code)
    if stale_codes:
        return _result(
            monitor_input,
            SafetyGuardName.QUOTE_STALE,
            SafetyDecision.BLOCK,
            SafetySeverity.BLOCK,
            "QUOTE_STALE_FOR_MONITOR",
            "One or more monitored quotes are stale.",
            state,
            state_after=SafetyState.BUY_REVIEW_REQUIRED,
            recommended_action="Block new buys and refresh realtime quotes.",
            details={"quote_freshness": "stale", "stale_issue_codes": stale_codes, "refined_classification": "BUY_REVIEW_REQUIRED", "critical_stale": False},
        )
    return SafetyCheckResult.allow(
        SafetyGuardName.QUOTE_STALE,
        state,
        reason_code="QUOTES_FRESH",
        message="Quote freshness passed for monitored issues.",
        details={"quote_freshness": "fresh"},
    )


def _order_execution_consistency_result(monitor_input: HourlyMonitorInput, state: SafetyState) -> SafetyCheckResult:
    active_buys = [
        order
        for order in monitor_input.orders
        if str(order.get("side") or "").upper() == "BUY"
        and str(order.get("status") or "OPEN").upper() in {"OPEN", "PENDING", "ACCEPTED", "WAITING_FILL", "PARTIAL", "PARTIALLY_FILLED"}
    ]
    duplicate_keys = _duplicate_keys(active_buys)
    if duplicate_keys:
        return _result(
            monitor_input,
            SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
            SafetyDecision.EMERGENCY_STOP,
            SafetySeverity.EMERGENCY,
            "DUPLICATE_ACTIVE_BUY_ORDER",
            "Duplicate active buy orders were found during hourly monitoring.",
            state,
            state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
            recommended_action="Stop order flow and reconcile broker active orders.",
            details={"duplicate_active_buy_orders": duplicate_keys},
        )
    position_codes = {str(position.get("issue_code") or position.get("symbol") or "") for position in monitor_input.positions}
    position_codes = {code for code in position_codes if code}
    filled_buys = [
        item
        for item in list(monitor_input.orders) + list(monitor_input.executions)
        if str(item.get("side") or "").upper() == "BUY" and str(item.get("status") or item.get("execution_status") or "").upper() in {"FILLED", "EXECUTED"}
    ]
    missing_positions = sorted(
        {
            str(item.get("issue_code") or item.get("symbol") or "")
            for item in filled_buys
            if str(item.get("issue_code") or item.get("symbol") or "") and str(item.get("issue_code") or item.get("symbol") or "") not in position_codes
        }
    )
    if missing_positions:
        return _result(
            monitor_input,
            SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "EXECUTION_POSITION_MISMATCH",
            "Filled buy execution exists but matching broker position is missing.",
            state,
            recommended_action="Review executions and broker positions before continuing.",
            details={"missing_position_issue_codes": missing_positions},
        )
    if monitor_input.positions and not monitor_input.broker_snapshot:
        return _result(
            monitor_input,
            SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "POSITION_WITHOUT_BROKER_SNAPSHOT",
            "Positions exist but broker snapshot is missing.",
            state,
            recommended_action="Broker is source of truth. Refresh broker snapshot.",
        )
    unknown_orders = [
        str(order.get("issue_code") or order.get("symbol") or "")
        for order in monitor_input.orders
        if str(order.get("status") or "").upper() in {"", "UNKNOWN", "UNKNOWN_STATUS"}
    ]
    if unknown_orders:
        return _result(
            monitor_input,
            SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "UNKNOWN_ORDER_STATE",
            "One or more orders have unknown state.",
            state,
            recommended_action="Review order status before continuing.",
            details={"unknown_order_issue_codes": sorted(set(unknown_orders))},
        )
    unclear_terminal = [
        str(order.get("issue_code") or order.get("symbol") or "")
        for order in monitor_input.orders
        if str(order.get("status") or "").upper() in {"CANCELED_UNKNOWN", "REJECTED_UNKNOWN", "EXPIRED_UNKNOWN"}
    ]
    if unclear_terminal:
        return _result(
            monitor_input,
            SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
            SafetyDecision.REVIEW_REQUIRED,
            SafetySeverity.REVIEW,
            "UNCLEAR_TERMINAL_ORDER_STATE",
            "Canceled, rejected, or expired order handling is unclear.",
            state,
            recommended_action="Review terminal order state before continuing.",
            details={"unclear_terminal_issue_codes": sorted(set(unclear_terminal))},
        )
    return SafetyCheckResult.allow(
        SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
        state,
        reason_code="ORDER_EXECUTION_CONSISTENT",
        message="Order and execution consistency checks passed.",
        details={"order_execution_consistency": "consistent"},
    )


def _duplicate_keys(orders: list[dict[str, Any]]) -> list[str]:
    counts: dict[tuple[str, str], int] = {}
    for order in orders:
        key = (str(order.get("issue_code") or order.get("symbol") or ""), str(order.get("side") or "").upper())
        if key[0] and key[1]:
            counts[key] = counts.get(key, 0) + 1
    return sorted(f"{symbol}:{side}" for (symbol, side), count in counts.items() if count > 1)


def _overall_decision(results: tuple[SafetyCheckResult, ...]) -> SafetyDecision:
    decisions = [result.decision for result in results]
    if SafetyDecision.EMERGENCY_STOP in decisions:
        return SafetyDecision.EMERGENCY_STOP
    if SafetyDecision.BLOCK in decisions:
        return SafetyDecision.BLOCK
    if SafetyDecision.REVIEW_REQUIRED in decisions:
        return SafetyDecision.REVIEW_REQUIRED
    return SafetyDecision.ALLOW


def _state_candidate(current_state: SafetyState, overall: SafetyDecision, results: tuple[SafetyCheckResult, ...]) -> SafetyState:
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


def _monitor_summary(
    monitor_input: HourlyMonitorInput,
    check_results: tuple[SafetyCheckResult, ...],
    overall: SafetyDecision,
) -> dict[str, Any]:
    return {
        "positions_count": len(monitor_input.positions),
        "quotes_count": len(monitor_input.quotes),
        "orders_count": len(monitor_input.orders),
        "executions_count": len(monitor_input.executions),
        "overall_decision": overall.value,
        "triggered_reason_codes": [result.reason_code for result in check_results if result.decision is not SafetyDecision.ALLOW],
        "broker_snapshot_freshness": _detail_value(check_results, "broker_snapshot_freshness", "unknown"),
        "quote_freshness": _detail_value(check_results, "quote_freshness", "unknown"),
        "market_crash_status": _detail_value(check_results, "market_crash_status", "unknown"),
        "market_stress_summary": _market_stress_summary(check_results),
        "buy_opportunity_review": _has_reason(check_results, {"BUY_OPPORTUNITY_REVIEW"}),
        "sell_review_required": _has_reason(check_results, {"SELL_REVIEW_REQUIRED"}),
        "high_risk_review": _has_reason(check_results, {"HIGH_RISK_REVIEW"}),
        "recovery_candidate_status": _detail_value(check_results, "recovery_candidate_status", "unknown"),
        "divergence_summary": _detail_value(check_results, "divergence_summary", "none"),
    }


def _detail_value(check_results: tuple[SafetyCheckResult, ...], key: str, default: Any) -> Any:
    for result in check_results:
        if key in result.details:
            return result.details[key]
    return default


def _has_reason(check_results: tuple[SafetyCheckResult, ...], reason_codes: set[str]) -> bool:
    return any(result.reason_code in reason_codes for result in check_results)


def _market_stress_summary(check_results: tuple[SafetyCheckResult, ...]) -> dict[str, Any]:
    reasons = [result.reason_code for result in check_results if result.reason_code in {"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "DAILY_LOSS_REVIEW_REQUIRED", "MARKET_STRESS_DAILY_LOSS"}]
    return {
        "market_stress_detected": bool(reasons),
        "reason_codes": reasons,
        "emergency_stop": False,
        "auto_sell_executed": False,
        "auto_buy_stop": False,
    }


def _result(
    monitor_input: HourlyMonitorInput,
    guard_name: SafetyGuardName,
    decision: SafetyDecision,
    severity: SafetySeverity,
    reason_code: str,
    message: str,
    state_before: SafetyState,
    *,
    state_after: SafetyState | None = None,
    issue_code: str | None = None,
    recommended_action: str,
    details: dict[str, Any] | None = None,
) -> SafetyCheckResult:
    requires_review = decision in {SafetyDecision.REVIEW_REQUIRED, SafetyDecision.BLOCK, SafetyDecision.EMERGENCY_STOP}
    event = SafetyEvent(
        guard_name=guard_name,
        decision=decision,
        severity=severity,
        reason_code=reason_code,
        message=message,
        state_before=state_before,
        state_after=state_after,
        runtime_id=monitor_input.runtime_id,
        business_date=monitor_input.business_date,
        environment=monitor_input.environment,
        issue_code=issue_code,
        requires_human_review=requires_review,
        details=details or {},
    )
    review_items: tuple[HumanReviewItem, ...] = ()
    if requires_review:
        review_items = (
            HumanReviewItem(
                guard_name=guard_name,
                reason_code=reason_code,
                message=message,
                severity=severity,
                recommended_action=recommended_action,
                issue_code=issue_code,
                event_id=event.event_id,
            ),
        )
    return SafetyCheckResult(
        guard_name=guard_name,
        decision=decision,
        severity=severity,
        reason_code=reason_code,
        message=message,
        state_before=state_before,
        state_after=state_after,
        events=(event,),
        review_items=review_items,
        details=details or {},
    )


def _review_item_payload(item: HumanReviewItem) -> dict[str, Any]:
    return {
        "review_id": item.review_id,
        "event_id": item.event_id,
        "guard_name": item.guard_name.value,
        "reason_code": item.reason_code,
        "message": item.message,
        "severity": item.severity.value,
        "issue_code": item.issue_code,
        "recommended_action": item.recommended_action,
    }


def _event_summary(event: SafetyEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "guard_name": event.guard_name.value,
        "decision": event.decision.value,
        "severity": event.severity.value,
        "reason_code": event.reason_code,
        "issue_code": event.issue_code,
        "requires_human_review": event.requires_human_review,
        "auto_trade_executed": event.auto_trade_executed,
        "raw_response_saved": event.raw_response_saved,
    }
