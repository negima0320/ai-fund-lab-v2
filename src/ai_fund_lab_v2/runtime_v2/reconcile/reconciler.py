"""Reconcile Runtime skeleton aggregator."""

from __future__ import annotations

import hashlib
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetState
from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerExecutionRecord,
    LedgerOrderRecord,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan
from ai_fund_lab_v2.runtime_v2.reconcile.checks import (
    check_broker_cash_vs_asset_state,
    check_broker_executions_vs_ledger_executions,
    check_broker_positions_vs_asset_state,
    check_broker_total_equity_vs_asset_state,
    check_demo_fallback_policy,
    check_ledger_orders_vs_broker_orders,
    check_pending_vs_ledger_orders,
)
from ai_fund_lab_v2.runtime_v2.reconcile.models import (
    ReconciliationFinding,
    ReconciliationResult,
    ReconciliationSeverity,
)


def run_reconciliation(
    *,
    mode: str,
    environment: str,
    business_date: str,
    pending_plan: PendingOrderPlan | None = None,
    ledger_orders: Sequence[LedgerOrderRecord] = (),
    ledger_executions: Sequence[LedgerExecutionRecord] = (),
    broker_orders: Sequence[BrokerOrderSnapshot] = (),
    broker_executions: Sequence[BrokerExecutionSnapshot] = (),
    broker_positions: Sequence[BrokerPositionSnapshot] = (),
    broker_cash: BrokerCashSnapshot | None = None,
    asset_state: CurrentAssetState | None = None,
    source: str | None = None,
    production_equivalent: bool | None = None,
    review_required: bool | None = None,
) -> ReconciliationResult:
    as_of = business_date
    findings: tuple[ReconciliationFinding, ...] = (
        *(
            check_demo_fallback_policy(
                mode=mode,
                environment=environment,
                source=source,
                review_required=review_required is True,
                production_equivalent=production_equivalent is True,
            )
            if source == "broker_orders_fallback"
            else ()
        ),
        *check_pending_vs_ledger_orders(
            pending_plan=pending_plan,
            ledger_orders=ledger_orders,
        ),
        *check_ledger_orders_vs_broker_orders(
            ledger_orders=ledger_orders,
            broker_orders=broker_orders,
        ),
        *check_broker_executions_vs_ledger_executions(
            broker_executions=broker_executions,
            ledger_executions=ledger_executions,
        ),
        *check_broker_positions_vs_asset_state(
            broker_positions=broker_positions,
            asset_state=asset_state,
        ),
        *check_broker_cash_vs_asset_state(
            broker_cash=broker_cash,
            asset_state=asset_state,
        ),
        *check_broker_total_equity_vs_asset_state(
            broker_positions=broker_positions,
            broker_cash=broker_cash,
            asset_state=asset_state,
        ),
    )
    halt = any(finding.severity == ReconciliationSeverity.HALT for finding in findings)
    blocked = any(finding.severity == ReconciliationSeverity.BLOCKED for finding in findings)
    review_required = any(
        finding.severity
        in {
            ReconciliationSeverity.REVIEW_REQUIRED,
            ReconciliationSeverity.BLOCKED,
            ReconciliationSeverity.HALT,
        }
        for finding in findings
    )
    return ReconciliationResult(
        result_id=_result_id(mode, environment, business_date, findings),
        schema_version="1",
        environment=environment,
        mode=mode,
        business_date=business_date,
        as_of=as_of,
        findings=findings,
        review_required=review_required,
        blocked=blocked,
        halt=halt,
        summary=f"{len(findings)} finding(s)",
        created_at=as_of,
    )


def _result_id(
    mode: str,
    environment: str,
    business_date: str,
    findings: tuple[ReconciliationFinding, ...],
) -> str:
    raw = "|".join((mode, environment, business_date, *(finding.finding_id for finding in findings)))
    return "reconciliation-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
