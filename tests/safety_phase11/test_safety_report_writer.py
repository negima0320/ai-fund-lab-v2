import json
from dataclasses import replace

from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyEvent, SafetyGuardName, SafetySeverity, SafetyState
from ai_fund_lab_v2.safety_phase11.report_writer import write_safety_report_bundle


def _monitor_result(**overrides):
    data = {
        "business_date": "2026-06-29",
        "environment": "demo",
        "runtime_id": "runtime_report",
        "current_safety_state": SafetyState.NORMAL,
        "broker_snapshot": {"age_seconds": "30", "buying_power": "1000000"},
        "positions": ({"issue_code": "7203", "quantity": "100", "average_price": "1000", "market_value": "100000"},),
        "quotes": {"7203": {"age_seconds": "30", "price": "900"}},
        "orders": (),
        "executions": (),
        "config": {"max_quote_age_seconds": "300", "max_broker_snapshot_age_seconds": "900"},
    }
    data.update(overrides)
    return HourlyPositionMonitor().evaluate(HourlyMonitorInput(**data))


def test_safety_report_json_and_markdown_are_generated(tmp_path):
    result = _monitor_result()
    json_path, markdown_path = write_safety_report_bundle(result, reports_dir=tmp_path)
    assert json_path.exists()
    assert markdown_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["business_date"] == "2026-06-29"
    assert payload["overall_decision"] == "REVIEW_REQUIRED"
    assert payload["next_recommended_safety_state"] == "WARNING"
    assert payload["auto_sell_executed"] is False
    assert payload["auto_recovery_executed"] is False
    assert payload["no_live_order_confirmation"]["demo_order_submitted"] is False
    assert payload["sell_review_required"] == ["SELL_REVIEW_REQUIRED"]
    assert "new_buy_without_human_review" in payload["blocked_actions"]

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Phase11 Safety Report 2026-06-29" in markdown
    assert "新規買い可否:" in markdown
    assert "実発注なし" not in markdown or "clm_kabu_new_order_executed" in markdown


def test_safety_report_high_risk_review_and_redaction(tmp_path):
    result = _monitor_result(quotes={"7203": {"age_seconds": "30", "price": "850"}})
    unsafe_event = SafetyEvent(
        guard_name=SafetyGuardName.INDIVIDUAL_CRASH,
        decision=SafetyDecision.REVIEW_REQUIRED,
        severity=SafetySeverity.REVIEW,
        reason_code="HIGH_RISK_REVIEW",
        message="unsafe",
        state_before=SafetyState.NORMAL,
        requires_human_review=True,
        details={
            "raw_request": "raw-secret-request",
            "raw_response": "raw-secret-response",
            "account_id": "ACCOUNT-PLAINTEXT",
            "order_id": "ORDER-PLAINTEXT",
            "execution_id": "EXEC-PLAINTEXT",
            "auth_id": "AUTH-PLAINTEXT",
            "private_key": "KEY-PLAINTEXT",
            "virtual_url": "https://secret.example.test/path",
            "second_password": "SECOND-PASSWORD",
        },
    )
    result = replace(result, events=result.events + (unsafe_event,))
    json_path, markdown_path = write_safety_report_bundle(result, reports_dir=tmp_path)
    combined = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "HIGH_RISK_REVIEW" in combined
    assert "raw-secret-request" not in combined
    assert "raw-secret-response" not in combined
    assert "ACCOUNT-PLAINTEXT" not in combined
    assert "ORDER-PLAINTEXT" not in combined
    assert "EXEC-PLAINTEXT" not in combined
    assert "AUTH-PLAINTEXT" not in combined
    assert "KEY-PLAINTEXT" not in combined
    assert "secret.example.test" not in combined
    assert "SECOND-PASSWORD" not in combined
