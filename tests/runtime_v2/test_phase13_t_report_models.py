from ai_fund_lab_v2.runtime_v2.report.models import ReportArtifact, ReportSection


def test_report_artifact_is_derived_and_not_current_state():
    report = _report()

    assert report.derived is True
    assert report.not_current_state is True


def test_report_sections_have_source_refs():
    section = ReportSection(
        section_id="asset",
        title="Asset",
        content="asset",
        source_refs=("persistent_ledger/state.json",),
        review_required=False,
        severity="INFO",
    )

    assert section.source_refs == ("persistent_ledger/state.json",)


def test_report_can_carry_review_required():
    report = _report(review_required=True)

    assert report.review_required is True


def _report(review_required=False):
    return ReportArtifact(
        report_id="report-1",
        schema_version="1",
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        target_session_date="2026-07-08",
        report_type="runtime",
        sections=(),
        source_current_paths=("persistent_ledger/state.json",),
        source_history_refs=("reports/history",),
        review_required=review_required,
        blocked=False,
        halt=False,
        created_at="2026-07-07",
    )

