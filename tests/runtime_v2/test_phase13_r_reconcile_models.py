from ai_fund_lab_v2.runtime_v2.reconcile.models import (
    ReconciliationFinding,
    ReconciliationResult,
    ReconciliationSeverity,
)
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation


def test_reconciliation_finding_has_severity():
    finding = ReconciliationFinding(
        finding_id="finding-1",
        finding_type="TEST",
        severity=ReconciliationSeverity.REVIEW_REQUIRED,
        message="needs review",
        related_object_type="test",
        related_object_id="test-1",
        expected="expected",
        actual="actual",
        review_required=True,
        production_equivalent=True,
        created_at="2026-07-07",
    )

    assert finding.severity == ReconciliationSeverity.REVIEW_REQUIRED


def test_reconciliation_result_aggregates_review_required():
    result = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    assert isinstance(result, ReconciliationResult)
    assert result.review_required is True
    assert result.findings


def test_halt_and_blocked_flags_are_aggregated():
    halt_finding = ReconciliationFinding(
        finding_id="finding-halt",
        finding_type="HALT_TEST",
        severity=ReconciliationSeverity.HALT,
        message="halt",
        related_object_type="test",
        related_object_id="test",
        expected="safe",
        actual="unsafe",
        review_required=True,
        production_equivalent=False,
        created_at="2026-07-07",
    )
    blocked_finding = ReconciliationFinding(
        finding_id="finding-blocked",
        finding_type="BLOCKED_TEST",
        severity=ReconciliationSeverity.BLOCKED,
        message="blocked",
        related_object_type="test",
        related_object_id="test",
        expected="safe",
        actual="blocked",
        review_required=True,
        production_equivalent=True,
        created_at="2026-07-07",
    )

    assert _aggregate_halt((halt_finding,)) is True
    assert _aggregate_blocked((blocked_finding,)) is True


def _aggregate_halt(findings):
    return any(finding.severity == ReconciliationSeverity.HALT for finding in findings)


def _aggregate_blocked(findings):
    return any(finding.severity == ReconciliationSeverity.BLOCKED for finding in findings)

