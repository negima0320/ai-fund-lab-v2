from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from tests.runtime_v2.planning_fixtures import make_asset_state


def test_build_report_from_current_asset_state():
    report = build_runtime_report(_input(asset_state=make_asset_state()))

    assert report.derived is True
    assert _section(report, "asset_summary").content.startswith("asset_state=asset-1")


def test_orders_and_executions_are_separate_sections():
    report = build_runtime_report(_input(ledger_orders=(object(),), ledger_executions=(object(),)))

    assert _section(report, "orders_summary").title == "Orders"
    assert _section(report, "executions_summary").title == "Executions"


def test_broker_order_is_not_treated_as_position():
    report = build_runtime_report(_input(broker_orders=(object(),), broker_positions=()))

    assert "broker_orders=1" in _section(report, "orders_summary").content
    assert "broker_positions=0" in _section(report, "positions_summary").content


def test_reconciliation_review_required_propagates_to_report():
    reconciliation = run_reconciliation(mode="demo", environment="demo", business_date="2026-07-07")

    report = build_runtime_report(_input(reconciliation_result=reconciliation))

    assert report.review_required is True
    assert _section(report, "reconciliation_summary").review_required is True


def test_report_has_source_refs():
    report = build_runtime_report(_input(asset_state=make_asset_state()))

    assert report.source_current_paths
    assert all(section.source_refs for section in report.sections)


def _input(**overrides):
    kwargs = {
        "mode": "demo",
        "environment": "demo",
        "business_date": "2026-07-07",
        "target_session_date": "2026-07-08",
    }
    kwargs.update(overrides)
    return ReportBuildInput(**kwargs)


def _section(report, section_id: str):
    return next(section for section in report.sections if section.section_id == section_id)

