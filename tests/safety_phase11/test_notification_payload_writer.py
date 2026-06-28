import json

from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.notification_payload_writer import build_line_notification_payload, write_line_notification_payload
from ai_fund_lab_v2.safety_phase11.models import SafetyState


def _monitor_result(**overrides):
    data = {
        "business_date": "2026-06-29",
        "environment": "demo",
        "runtime_id": "runtime_notify",
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


def test_system_emergency_line_payload_is_generated(tmp_path):
    result = _monitor_result(
        orders=(
            {"issue_code": "7203", "side": "BUY", "status": "OPEN"},
            {"issue_code": "7203", "side": "BUY", "status": "ACCEPTED"},
        )
    )
    payload = build_line_notification_payload(result)
    assert payload["notification_level"] == "SYSTEM_EMERGENCY"
    assert "発注停止" in payload["message"]
    assert payload["auto_sell_executed"] is False
    assert payload["auto_recovery_executed"] is False
    assert payload["live_order_executed"] is False
    assert payload["raw_response_saved"] is False

    path = write_line_notification_payload(result, reports_dir=tmp_path)
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["line_send_executed"] is False


def test_market_stress_line_payload_is_review_not_emergency():
    payload = build_line_notification_payload(_monitor_result(candidate_universe_market_summary={"market_crash": True}))
    text = json.dumps(payload, ensure_ascii=False)
    assert payload["notification_level"] == "MARKET_STRESS"
    assert "自動停止ではありません" in text
    assert "買い場候補" in text
    assert "市場急落によりEmergency Stop" not in text


def test_buy_opportunity_review_line_payload_is_generated():
    payload = build_line_notification_payload(_monitor_result(candidate_universe_market_summary={"severe_crash": True}))
    text = json.dumps(payload, ensure_ascii=False)
    assert payload["notification_level"] == "BUY_OPPORTUNITY_REVIEW"
    assert "買い場候補として確認してください" in text
    assert "自動買い停止ではありません" in text


def test_position_review_line_payload_is_generated_and_redacted(tmp_path):
    result = _monitor_result(quotes={"7203": {"age_seconds": "30", "price": "850"}})
    path = write_line_notification_payload(result, reports_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["notification_level"] == "POSITION_REVIEW"
    assert "自動売却はしていません" in json.dumps(payload, ensure_ascii=False)
    assert payload["raw_response_saved"] is False
    assert "SECOND-PASSWORD" not in text
