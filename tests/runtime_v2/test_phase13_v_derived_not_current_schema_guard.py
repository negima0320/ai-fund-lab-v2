from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from tests.runtime_v2.planning_fixtures import make_asset_state
from tests.runtime_v2.test_phase13_t_report_models import _report


def test_report_artifact_schema_marks_derived_not_current():
    report = _report()

    assert report.derived is True
    assert report.not_current_state is True
    assert not hasattr(report, "current_writer")
    assert not hasattr(report, "not_submit_source")


def test_notification_payload_schema_marks_derived_not_current():
    payload = build_notification_payload(report=_report(), channel="discord")

    assert payload.derived is True
    assert payload.not_current_state is True
    assert not hasattr(payload, "current_writer")
    assert not hasattr(payload, "delivery_status")


def test_audit_result_schema_marks_evidence_only_not_submit_source():
    result = run_audit(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        asset_state=make_asset_state(),
    )

    assert result.evidence_only is True
    assert result.not_submit_source is True
    assert not hasattr(result, "submit_candidate")
    assert not hasattr(result, "current_writer")


def test_reconciliation_result_schema_marks_evidence_only_not_current_writer():
    result = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    assert result.evidence_only is True
    assert result.not_submit_source is True
    assert result.not_current_state is True
    assert result.current_writer is False


def test_no_derived_or_evidence_model_is_marked_current_input():
    report = _report()
    payload = build_notification_payload(report=report, channel="discord")
    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        asset_state=make_asset_state(),
    )
    reconciliation = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    models = (report, payload, audit, reconciliation)

    assert all(getattr(model, "not_current_state", True) is True for model in models)
    assert all(getattr(model, "current_writer", False) is False for model in models)

