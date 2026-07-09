from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.notification.models import DeliveryQueueStatus
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload_from_summary
from ai_fund_lab_v2.runtime_v2.notification.queue import build_delivery_queue
from ai_fund_lab_v2.runtime_v2.notification.sender import DiscordNotificationSender, LineNotificationSender
from tests.runtime_v2.planning_fixtures import make_asset_state


def test_phase14e34_notification_payload_contract_from_runtime_summary():
    payload = build_notification_payload_from_summary(
        summary=_summary(),
        channel="runtime_v2",
        source_report_id="report-e34",
    )

    assert payload.business_date == "2026-07-08"
    assert payload.run_id == "run-e34"
    assert payload.current_portfolio["total_equity"] == 1_010_200
    assert payload.today_operation["sell_filled_count"] == 1
    assert payload.execution_equivalent_count == 1
    assert payload.warnings == ("payload-only",)
    assert payload.review_required is False
    assert payload.severity == "INFO"
    assert payload.derived is True
    assert payload.not_current_state is True
    assert not hasattr(payload, "delivery_status")


def test_phase14e34_delivery_queue_and_stub_results_do_not_send():
    payload = build_notification_payload_from_summary(
        summary=_summary(),
        channel="runtime_v2",
        source_report_id="report-e34",
    )
    queue = build_delivery_queue(payload=payload, channels=("line", "discord"), delivery_mode="payload-only")
    results = (
        LineNotificationSender().deliver(payload=payload, queue_entry=queue[0]),
        DiscordNotificationSender().deliver(payload=payload, queue_entry=queue[1]),
    )

    assert tuple(entry.status for entry in queue) == (DeliveryQueueStatus.PENDING, DeliveryQueueStatus.PENDING)
    assert tuple(result.status for result in results) == (
        DeliveryQueueStatus.NOT_IMPLEMENTED,
        DeliveryQueueStatus.NOT_IMPLEMENTED,
    )
    assert all(result.attempted is False for result in results)
    assert all(result.sent is False for result in results)
    assert all(result.review_required is False for result in results)


def test_phase14e34_audit_accepts_payload_queue_and_not_implemented_results():
    payload = build_notification_payload_from_summary(
        summary=_summary(),
        channel="runtime_v2",
        source_report_id="report-e34",
    )
    queue = build_delivery_queue(payload=payload, channels=("line", "discord"), delivery_mode="payload-only")
    results = (
        LineNotificationSender().deliver(payload=payload, queue_entry=queue[0]),
        DiscordNotificationSender().deliver(payload=payload, queue_entry=queue[1]),
    )

    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date="2026-07-08",
        notification_payload=payload,
        delivery_queue=queue,
        delivery_results=results,
        asset_state=make_asset_state(),
    )

    assert audit.review_required is False
    assert audit.blocked is False
    assert audit.halt is False
    assert audit.findings == ()


def _summary():
    return {
        "business_date": "2026-07-08",
        "runtime_mode": "demo",
        "environment": "demo",
        "current_run": {"run_id": "run-e34"},
        "current_portfolio": {
            "cash": 1_010_200,
            "buying_power": 1_010_200,
            "market_value": 0,
            "total_equity": 1_010_200,
            "position_count": 0,
        },
        "today_operation": {
            "accepted_count": 1,
            "rejected_count": 0,
            "execution_equivalent_count": 1,
            "sell_filled_count": 1,
            "review_required": False,
        },
        "warning_summary": {"notes": ("payload-only",)},
        "reconcile": {"review_required": False},
        "notification": {"execution_equivalent_count": 1},
    }
