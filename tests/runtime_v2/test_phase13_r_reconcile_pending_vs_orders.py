from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerOrderRecord
from ai_fund_lab_v2.runtime_v2.pending.models import PendingConsumeInfo, PendingPlanState
from ai_fund_lab_v2.runtime_v2.reconcile.checks import check_pending_vs_ledger_orders
from tests.runtime_v2.pending_fixtures import make_approved_pending_plan


def test_approved_pending_with_existing_ledger_order_requires_review():
    pending = make_approved_pending_plan()

    findings = check_pending_vs_ledger_orders(
        pending_plan=pending,
        ledger_orders=(_ledger_order(pending.pending_plan_id),),
    )

    assert _has_finding(findings, "APPROVED_PENDING_HAS_LEDGER_ORDER")


def test_submitted_pending_without_ledger_order_requires_review():
    pending = replace(make_approved_pending_plan(), state=PendingPlanState.SUBMITTED)

    findings = check_pending_vs_ledger_orders(pending_plan=pending, ledger_orders=())

    assert _has_finding(findings, "SUBMITTED_PENDING_MISSING_LEDGER_ORDER")


def test_consumed_pending_without_ledger_link_requires_review():
    pending = replace(
        make_approved_pending_plan(),
        state=PendingPlanState.CONSUMED,
        consume=PendingConsumeInfo(consumed=True, consume_reason="done"),
    )

    findings = check_pending_vs_ledger_orders(
        pending_plan=pending,
        ledger_orders=(_ledger_order(pending.pending_plan_id),),
    )

    assert _has_finding(findings, "CONSUMED_PENDING_MISSING_LEDGER_LINK")


def test_clean_consumed_pending_with_link_has_no_findings():
    pending = replace(
        make_approved_pending_plan(),
        state=PendingPlanState.CONSUMED,
        consume=PendingConsumeInfo(
            consumed=True,
            consume_reason="done",
            ledger_order_record_ids=("ledger-order-1",),
        ),
    )

    findings = check_pending_vs_ledger_orders(
        pending_plan=pending,
        ledger_orders=(_ledger_order(pending.pending_plan_id),),
    )

    assert findings == ()


def _ledger_order(pending_plan_id: str) -> LedgerOrderRecord:
    return LedgerOrderRecord(
        record_id="ledger-order-1",
        record_type="order",
        schema_version="1",
        environment="demo",
        source="submit_runtime",
        created_at="2026-07-07",
        dedup_key="order-ref-hash",
        order_id="order-ref-hash",
        pending_plan_id=pending_plan_id,
        pending_item_id="item-1",
        side="BUY",
        symbol="7203",
        quantity=100,
        status="accepted",
    )


def _has_finding(findings, finding_type: str) -> bool:
    return any(finding.finding_type == finding_type for finding in findings)

