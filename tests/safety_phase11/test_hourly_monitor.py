import json
from dataclasses import replace

from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyEvent, SafetyGuardName, SafetySeverity, SafetyState


def _base_input(**overrides):
    data = {
        "business_date": "2026-06-29",
        "environment": "demo",
        "runtime_id": "runtime_test",
        "broker_snapshot": {"age_seconds": "30", "buying_power": "1000000"},
        "positions": ({"issue_code": "7203", "quantity": "100", "average_price": "1000", "market_value": "100000"},),
        "quotes": {"7203": {"age_seconds": "30", "price": "1000"}},
        "orders": (),
        "executions": (),
        "config": {"max_quote_age_seconds": "300", "max_broker_snapshot_age_seconds": "900"},
    }
    data.update(overrides)
    return HourlyMonitorInput(**data)


def test_hourly_monitor_allows_normal_data():
    result = HourlyPositionMonitor().evaluate(_base_input())
    assert result.overall_decision is SafetyDecision.ALLOW
    assert result.next_recommended_state is SafetyState.NORMAL
    assert result.monitor_summary["quote_freshness"] == "fresh"
    assert result.monitor_summary["broker_snapshot_freshness"] == "fresh"


def test_hourly_monitor_individual_minus_7_warning_review_required():
    result = HourlyPositionMonitor().evaluate(_base_input(quotes={"7203": {"age_seconds": "30", "price": "930"}}))
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert result.next_recommended_state is SafetyState.WARNING
    assert "INDIVIDUAL_DRAWDOWN_WARNING" in result.monitor_summary["triggered_reason_codes"]


def test_hourly_monitor_individual_minus_10_sell_review_required():
    result = HourlyPositionMonitor().evaluate(_base_input(quotes={"7203": {"age_seconds": "30", "price": "900"}}))
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert result.next_recommended_state is SafetyState.WARNING
    assert "SELL_REVIEW_REQUIRED" in result.monitor_summary["triggered_reason_codes"]
    assert result.monitor_summary["sell_review_required"] is True


def test_hourly_monitor_individual_minus_15_high_risk_review_not_emergency():
    result = HourlyPositionMonitor().evaluate(_base_input(quotes={"7203": {"age_seconds": "30", "price": "850"}}))
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert result.next_recommended_state is SafetyState.WARNING
    assert "HIGH_RISK_REVIEW" in result.monitor_summary["triggered_reason_codes"]
    assert result.monitor_summary["high_risk_review"] is True


def test_hourly_monitor_blocks_stale_quote():
    result = HourlyPositionMonitor().evaluate(_base_input(quotes={"7203": {"age_seconds": "999", "price": "1000"}}))
    assert result.overall_decision is SafetyDecision.BLOCK
    assert result.next_recommended_state is SafetyState.BUY_REVIEW_REQUIRED
    assert "QUOTE_STALE_FOR_MONITOR" in result.monitor_summary["triggered_reason_codes"]


def test_hourly_monitor_missing_broker_snapshot_requires_review():
    result = HourlyPositionMonitor().evaluate(_base_input(broker_snapshot={}))
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert "BROKER_SNAPSHOT_MISSING" in result.monitor_summary["triggered_reason_codes"]


def test_hourly_monitor_duplicate_active_buy_order_emergency():
    orders = (
        {"issue_code": "7203", "side": "BUY", "status": "OPEN"},
        {"issue_code": "7203", "side": "BUY", "status": "ACCEPTED"},
    )
    result = HourlyPositionMonitor().evaluate(_base_input(orders=orders))
    assert result.overall_decision is SafetyDecision.EMERGENCY_STOP
    assert result.next_recommended_state is SafetyState.SYSTEM_EMERGENCY_STOP
    assert "DUPLICATE_ACTIVE_BUY_ORDER" in result.monitor_summary["triggered_reason_codes"]


def test_hourly_monitor_execution_exists_but_position_missing_requires_review():
    executions = ({"issue_code": "6758", "side": "BUY", "status": "FILLED"},)
    result = HourlyPositionMonitor().evaluate(_base_input(executions=executions))
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert "EXECUTION_POSITION_MISMATCH" in result.monitor_summary["triggered_reason_codes"]


def test_hourly_monitor_market_crash_market_stress_review_candidate():
    result = HourlyPositionMonitor().evaluate(_base_input(candidate_universe_market_summary={"market_crash": True}))
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert result.next_recommended_state is SafetyState.MARKET_STRESS
    assert result.monitor_summary["market_crash_status"] == "market_stress"
    assert result.monitor_summary["market_stress_summary"]["market_stress_detected"] is True


def test_hourly_monitor_recovery_guard_does_not_auto_normalize():
    result = HourlyPositionMonitor().evaluate(
        _base_input(current_safety_state=SafetyState.BUY_STOP, candidate_universe_market_summary={"recovery_candidate": True})
    )
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert result.next_recommended_state is SafetyState.RECOVERY_CANDIDATE
    assert result.next_recommended_state is not SafetyState.NORMAL


def test_hourly_monitor_report_and_events_redact_forbidden_values(tmp_path):
    monitor = HourlyPositionMonitor()
    result = monitor.evaluate(
        _base_input(
            orders=(
                {"issue_code": "7203", "side": "BUY", "status": "OPEN"},
                {"issue_code": "7203", "side": "BUY", "status": "ACCEPTED"},
            )
        )
    )
    unsafe_event = SafetyEvent(
        guard_name=SafetyGuardName.ORDER_EXECUTION_CONSISTENCY,
        decision=SafetyDecision.REVIEW_REQUIRED,
        severity=SafetySeverity.REVIEW,
        reason_code="UNSAFE_TEST_EVENT",
        message="Contains forbidden details.",
        state_before=SafetyState.NORMAL,
        requires_human_review=True,
        details={
            "raw_response": "raw-secret-response",
            "raw_request": "raw-secret-request",
            "order_id": "ORDER-PLAINTEXT",
            "execution_id": "EXEC-PLAINTEXT",
            "virtual_url": "https://secret.example.test/path",
        },
    )
    result = replace(result, events=result.events + (unsafe_event,))
    event_paths, report_path = monitor.write_outputs(result, runtime_dir=tmp_path, reports_dir=tmp_path)
    combined = report_path.read_text(encoding="utf-8") + "\n" + "\n".join(path.read_text(encoding="utf-8") for path in event_paths)
    assert "raw-secret-response" not in combined
    assert "raw-secret-request" not in combined
    assert "ORDER-PLAINTEXT" not in combined
    assert "EXEC-PLAINTEXT" not in combined
    assert "secret.example.test" not in combined
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["no_live_order_confirmation"]["broker_api_connected"] is False
    assert report["no_live_order_confirmation"]["websocket_connected"] is False
