from ai_fund_lab_v2.safety_phase11.emergency_stop import EmergencyStopEvaluator
from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.models import SafetyState
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine


def _monitor_result(**overrides):
    data = {
        "business_date": "2026-06-29",
        "environment": "demo",
        "runtime_id": "runtime_emergency",
        "current_safety_state": SafetyState.NORMAL,
        "broker_snapshot": {"age_seconds": "30", "buying_power": "1000000"},
        "positions": ({"issue_code": "7203", "quantity": "100", "average_price": "1000", "market_value": "100000"},),
        "quotes": {"7203": {"age_seconds": "30", "price": "1000"}},
        "orders": (),
        "executions": (),
        "config": {"max_quote_age_seconds": "300", "max_broker_snapshot_age_seconds": "900"},
    }
    data.update(overrides)
    return HourlyPositionMonitor().evaluate(HourlyMonitorInput(**data))


def test_manual_emergency_flag_forces_emergency_stop_decision():
    result = _monitor_result()
    decision = EmergencyStopEvaluator().evaluate(result, manual_flag_active=True)
    assert decision.emergency_required is True
    assert decision.next_state is SafetyState.SYSTEM_EMERGENCY_STOP
    assert "MANUAL_EMERGENCY_STOP" in decision.reason_codes


def test_individual_minus_15_is_not_system_emergency_candidate():
    result = _monitor_result(quotes={"7203": {"age_seconds": "30", "price": "850"}})
    decision = EmergencyStopEvaluator().evaluate(result)
    assert decision.emergency_required is False
    assert "HIGH_RISK_REVIEW" not in decision.reason_codes


def test_duplicate_active_buy_order_is_emergency_candidate():
    result = _monitor_result(
        orders=(
            {"issue_code": "7203", "side": "BUY", "status": "OPEN"},
            {"issue_code": "7203", "side": "BUY", "status": "ACCEPTED"},
        )
    )
    decision = EmergencyStopEvaluator().evaluate(result)
    assert decision.emergency_required is True
    assert "DUPLICATE_ACTIVE_BUY_ORDER" in decision.reason_codes
    assert "ORDER_EXECUTION_CONSISTENCY" in decision.triggered_guards


def test_critical_missing_or_stale_broker_snapshot_is_emergency_candidate():
    missing = _monitor_result(broker_snapshot={})
    missing_decision = EmergencyStopEvaluator().evaluate(missing)
    assert missing_decision.emergency_required is True
    assert "BROKER_SNAPSHOT_MISSING" in missing_decision.reason_codes

    stale = _monitor_result(broker_snapshot={"age_seconds": "9999", "buying_power": "1000000"})
    stale_decision = EmergencyStopEvaluator().evaluate(stale)
    assert stale_decision.emergency_required is True
    assert "BROKER_SNAPSHOT_STALE" in stale_decision.reason_codes


def test_emergency_state_transitions_are_fail_closed():
    for state in SafetyState:
        machine = SafetyStateMachine(state)
        next_machine, result = machine.transition_to(SafetyState.EMERGENCY_STOP)
        assert result.allowed is True
        assert next_machine.current_state is SafetyState.EMERGENCY_STOP

    machine = SafetyStateMachine(SafetyState.EMERGENCY_STOP)
    next_machine, result = machine.transition_to(SafetyState.NORMAL)
    assert result.allowed is False
    assert next_machine.current_state is SafetyState.EMERGENCY_STOP


def test_emergency_blocked_and_allowed_actions_are_constrained():
    decision = EmergencyStopEvaluator().evaluate(_monitor_result(), manual_flag_active=True)
    assert "new_buy" in decision.blocked_actions
    assert "new_sell_auto_execution" in decision.blocked_actions
    assert "retry" in decision.blocked_actions
    assert "automatic_recovery" in decision.blocked_actions
    assert "normal_runtime_progression" in decision.blocked_actions
    assert set(decision.allowed_actions) == {"read_only_broker_sync", "quote_polling", "report_generation", "audit", "human_review"}
