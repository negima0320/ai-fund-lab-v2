"""Pure reconciliation checks for Runtime v2."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetState
from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerExecutionRecord,
    LedgerOrderRecord,
    LedgerPositionRecord,
)
from ai_fund_lab_v2.runtime_v2.pending.consume import can_submit_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingOrderPlan,
    PendingPlanState,
)
from ai_fund_lab_v2.runtime_v2.reconcile.models import (
    ReconciliationFinding,
    ReconciliationSeverity,
)


def check_pending_vs_ledger_orders(
    *,
    pending_plan: PendingOrderPlan | None,
    ledger_orders: Sequence[LedgerOrderRecord],
) -> tuple[ReconciliationFinding, ...]:
    if pending_plan is None:
        return ()
    related_orders = tuple(
        order for order in ledger_orders if order.pending_plan_id == pending_plan.pending_plan_id
    )
    findings: list[ReconciliationFinding] = []
    if pending_plan.state == PendingPlanState.APPROVED and related_orders:
        findings.append(
            _finding(
                finding_type="APPROVED_PENDING_HAS_LEDGER_ORDER",
                severity=ReconciliationSeverity.REVIEW_REQUIRED,
                message="Approved pending plan already has ledger order records.",
                related_object_type="pending_order_plan",
                related_object_id=pending_plan.pending_plan_id,
                expected="no ledger orders before submit",
                actual=str(len(related_orders)),
                created_at=pending_plan.updated_at,
            )
        )
    if pending_plan.state == PendingPlanState.SUBMITTED and not related_orders:
        findings.append(
            _finding(
                finding_type="SUBMITTED_PENDING_MISSING_LEDGER_ORDER",
                severity=ReconciliationSeverity.REVIEW_REQUIRED,
                message="Submitted pending plan has no linked ledger order records.",
                related_object_type="pending_order_plan",
                related_object_id=pending_plan.pending_plan_id,
                expected="ledger order exists",
                actual="none",
                created_at=pending_plan.updated_at,
            )
        )
    if pending_plan.state == PendingPlanState.CONSUMED:
        if not pending_plan.consume.ledger_order_record_ids:
            findings.append(
                _finding(
                    finding_type="CONSUMED_PENDING_MISSING_LEDGER_LINK",
                    severity=ReconciliationSeverity.REVIEW_REQUIRED,
                    message="Consumed pending plan is missing ledger order links.",
                    related_object_type="pending_order_plan",
                    related_object_id=pending_plan.pending_plan_id,
                    expected="ledger order link",
                    actual="none",
                    created_at=pending_plan.updated_at,
                )
            )
        if can_submit_pending_plan(pending_plan, set()):
            findings.append(
                _finding(
                    finding_type="CONSUMED_PENDING_SUBMIT_CANDIDATE",
                    severity=ReconciliationSeverity.HALT,
                    message="Consumed pending plan must not be submit candidate.",
                    related_object_type="pending_order_plan",
                    related_object_id=pending_plan.pending_plan_id,
                    expected="cannot submit",
                    actual="can submit",
                    created_at=pending_plan.updated_at,
                )
            )
    return tuple(findings)


def check_ledger_orders_vs_broker_orders(
    *,
    ledger_orders: Sequence[LedgerOrderRecord],
    broker_orders: Sequence[BrokerOrderSnapshot],
) -> tuple[ReconciliationFinding, ...]:
    broker_by_ref = {order.order_ref_hash: order for order in broker_orders}
    ledger_by_ref = {order.order_id: order for order in ledger_orders}
    findings: list[ReconciliationFinding] = []
    for ledger_order in ledger_orders:
        broker_order = broker_by_ref.get(ledger_order.order_id)
        if broker_order is None:
            findings.append(_review("LEDGER_ORDER_MISSING_BROKER_ORDER", "ledger_order", ledger_order.record_id, "broker order exists", "none", ledger_order.created_at))
            continue
        if ledger_order.status and broker_order.order_status and ledger_order.status != broker_order.order_status:
            findings.append(_review("ORDER_STATUS_MISMATCH", "ledger_order", ledger_order.record_id, ledger_order.status, broker_order.order_status, ledger_order.created_at))
        if ledger_order.quantity != broker_order.quantity:
            findings.append(_review("ORDER_QUANTITY_MISMATCH", "ledger_order", ledger_order.record_id, str(ledger_order.quantity), str(broker_order.quantity), ledger_order.created_at))
    for broker_order in broker_orders:
        if broker_order.order_ref_hash not in ledger_by_ref:
            findings.append(_review("BROKER_ORDER_MISSING_LEDGER_ORDER", "broker_order", broker_order.order_ref_hash, "ledger order exists", "none", broker_order.as_of))
    return tuple(findings)


def check_broker_executions_vs_ledger_executions(
    *,
    broker_executions: Sequence[BrokerExecutionSnapshot],
    ledger_executions: Sequence[LedgerExecutionRecord],
) -> tuple[ReconciliationFinding, ...]:
    equivalent_by_order = {
        execution.order_id: execution
        for execution in ledger_executions
        if getattr(execution, "execution_evidence_type", "") == "execution_equivalent"
    }
    broker_by_ref = {execution.execution_ref_hash: execution for execution in broker_executions}
    ledger_by_ref = {execution.execution_id: execution for execution in ledger_executions}
    findings: list[ReconciliationFinding] = []
    duplicate_keys = {
        key for key, count in Counter(execution.execution_key for execution in ledger_executions).items() if count > 1
    }
    for key in duplicate_keys:
        findings.append(_review("DUPLICATE_LEDGER_EXECUTION_KEY", "ledger_execution", key, "unique execution_key", "duplicate", ""))
    for broker_execution in broker_executions:
        ledger_execution = ledger_by_ref.get(broker_execution.execution_ref_hash)
        if ledger_execution is None:
            ledger_execution = equivalent_by_order.get(broker_execution.order_ref_hash)
            if ledger_execution is None:
                findings.append(_review("BROKER_EXECUTION_MISSING_LEDGER_EXECUTION", "broker_execution", broker_execution.execution_ref_hash, "ledger execution exists", "none", broker_execution.as_of))
                continue
        if ledger_execution.symbol != broker_execution.symbol:
            findings.append(_review("EXECUTION_SYMBOL_MISMATCH", "ledger_execution", ledger_execution.record_id, ledger_execution.symbol, broker_execution.symbol, ledger_execution.created_at))
        if ledger_execution.quantity != broker_execution.quantity:
            findings.append(_review("EXECUTION_QUANTITY_MISMATCH", "ledger_execution", ledger_execution.record_id, str(ledger_execution.quantity), str(broker_execution.quantity), ledger_execution.created_at))
        if ledger_execution.price != broker_execution.price:
            findings.append(_review("EXECUTION_PRICE_MISMATCH", "ledger_execution", ledger_execution.record_id, str(ledger_execution.price), str(broker_execution.price), ledger_execution.created_at))
    for ledger_execution in ledger_executions:
        if getattr(ledger_execution, "execution_evidence_type", "") == "execution_equivalent":
            continue
        if ledger_execution.execution_id not in broker_by_ref:
            findings.append(_review("LEDGER_EXECUTION_MISSING_BROKER_EVIDENCE", "ledger_execution", ledger_execution.record_id, "broker execution evidence", "none", ledger_execution.created_at))
    if not broker_executions and equivalent_by_order:
        return tuple(findings)
    return tuple(findings)


def check_broker_positions_vs_asset_state(
    *,
    broker_positions: Sequence[BrokerPositionSnapshot],
    asset_state: CurrentAssetState | None,
) -> tuple[ReconciliationFinding, ...]:
    if asset_state is None:
        return (_review("ASSET_STATE_MISSING_FOR_POSITION_CHECK", "asset_state", "missing", "asset state exists", "none", ""),)
    asset_positions = asset_state.positions
    if asset_positions is None:
        return (_review("ASSET_POSITIONS_UNKNOWN", "asset_state", asset_state.asset_state_id, "positions known", "unknown", asset_state.created_at),)
    broker_by_symbol = {position.symbol: position for position in broker_positions}
    asset_by_symbol = {position.symbol: position for position in asset_positions}
    findings: list[ReconciliationFinding] = []
    for symbol, broker_position in broker_by_symbol.items():
        asset_position = asset_by_symbol.get(symbol)
        if asset_position is None:
            findings.append(_review("BROKER_POSITION_MISSING_IN_ASSET", "broker_position", broker_position.position_ref_hash, "asset position exists", "none", broker_position.as_of))
        elif asset_position.quantity != broker_position.quantity:
            findings.append(_review("POSITION_QUANTITY_MISMATCH", "asset_position", symbol, str(asset_position.quantity), str(broker_position.quantity), asset_state.created_at))
    for symbol, asset_position in asset_by_symbol.items():
        if symbol not in broker_by_symbol:
            findings.append(_review("ASSET_POSITION_MISSING_IN_BROKER", "asset_position", symbol, "broker position exists", "none", asset_position.as_of))
    return tuple(findings)


def check_broker_cash_vs_asset_state(
    *,
    broker_cash: BrokerCashSnapshot | None,
    asset_state: CurrentAssetState | None,
) -> tuple[ReconciliationFinding, ...]:
    if broker_cash is None:
        return (_review("BROKER_CASH_MISSING", "broker_cash", "missing", "broker cash exists", "none", ""),)
    if asset_state is None:
        return (_review("ASSET_STATE_MISSING_FOR_CASH_CHECK", "asset_state", "missing", "asset state exists", "none", broker_cash.as_of),)
    findings: list[ReconciliationFinding] = []
    if asset_state.cash is None:
        findings.append(_review("ASSET_CASH_UNKNOWN", "asset_state", asset_state.asset_state_id, "cash known", "unknown", asset_state.created_at))
    elif asset_state.cash != broker_cash.cash:
        findings.append(_review("CASH_MISMATCH", "asset_state", asset_state.asset_state_id, str(asset_state.cash), str(broker_cash.cash), asset_state.created_at))
    if asset_state.buying_power is None:
        findings.append(_review("ASSET_BUYING_POWER_UNKNOWN", "asset_state", asset_state.asset_state_id, "buying_power known", "unknown", asset_state.created_at))
    elif asset_state.buying_power != broker_cash.buying_power:
        findings.append(_review("BUYING_POWER_MISMATCH", "asset_state", asset_state.asset_state_id, str(asset_state.buying_power), str(broker_cash.buying_power), asset_state.created_at))
    return tuple(findings)


def check_demo_fallback_policy(
    *,
    mode: str,
    environment: str,
    source: str,
    review_required: bool,
    production_equivalent: bool,
) -> tuple[ReconciliationFinding, ...]:
    if source != "broker_orders_fallback":
        return ()
    findings: list[ReconciliationFinding] = []
    if mode == "production" or environment == "production":
        findings.append(
            _finding(
                finding_type="PRODUCTION_BROKER_ORDERS_FALLBACK",
                severity=ReconciliationSeverity.HALT,
                message="Production must not use broker orders fallback.",
                related_object_type="fallback_policy",
                related_object_id=source,
                expected="fallback disabled",
                actual="fallback enabled",
                created_at="",
            )
        )
    elif mode != "demo" or environment != "demo":
        findings.append(_review("NON_DEMO_BROKER_ORDERS_FALLBACK", "fallback_policy", source, "demo only", f"{mode}/{environment}", ""))
    if review_required is not True:
        findings.append(_review("FALLBACK_REVIEW_REQUIRED_FALSE", "fallback_policy", source, "review_required=true", str(review_required), ""))
    if production_equivalent is not False:
        findings.append(_review("FALLBACK_PRODUCTION_EQUIVALENT_TRUE", "fallback_policy", source, "production_equivalent=false", str(production_equivalent), ""))
    return tuple(findings)


def _review(
    finding_type: str,
    related_object_type: str,
    related_object_id: str,
    expected: str,
    actual: str,
    created_at: str,
) -> ReconciliationFinding:
    return _finding(
        finding_type=finding_type,
        severity=ReconciliationSeverity.REVIEW_REQUIRED,
        message=f"{finding_type} requires review.",
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        expected=expected,
        actual=actual,
        created_at=created_at,
    )


def _finding(
    *,
    finding_type: str,
    severity: ReconciliationSeverity,
    message: str,
    related_object_type: str,
    related_object_id: str,
    expected: str,
    actual: str,
    created_at: str,
) -> ReconciliationFinding:
    raw = "|".join((finding_type, related_object_type, related_object_id, expected, actual))
    return ReconciliationFinding(
        finding_id="finding-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
        finding_type=finding_type,
        severity=severity,
        message=message,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        expected=expected,
        actual=actual,
        review_required=severity in {ReconciliationSeverity.REVIEW_REQUIRED, ReconciliationSeverity.BLOCKED, ReconciliationSeverity.HALT},
        production_equivalent=severity != ReconciliationSeverity.HALT,
        created_at=created_at,
    )
