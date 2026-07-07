from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.audit.checks import audit_notification_payload, audit_report
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from tests.runtime_v2.planning_fixtures import make_asset_state
from tests.runtime_v2.test_phase13_t_report_models import _report


def test_report_derived_check_passes_for_valid_report():
    findings = audit_report(_report())

    assert not any(finding.finding_type == "REPORT_NOT_DERIVED" for finding in findings)
    assert not any(finding.finding_type == "REPORT_MARKED_CURRENT_STATE" for finding in findings)


def test_notification_derived_check_passes_for_valid_payload():
    payload = build_notification_payload(report=_report(), channel="discord")

    findings = audit_notification_payload(payload)

    assert not any(finding.finding_type == "NOTIFICATION_PAYLOAD_NOT_DERIVED" for finding in findings)


def test_missing_asset_state_produces_state_unknown_review_finding():
    result = run_audit(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        asset_state=None,
    )

    assert result.review_required is True
    assert any(finding.finding_type == "CURRENT_ASSET_STATE_UNKNOWN" for finding in result.findings)


def test_audit_result_is_evidence_and_not_submit_source():
    result = run_audit(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        asset_state=make_asset_state(),
    )

    assert result.evidence_only is True
    assert result.not_submit_source is True


def test_order_and_broker_order_are_not_asset_or_position_by_shape():
    report = _report()
    payload = build_notification_payload(report=report, channel="discord")

    assert not hasattr(report, "positions")
    assert not hasattr(payload, "broker_position")

