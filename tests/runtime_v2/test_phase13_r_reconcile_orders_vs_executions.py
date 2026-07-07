from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import (
    normalize_broker_readonly_payload,
)
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_execution_to_ledger_record,
    project_order_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.reconcile.checks import (
    check_broker_executions_vs_ledger_executions,
    check_ledger_orders_vs_broker_orders,
)


def test_missing_broker_order_requires_review():
    bundle = _bundle()
    ledger_order = project_order_to_ledger_record(bundle.orders[0])

    findings = check_ledger_orders_vs_broker_orders(
        ledger_orders=(ledger_order,),
        broker_orders=(),
    )

    assert _has_finding(findings, "LEDGER_ORDER_MISSING_BROKER_ORDER")


def test_missing_ledger_order_requires_review():
    bundle = _bundle()

    findings = check_ledger_orders_vs_broker_orders(
        ledger_orders=(),
        broker_orders=bundle.orders,
    )

    assert _has_finding(findings, "BROKER_ORDER_MISSING_LEDGER_ORDER")


def test_order_quantity_and_status_mismatch_requires_review():
    bundle = _bundle()
    ledger_order = replace(
        project_order_to_ledger_record(bundle.orders[0]),
        quantity=50,
        status="different",
    )

    findings = check_ledger_orders_vs_broker_orders(
        ledger_orders=(ledger_order,),
        broker_orders=bundle.orders,
    )

    assert _has_finding(findings, "ORDER_QUANTITY_MISMATCH")
    assert _has_finding(findings, "ORDER_STATUS_MISMATCH")


def test_broker_execution_missing_in_ledger_requires_review():
    bundle = _bundle()

    findings = check_broker_executions_vs_ledger_executions(
        broker_executions=bundle.executions,
        ledger_executions=(),
    )

    assert _has_finding(findings, "BROKER_EXECUTION_MISSING_LEDGER_EXECUTION")


def test_ledger_execution_missing_broker_evidence_requires_review():
    bundle = _bundle()
    ledger_execution = project_execution_to_ledger_record(bundle.executions[0])

    findings = check_broker_executions_vs_ledger_executions(
        broker_executions=(),
        ledger_executions=(ledger_execution,),
    )

    assert _has_finding(findings, "LEDGER_EXECUTION_MISSING_BROKER_EVIDENCE")


def test_duplicate_execution_key_requires_review():
    bundle = _bundle()
    ledger_execution = project_execution_to_ledger_record(bundle.executions[0])
    duplicate = replace(
        ledger_execution,
        record_id="ledger-exec-duplicate",
        execution_id="other-execution",
    )

    findings = check_broker_executions_vs_ledger_executions(
        broker_executions=bundle.executions,
        ledger_executions=(ledger_execution, duplicate),
    )

    assert _has_finding(findings, "DUPLICATE_LEDGER_EXECUTION_KEY")


def test_matching_orders_and_executions_clean():
    bundle = _bundle()
    ledger_order = project_order_to_ledger_record(bundle.orders[0])
    ledger_execution = project_execution_to_ledger_record(bundle.executions[0])

    order_findings = check_ledger_orders_vs_broker_orders(
        ledger_orders=(ledger_order,),
        broker_orders=bundle.orders,
    )
    execution_findings = check_broker_executions_vs_ledger_executions(
        broker_executions=bundle.executions,
        ledger_executions=(ledger_execution,),
    )

    assert order_findings == ()
    assert execution_findings == ()


def _bundle():
    return normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07",
        orders=(
            {
                "order_ref": "ORDER-1",
                "pending_plan_id": "pending-1",
                "pending_item_id": "item-1",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "order_status": "accepted",
                "filled_quantity": 100,
                "remaining_quantity": 0,
            },
        ),
        executions=(
            {
                "execution_ref": "EXEC-1",
                "order_ref": "ORDER-1",
                "execution_key": "exec-key-1",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "price": 2500,
                "executed_at": "2026-07-07",
            },
        ),
    )


def _has_finding(findings, finding_type: str) -> bool:
    return any(finding.finding_type == finding_type for finding in findings)

