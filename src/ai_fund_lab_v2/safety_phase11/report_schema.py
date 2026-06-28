from __future__ import annotations

from typing import Any

from ai_fund_lab_v2.safety_phase11.models import HumanReviewItem, SafetyDecision, SafetyEvent, SafetyState, safety_id, utc_now_iso


REVIEW_REASON_CODES = {
    "SELL_REVIEW_REQUIRED",
    "HIGH_RISK_REVIEW",
    "MARKET_STRESS",
    "BUY_REVIEW_REQUIRED",
    "BUY_OPPORTUNITY_REVIEW",
    "DAILY_LOSS_REVIEW_REQUIRED",
    "MARKET_STRESS_DAILY_LOSS",
    "RECOVERY_CANDIDATE_REVIEW_REQUIRED",
    "BROKER_DIVERGENCE_DETECTED",
    "BROKER_DUPLICATE_ORDER_RISK",
    "DUPLICATE_ORDER_SYSTEM_EMERGENCY",
    "DUPLICATE_ACTIVE_BUY_ORDER",
    "QUOTE_STALE",
    "QUOTE_STALE_FOR_MONITOR",
    "QUOTE_MISSING",
    "QUOTE_MISSING_FOR_MONITOR",
    "BROKER_SNAPSHOT_STALE",
    "BROKER_SNAPSHOT_MISSING",
    "UNKNOWN_ORDER_STATE",
    "UNCLEAR_TERMINAL_ORDER_STATE",
    "EXECUTION_POSITION_MISMATCH",
    "POSITION_WITHOUT_BROKER_SNAPSHOT",
}


def build_phase11_safety_report(result: Any, *, report_id: str | None = None) -> dict[str, Any]:
    business_date = getattr(result, "business_date", None) or "unknown_business_date"
    environment = getattr(result, "environment", None) or "unknown_environment"
    runtime_id = getattr(result, "runtime_id", None) or "unknown_runtime"
    current_state = _state_value(getattr(result, "current_state", SafetyState.NORMAL))
    next_state = _state_value(getattr(result, "next_recommended_state", getattr(result, "state_candidate", SafetyState.NORMAL)))
    decision = _decision_value(getattr(result, "overall_decision", SafetyDecision.REVIEW_REQUIRED))
    check_results = tuple(getattr(result, "check_results", getattr(result, "guard_results", ())))
    review_items = tuple(getattr(result, "review_items", ()))
    events = tuple(getattr(result, "events", ()))
    triggered_guards = list(getattr(result, "triggered_guards", ()))
    monitor_summary = dict(getattr(result, "monitor_summary", {}) or {})
    allowed_actions = allowed_actions_for(decision, next_state)
    blocked_actions = blocked_actions_for(decision, next_state)
    payload = {
        "schema_version": "phase11_safety_report_v2",
        "report_id": report_id or safety_id("phase11_safety_report"),
        "business_date": business_date,
        "generated_at": utc_now_iso(),
        "environment": environment,
        "runtime_id": runtime_id,
        "current_safety_state": current_state,
        "overall_decision": decision,
        "next_recommended_safety_state": next_state,
        "transition_allowed": bool(getattr(result, "transition_allowed", False)),
        "transition_reason": getattr(result, "transition_reason", ""),
        "triggered_guards": triggered_guards,
        "blocked_orders": _blocked_orders(review_items),
        "review_required_items": [
            _review_item_payload(item, business_date, environment, runtime_id, events, "", allowed_actions, blocked_actions, raw_response_saved_key=False)
            for item in review_items
        ],
        "emergency_candidates": _system_emergency_reason_codes(review_items),
        "individual_crash_summary": _individual_crash_summary(check_results),
        "market_crash_status": _detail_value(check_results, "market_crash_status", monitor_summary.get("market_crash_status", "unknown")),
        "market_stress_summary": _market_stress_summary(check_results, monitor_summary),
        "buy_opportunity_review": _reason_codes(review_items, {"BUY_OPPORTUNITY_REVIEW"}),
        "buy_review_required": _reason_codes(review_items, {"BUY_REVIEW_REQUIRED", "DAILY_LOSS_REVIEW_REQUIRED"}),
        "sell_review_required": _reason_codes(review_items, {"SELL_REVIEW_REQUIRED"}),
        "high_risk_review": _reason_codes(review_items, {"HIGH_RISK_REVIEW"}),
        "recovery_candidate_status": _detail_value(check_results, "recovery_candidate_status", monitor_summary.get("recovery_candidate_status", "unknown")),
        "recovery_candidate_summary": getattr(result, "recovery_candidate_summary", {}),
        "manual_unlock_summary": getattr(result, "manual_unlock_summary", {}),
        "broker_snapshot_freshness": _detail_value(check_results, "broker_snapshot_freshness", monitor_summary.get("broker_snapshot_freshness", "unknown")),
        "quote_freshness": _detail_value(check_results, "quote_freshness", monitor_summary.get("quote_freshness", "unknown")),
        "divergence_summary": _detail_value(check_results, "divergence_summary", monitor_summary.get("divergence_summary", "none")),
        "duplicate_order_summary": _duplicate_order_summary(check_results),
        "daily_loss_summary": _daily_loss_summary(check_results),
        "recommended_human_actions": [item.recommended_action for item in review_items],
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "refined_safety_confirmation": {
            "market_price_decline_triggers_emergency_stop": False,
            "market_stress_sent_to_human_review": True,
            "auto_sell_executed": False,
            "auto_buy_stop_executed": False,
            "system_faults_remain_emergency_stop_candidates": True
        },
        "no_live_order_confirmation": no_live_order_confirmation(),
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "persistence_confirmation": {
            "secret_persisted": False,
            "request_payload_persisted": False,
            "raw_payload_persisted": False,
            "plaintext_account_id_persisted": False,
            "plaintext_order_id_persisted": False,
            "plaintext_execution_id_persisted": False,
        },
        "ai_learning_use": ai_learning_use_confirmation(),
    }
    return payload


def build_review_queue_items(result: Any, *, safety_report_path: str = "") -> list[dict[str, Any]]:
    business_date = getattr(result, "business_date", None) or "unknown_business_date"
    environment = getattr(result, "environment", None) or "unknown_environment"
    runtime_id = getattr(result, "runtime_id", None) or "unknown_runtime"
    decision = _decision_value(getattr(result, "overall_decision", SafetyDecision.REVIEW_REQUIRED))
    next_state = _state_value(getattr(result, "next_recommended_state", getattr(result, "state_candidate", SafetyState.NORMAL)))
    allowed_actions = allowed_actions_for(decision, next_state)
    blocked_actions = blocked_actions_for(decision, next_state)
    events = tuple(getattr(result, "events", ()))
    items = []
    for item in getattr(result, "review_items", ()):
        if should_include_review_item(item):
            items.append(
                _review_item_payload(
                    item,
                    business_date,
                    environment,
                    runtime_id,
                    events,
                    safety_report_path,
                    allowed_actions,
                    blocked_actions,
                    raw_response_saved_key=True,
                )
            )
    return items


def should_include_review_item(item: HumanReviewItem) -> bool:
    return item.reason_code in REVIEW_REASON_CODES or item.severity.value in {"REVIEW", "BLOCK", "EMERGENCY", "WARNING"}


def allowed_actions_for(decision: str, next_state: str) -> list[str]:
    base = ["read_only_broker_sync", "quote_polling", "audit", "report_generation", "human_review"]
    if next_state in {SafetyState.MARKET_STRESS.value, SafetyState.BUY_REVIEW_REQUIRED.value, SafetyState.BUY_OPPORTUNITY_REVIEW.value, SafetyState.WARNING.value}:
        return base + ["review_buy_opportunity", "review_sell_or_hold_decision"]
    if decision == SafetyDecision.ALLOW.value and next_state in {SafetyState.NORMAL.value, SafetyState.WARNING.value}:
        return base + ["pre_order_safety_passed_candidate"]
    return base


def blocked_actions_for(decision: str, next_state: str) -> list[str]:
    blocked = [
        "broker_order_api",
        "demo_order_submit",
        "production_order_submit",
        "auto_sell",
        "auto_recovery",
        "auto_cancel",
        "auto_retry",
        "correction",
        "cancel",
        "retry",
    ]
    if next_state in {SafetyState.MARKET_STRESS.value, SafetyState.BUY_REVIEW_REQUIRED.value, SafetyState.BUY_OPPORTUNITY_REVIEW.value, SafetyState.WARNING.value}:
        blocked.append("new_buy_without_human_review")
    elif decision != SafetyDecision.ALLOW.value or next_state in {SafetyState.BUY_STOP.value, SafetyState.SYSTEM_EMERGENCY_STOP.value, SafetyState.EMERGENCY_STOP.value, SafetyState.RECOVERY_CANDIDATE.value}:
        blocked.append("new_buy")
    if next_state == SafetyState.BUY_STOP.value:
        blocked.append("new_buy_during_buy_stop")
    if next_state in {SafetyState.SYSTEM_EMERGENCY_STOP.value, SafetyState.EMERGENCY_STOP.value}:
        blocked.append("all_order_submission")
        blocked.append("normal_runtime_progression")
    return blocked


def no_live_order_confirmation() -> dict[str, bool]:
    return {
        "broker_api_connected": False,
        "websocket_connected": False,
        "demo_order_submitted": False,
        "production_order_submitted": False,
        "clm_kabu_new_order_executed": False,
    }


def ai_learning_use_confirmation() -> dict[str, Any]:
    return {
        "safety_report_used_for_ai_learning": False,
        "review_queue_used_for_ai_learning": False,
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
    }


def _review_item_payload(
    item: HumanReviewItem,
    business_date: str,
    environment: str,
    runtime_id: str,
    events: tuple[SafetyEvent, ...],
    safety_report_path: str,
    allowed_actions: list[str],
    blocked_actions: list[str],
    *,
    raw_response_saved_key: bool,
) -> dict[str, Any]:
    event = _event_by_id(events, item.event_id)
    payload = {
        "review_id": item.review_id,
        "event_id": item.event_id,
        "business_date": business_date,
        "environment": environment,
        "runtime_id": runtime_id,
        "guard": item.guard_name.value,
        "severity": item.severity.value,
        "decision": event.decision.value if event else "REVIEW_REQUIRED",
        "affected_issue_code": item.issue_code,
        "reason_code": item.reason_code,
        "message": item.message,
        "recommended_human_action": item.recommended_action,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "safety_report_path": safety_report_path,
        "requires_manual_approval": True,
        "auto_trade_executed": False,
    }
    if raw_response_saved_key:
        payload["raw_response_saved"] = False
    else:
        payload["raw_payload_saved"] = False
    return payload


def _event_by_id(events: tuple[SafetyEvent, ...], event_id: str | None) -> SafetyEvent | None:
    if not event_id:
        return None
    for event in events:
        if event.event_id == event_id:
            return event
    return None


def _state_value(value: Any) -> str:
    return value.value if isinstance(value, SafetyState) else str(value)


def _decision_value(value: Any) -> str:
    return value.value if isinstance(value, SafetyDecision) else str(value)


def _detail_value(check_results: tuple[Any, ...], key: str, default: Any) -> Any:
    for result in check_results:
        if key in result.details:
            return result.details[key]
    return default


def _reason_codes(items: tuple[HumanReviewItem, ...], reason_codes: set[str], *, severity: str | None = None) -> list[str]:
    values = []
    for item in items:
        if item.reason_code in reason_codes or (severity is not None and item.severity.value == severity):
            values.append(item.reason_code)
    return values


def _system_emergency_reason_codes(items: tuple[HumanReviewItem, ...]) -> list[str]:
    price_review_codes = {"HIGH_RISK_REVIEW", "SELL_REVIEW_REQUIRED", "MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "DAILY_LOSS_REVIEW_REQUIRED", "MARKET_STRESS_DAILY_LOSS"}
    return [
        item.reason_code
        for item in items
        if item.severity.value == "EMERGENCY" and item.reason_code not in price_review_codes
    ]


def _blocked_orders(items: tuple[HumanReviewItem, ...]) -> list[str]:
    return [
        item.reason_code
        for item in items
        if item.guard_name.value in {"DUPLICATE_ORDER", "CASH_BUFFER", "MAX_EXPOSURE", "QUOTE_STALE", "ORDER_EXECUTION_CONSISTENCY"}
    ]


def _market_stress_summary(check_results: tuple[Any, ...], monitor_summary: dict[str, Any]) -> dict[str, Any]:
    reasons = [
        result.reason_code
        for result in check_results
        if result.reason_code in {"MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW", "DAILY_LOSS_REVIEW_REQUIRED", "MARKET_STRESS_DAILY_LOSS"}
    ]
    details = [result.details for result in check_results if result.reason_code in set(reasons)]
    return {
        "market_stress_detected": bool(reasons) or bool(monitor_summary.get("market_stress_summary", {}).get("market_stress_detected")),
        "reason_codes": reasons or list(monitor_summary.get("market_stress_summary", {}).get("reason_codes", [])),
        "details": details,
        "emergency_stop": False,
        "auto_sell_executed": False,
        "auto_buy_stop": False,
        "human_review_required": bool(reasons),
    }


def _individual_crash_summary(check_results: tuple[Any, ...]) -> dict[str, Any]:
    for result in check_results:
        if result.guard_name.value == "INDIVIDUAL_CRASH":
            return {
                "reason_code": result.reason_code,
                "decision": result.decision.value,
                "severity": result.severity.value,
                "details": result.details,
            }
    return {"reason_code": "NOT_CHECKED", "decision": "ALLOW", "severity": "INFO", "details": {}}


def _duplicate_order_summary(check_results: tuple[Any, ...]) -> dict[str, Any]:
    for result in check_results:
        if result.guard_name.value in {"DUPLICATE_ORDER", "ORDER_EXECUTION_CONSISTENCY"} and "DUPLICATE" in result.reason_code:
            return {"reason_code": result.reason_code, "decision": result.decision.value, "details": result.details}
    return {"reason_code": "NO_DUPLICATE_ORDER_RISK", "decision": "ALLOW", "details": {}}


def _daily_loss_summary(check_results: tuple[Any, ...]) -> dict[str, Any]:
    for result in check_results:
        if result.guard_name.value == "DAILY_LOSS":
            return {"reason_code": result.reason_code, "decision": result.decision.value, "details": result.details}
    return {"reason_code": "NOT_CHECKED", "decision": "ALLOW", "details": {}}
