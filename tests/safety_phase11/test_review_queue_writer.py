import json

from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.models import SafetyState
from ai_fund_lab_v2.safety_phase11.review_queue_writer import write_review_queue, write_runtime_review_queue
from ai_fund_lab_v2.safety_phase11.report_writer import write_safety_report


def _result_for_review(**overrides):
    data = {
        "business_date": "2026-06-29",
        "environment": "demo",
        "runtime_id": "runtime_review",
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


def test_review_queue_json_is_generated_for_sell_review_required(tmp_path):
    result = _result_for_review()
    report_path = write_safety_report(result, reports_dir=tmp_path)
    queue_path = write_review_queue(result, safety_report_path=report_path, reports_dir=tmp_path)
    runtime_queue_path = write_runtime_review_queue(result, safety_report_path=report_path, runtime_dir=tmp_path)
    assert queue_path.exists()
    assert runtime_queue_path.exists()

    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    assert payload["item_count"] >= 1
    reason_codes = [item["reason_code"] for item in payload["items"]]
    assert "SELL_REVIEW_REQUIRED" in reason_codes
    item = payload["items"][0]
    assert item["requires_manual_approval"] is True
    assert item["auto_trade_executed"] is False
    assert item["raw_response_saved"] is False
    assert str(report_path) == item["safety_report_path"]


def test_review_queue_includes_high_risk_review_and_recovery_candidate(tmp_path):
    emergency = _result_for_review(quotes={"7203": {"age_seconds": "30", "price": "850"}})
    emergency_path = write_review_queue(emergency, reports_dir=tmp_path)
    emergency_payload = json.loads(emergency_path.read_text(encoding="utf-8"))
    assert "HIGH_RISK_REVIEW" in [item["reason_code"] for item in emergency_payload["items"]]

    recovery = _result_for_review(current_safety_state=SafetyState.BUY_STOP, quotes={"7203": {"age_seconds": "30", "price": "1000"}}, candidate_universe_market_summary={"recovery_candidate": True})
    recovery_path = write_review_queue(recovery, reports_dir=tmp_path)
    recovery_payload = json.loads(recovery_path.read_text(encoding="utf-8"))
    assert "RECOVERY_CANDIDATE_REVIEW_REQUIRED" in [item["reason_code"] for item in recovery_payload["items"]]
    assert all("new_buy" in item["blocked_actions"] for item in recovery_payload["items"])


def test_review_queue_redacts_forbidden_values(tmp_path):
    result = _result_for_review(
        orders=(
            {"issue_code": "7203", "side": "BUY", "status": "OPEN", "order_id": "ORDER-PLAINTEXT"},
            {"issue_code": "7203", "side": "BUY", "status": "ACCEPTED", "raw_response": "raw-secret-response"},
        )
    )
    queue_path = write_review_queue(result, safety_report_path="https://secret.example.test/report?auth_id=AUTH", reports_dir=tmp_path)
    text = queue_path.read_text(encoding="utf-8")
    assert "ORDER-PLAINTEXT" not in text
    assert "raw-secret-response" not in text
    assert "secret.example.test" not in text
    assert "AUTH" not in text
