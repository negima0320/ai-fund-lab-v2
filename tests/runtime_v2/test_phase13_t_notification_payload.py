from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from tests.runtime_v2.test_phase13_t_report_models import _report


def test_payload_generated_from_report():
    report = _report()

    payload = build_notification_payload(report=report, channel="discord")

    assert payload.source_report_id == report.report_id
    assert payload.channel == "discord"


def test_payload_hash_is_stable_for_same_report_and_channel():
    report = _report()

    first = build_notification_payload(report=report, channel="discord")
    second = build_notification_payload(report=report, channel="discord")

    assert first.payload_hash == second.payload_hash


def test_notification_payload_is_derived_and_not_current_state():
    payload = build_notification_payload(report=_report(), channel="discord")

    assert payload.derived is True
    assert payload.not_current_state is True


def test_payload_generation_does_not_expose_delivery_status():
    payload = build_notification_payload(report=_report(), channel="discord")

    assert not hasattr(payload, "sent_at")
    assert not hasattr(payload, "status")

