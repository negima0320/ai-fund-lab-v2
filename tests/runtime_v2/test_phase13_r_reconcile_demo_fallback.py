from ai_fund_lab_v2.runtime_v2.reconcile.checks import check_demo_fallback_policy
from ai_fund_lab_v2.runtime_v2.reconcile.models import ReconciliationSeverity


def test_production_broker_orders_fallback_halts():
    findings = check_demo_fallback_policy(
        mode="production",
        environment="production",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=False,
    )

    assert any(finding.severity == ReconciliationSeverity.HALT for finding in findings)


def test_fallback_review_required_false_requires_review():
    findings = check_demo_fallback_policy(
        mode="demo",
        environment="demo",
        source="broker_orders_fallback",
        review_required=False,
        production_equivalent=False,
    )

    assert _has_finding(findings, "FALLBACK_REVIEW_REQUIRED_FALSE")


def test_fallback_production_equivalent_true_requires_review():
    findings = check_demo_fallback_policy(
        mode="demo",
        environment="demo",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=True,
    )

    assert _has_finding(findings, "FALLBACK_PRODUCTION_EQUIVALENT_TRUE")


def test_demo_fallback_with_required_flags_is_allowed():
    findings = check_demo_fallback_policy(
        mode="demo",
        environment="demo",
        source="broker_orders_fallback",
        review_required=True,
        production_equivalent=False,
    )

    assert findings == ()


def _has_finding(findings, finding_type: str) -> bool:
    return any(finding.finding_type == finding_type for finding in findings)

