from ai_fund_lab_v2.runtime_v2.reconcile.models import ReconciliationSeverity
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation


def test_run_reconciliation_production_mode_broker_orders_fallback_halts():
    result = run_reconciliation(
        mode="production",
        environment="demo",
        business_date="2026-07-07",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=False,
    )

    assert result.halt is True
    assert _has_finding(result.findings, "PRODUCTION_BROKER_ORDERS_FALLBACK")
    assert any(finding.severity == ReconciliationSeverity.HALT for finding in result.findings)


def test_run_reconciliation_production_environment_broker_orders_fallback_halts():
    result = run_reconciliation(
        mode="demo",
        environment="production",
        business_date="2026-07-07",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=False,
    )

    assert result.halt is True
    assert _has_finding(result.findings, "PRODUCTION_BROKER_ORDERS_FALLBACK")


def test_run_reconciliation_fallback_review_required_false_requires_review():
    result = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        source="broker_orders_fallback",
        review_required=False,
        production_equivalent=False,
    )

    assert result.review_required is True
    assert _has_finding(result.findings, "FALLBACK_REVIEW_REQUIRED_FALSE")


def test_run_reconciliation_fallback_production_equivalent_true_requires_review():
    result = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=True,
    )

    assert result.review_required is True
    assert _has_finding(result.findings, "FALLBACK_PRODUCTION_EQUIVALENT_TRUE")


def test_run_reconciliation_demo_fallback_required_flags_has_no_fallback_policy_finding():
    result = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=False,
    )

    assert not _has_finding(result.findings, "PRODUCTION_BROKER_ORDERS_FALLBACK")
    assert not _has_finding(result.findings, "NON_DEMO_BROKER_ORDERS_FALLBACK")
    assert not _has_finding(result.findings, "FALLBACK_REVIEW_REQUIRED_FALSE")
    assert not _has_finding(result.findings, "FALLBACK_PRODUCTION_EQUIVALENT_TRUE")


def _has_finding(findings, finding_type: str) -> bool:
    return any(finding.finding_type == finding_type for finding in findings)

