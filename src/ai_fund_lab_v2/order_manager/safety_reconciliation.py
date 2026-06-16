from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.order_manager.broker_snapshot_loader import BrokerSnapshotBundle
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger
from ai_fund_lab_v2.order_manager.reconciliation import OrderManagerReconciliationResult
from ai_fund_lab_v2.order_manager.schema import OrderPlan, OrderPlanItem, OrderPlanItemSide, create_order_plan
from ai_fund_lab_v2.safety.lock_state_resolver import resolve_current_lock_state


def build_review_only_plan_when_locked(
    broker: BrokerSnapshotBundle,
    paper: PaperLedger,
    reconciliation: OrderManagerReconciliationResult,
    runtime_dir: Path | str = ".runtime",
) -> OrderPlan:
    lock_state = resolve_current_lock_state(runtime_dir)
    if bool(lock_state.get("is_locked")):
        return create_order_plan(
            broker_snapshot_id=broker.broker_snapshot_id,
            paper_ledger_id=paper.ledger_id,
            policy_id="PHASE8_REVIEW_ONLY",
            items=[
                OrderPlanItem(
                    issue_code="",
                    side=OrderPlanItemSide.NOOP,
                    action="BLOCKED_BY_SAFETY",
                    quantity=Decimal("0"),
                    reason_code=str(lock_state.get("status") or "LOCKED"),
                    status="REVIEW_ONLY_LOCKED",
                )
            ],
            safety_status="HALT",
            lock_state="locked",
            warnings=(reconciliation.summary, str(lock_state.get("message") or "")),
        )
    return create_order_plan(
        broker_snapshot_id=broker.broker_snapshot_id,
        paper_ledger_id=paper.ledger_id,
        policy_id="PHASE8_REVIEW_ONLY",
        items=[
            OrderPlanItem(
                issue_code=position.issue_code,
                issue_name=position.issue_name,
                side=OrderPlanItemSide.HOLD,
                action="HOLD_PLAN",
                quantity=position.quantity,
                broker_position_quantity=position.quantity,
                paper_position_quantity=_paper_quantity(paper, position.issue_code),
            )
            for position in broker.positions
        ],
        safety_status=reconciliation.safety_status,
        lock_state="unlocked",
        blocked_reasons=("BROKER_PAPER_RECONCILIATION_MISMATCH",) if reconciliation.halt_candidate else (),
        warnings=(reconciliation.summary,) if reconciliation.warning else (),
    )


def _paper_quantity(paper: PaperLedger, issue_code: str) -> Decimal:
    for position in paper.positions:
        if position.issue_code == issue_code:
            return position.quantity
    return Decimal("0")


def load_phase8c_smoke_result(reports_dir: Path | str = "reports/phase_reports") -> dict[str, Any]:
    path = Path(reports_dir) / "phase8c_moomoo_readonly_smoke_result.json"
    if not path.exists():
        return {"status": "MISSING", "executed": False, "snapshot_paths": (), "message": "smoke result not found"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"status": "INVALID", "executed": False, "snapshot_paths": (), "message": "smoke result invalid"}
    return {
        "status": str(payload.get("status", "UNKNOWN")),
        "executed": bool(payload.get("executed", False)),
        "snapshot_paths": tuple(str(value) for value in payload.get("snapshot_paths", []) if value is not None),
        "message": str(payload.get("message", "")),
    }
