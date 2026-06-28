import json

from ai_fund_lab_v2.safety_phase11.event_writer import write_safety_events
from ai_fund_lab_v2.safety_phase11.guards import DuplicateOrderGuard
from ai_fund_lab_v2.safety_phase11.models import SafetyCheckInput
from ai_fund_lab_v2.safety_phase11.report_writer import write_safety_report
from ai_fund_lab_v2.safety_phase11.safety_manager import SafetyManager


def test_event_writer_redacts_phase11_forbidden_fields(tmp_path):
    result = DuplicateOrderGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY"},
            open_orders=({"issue_code": "7203", "side": "BUY", "status": "OPEN"},),
        )
    )
    event = result.events[0]
    event = type(event)(
        **{
            **event.__dict__,
            "details": {
                "raw_response": "raw-secret-response",
                "raw_request": "raw-secret-request",
                "order_id": "ORDER-PLAINTEXT",
                "execution_id": "EXEC-PLAINTEXT",
                "virtual_url": "https://secret.example.test/path",
                "safe_field": "kept",
            },
        }
    )
    paths = write_safety_events((event,), runtime_dir=tmp_path)
    payload_text = paths[0].read_text(encoding="utf-8")
    assert "raw-secret-response" not in payload_text
    assert "raw-secret-request" not in payload_text
    assert "ORDER-PLAINTEXT" not in payload_text
    assert "EXEC-PLAINTEXT" not in payload_text
    assert "secret.example.test" not in payload_text
    assert "kept" in payload_text


def test_report_writer_redacts_and_confirms_no_live_order(tmp_path):
    manager = SafetyManager(guards=(DuplicateOrderGuard(),))
    result = manager.evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY"},
            open_orders=({"issue_code": "7203", "side": "BUY", "status": "OPEN"},),
        )
    )
    path = write_safety_report(result, reports_dir=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["overall_decision"] == "EMERGENCY_STOP"
    assert payload["next_recommended_safety_state"] == "SYSTEM_EMERGENCY_STOP"
    assert payload["no_live_order_confirmation"]["broker_api_connected"] is False
    assert payload["no_live_order_confirmation"]["demo_order_submitted"] is False
    assert payload["no_live_order_confirmation"]["production_order_submitted"] is False
    payload_text = json.dumps(payload)
    assert "raw_response" not in payload_text
    assert "second_password" not in payload_text
