from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import BrokerSnapshotBundle
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger


def reconciliation_id() -> str:
    return f"order_reconciliation_{uuid4().hex}"


@dataclass(frozen=True)
class OrderManagerMismatch:
    mismatch_type: str
    severity: str
    detail: str
    broker_value: str = ""
    paper_value: str = ""


@dataclass(frozen=True)
class OrderManagerReconciliationResult:
    broker_snapshot_id: str
    paper_ledger_id: str
    status: str
    safety_status: str
    warning: bool
    halt_candidate: bool
    mismatches: tuple[OrderManagerMismatch, ...] = ()
    summary: str = ""
    generated_at: str = field(default_factory=utc_now_iso)
    reconciliation_id: str = field(default_factory=reconciliation_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def reconcile_broker_snapshot_with_paper(
    broker: BrokerSnapshotBundle, paper: PaperLedger
) -> OrderManagerReconciliationResult:
    mismatches: list[OrderManagerMismatch] = []
    _compare_decimal(mismatches, "cash_mismatch", broker.balance.cash_available, paper.cash)
    _compare_decimal(mismatches, "buying_power_mismatch", broker.balance.buying_power, paper.buying_power)
    _compare_map(mismatches, "position_quantity_mismatch", _broker_positions(broker), _paper_positions(paper))
    _compare_map(mismatches, "open_order_mismatch", _broker_open_orders(broker), _paper_open_orders(paper))
    _compare_set(mismatches, "execution_mismatch", _broker_executions(broker), _paper_executions(paper))

    if not broker.accounts or broker.balance.broker != "moomoo":
        mismatches.append(
            OrderManagerMismatch(
                mismatch_type="broker_snapshot_invalid",
                severity="halt_candidate",
                detail="Broker snapshot is missing account records or is not moomoo.",
            )
        )
    if paper.source != "paper":
        mismatches.append(
            OrderManagerMismatch(
                mismatch_type="paper_ledger_invalid",
                severity="halt_candidate",
                detail="Paper ledger source is not paper.",
            )
        )

    halt_candidate = any(mismatch.severity == "halt_candidate" for mismatch in mismatches)
    warning = bool(mismatches)
    status = "HALT_CANDIDATE" if halt_candidate else ("WARNING" if warning else "OK")
    safety_status = "HALT" if halt_candidate else ("WARNING" if warning else "OK")
    return OrderManagerReconciliationResult(
        broker_snapshot_id=broker.broker_snapshot_id,
        paper_ledger_id=paper.ledger_id,
        status=status,
        safety_status=safety_status,
        warning=warning,
        halt_candidate=halt_candidate,
        mismatches=tuple(mismatches),
        summary="Broker and paper ledger match." if not mismatches else f"{len(mismatches)} mismatch(es) detected.",
    )


def _compare_decimal(
    mismatches: list[OrderManagerMismatch], mismatch_type: str, broker_value: Decimal, paper_value: Decimal
) -> None:
    if broker_value != paper_value:
        mismatches.append(
            OrderManagerMismatch(
                mismatch_type=mismatch_type,
                severity="halt_candidate",
                detail="Broker value and paper value differ; broker is authoritative.",
                broker_value=str(broker_value),
                paper_value=str(paper_value),
            )
        )


def _compare_map(
    mismatches: list[OrderManagerMismatch], mismatch_type: str, broker_map: dict[str, Decimal], paper_map: dict[str, Decimal]
) -> None:
    for key in sorted(set(broker_map) | set(paper_map)):
        if broker_map.get(key, Decimal("0")) != paper_map.get(key, Decimal("0")):
            mismatches.append(
                OrderManagerMismatch(
                    mismatch_type=mismatch_type,
                    severity="halt_candidate",
                    detail=f"Quantity mismatch for {key}; broker is authoritative.",
                    broker_value=str(broker_map.get(key, Decimal("0"))),
                    paper_value=str(paper_map.get(key, Decimal("0"))),
                )
            )


def _compare_set(
    mismatches: list[OrderManagerMismatch], mismatch_type: str, broker_values: set[str], paper_values: set[str]
) -> None:
    if broker_values != paper_values:
        mismatches.append(
            OrderManagerMismatch(
                mismatch_type=mismatch_type,
                severity="warning",
                detail="Execution identifiers differ between broker snapshot and paper ledger.",
                broker_value=",".join(sorted(broker_values)),
                paper_value=",".join(sorted(paper_values)),
            )
        )


def _broker_positions(broker: BrokerSnapshotBundle) -> dict[str, Decimal]:
    return {position.issue_code: position.quantity for position in broker.positions}


def _paper_positions(paper: PaperLedger) -> dict[str, Decimal]:
    return {position.issue_code: position.quantity for position in paper.positions}


def _broker_open_orders(broker: BrokerSnapshotBundle) -> dict[str, Decimal]:
    return {
        order.order_id: order.remaining_quantity
        for order in broker.orders
        if order.remaining_quantity > 0 or order.status.upper() in {"SUBMITTED", "PENDING", "PARTIAL"}
    }


def _paper_open_orders(paper: PaperLedger) -> dict[str, Decimal]:
    return {
        order.paper_order_id: order.quantity
        for order in paper.pending_orders
        if order.status.upper() in {"PENDING", "SUBMITTED", "PARTIAL"}
    }


def _broker_executions(broker: BrokerSnapshotBundle) -> set[str]:
    return {execution.execution_id for execution in broker.executions if execution.execution_id}


def _paper_executions(paper: PaperLedger) -> set[str]:
    return {execution.paper_execution_id for execution in paper.executions if execution.paper_execution_id}

