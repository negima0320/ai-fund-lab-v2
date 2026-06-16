from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.allocation_decision_loader import AllocationDecisionSet
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import BrokerSnapshotBundle
from ai_fund_lab_v2.order_manager.dependency_validator import validate_sell_first_buy_after_fill
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger
from ai_fund_lab_v2.order_manager.reconciliation import OrderManagerReconciliationResult
from ai_fund_lab_v2.order_manager.schema import OrderPlan, OrderPlanItem, OrderPlanItemSide, OrderPlanStatus, create_order_plan
from ai_fund_lab_v2.safety.lock_state_resolver import resolve_current_lock_state


def generate_order_plan(
    *,
    allocation: AllocationDecisionSet,
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
            policy_id=allocation.policy_id,
            items=[
                OrderPlanItem(
                    issue_code="",
                    side=OrderPlanItemSide.NOOP,
                    action="BLOCKED_BY_SAFETY",
                    status="REVIEW_ONLY_LOCKED",
                    reason_code=str(lock_state.get("status") or "LOCKED"),
                )
            ],
            safety_status="HALT",
            lock_state="locked",
            plan_status=OrderPlanStatus.REVIEW_ONLY_LOCKED,
            warnings=(str(lock_state.get("message") or ""),),
        )
    if reconciliation.halt_candidate:
        return create_order_plan(
            broker_snapshot_id=broker.broker_snapshot_id,
            paper_ledger_id=paper.ledger_id,
            policy_id=allocation.policy_id,
            items=[
                OrderPlanItem(
                    issue_code="",
                    side=OrderPlanItemSide.NOOP,
                    action="BLOCKED_BY_BROKER_MISMATCH",
                    status="REVIEW_ONLY_RECONCILIATION_HALT",
                    reason_code=reconciliation.status,
                )
            ],
            safety_status=reconciliation.safety_status,
            lock_state="unlocked",
            plan_status=OrderPlanStatus.REVIEW_ONLY_RECONCILIATION_HALT,
            warnings=(reconciliation.summary,),
        )
    items = _build_items(allocation=allocation, broker=broker)
    plan = create_order_plan(
        broker_snapshot_id=broker.broker_snapshot_id,
        paper_ledger_id=paper.ledger_id,
        policy_id=allocation.policy_id,
        items=items,
        safety_status=reconciliation.safety_status,
        lock_state="unlocked",
        plan_status=OrderPlanStatus.READY_FOR_REVIEW,
        warnings=(reconciliation.summary,) if reconciliation.warning else (),
    )
    validation = validate_sell_first_buy_after_fill(plan)
    if not validation.valid:
        return create_order_plan(
            broker_snapshot_id=broker.broker_snapshot_id,
            paper_ledger_id=paper.ledger_id,
            policy_id=allocation.policy_id,
            items=items,
            safety_status="WARNING",
            lock_state="unlocked",
            plan_status=OrderPlanStatus.INVALID_INPUT,
            blocked_reasons=validation.errors,
            warnings=validation.errors,
        )
    return plan


def _build_items(*, allocation: AllocationDecisionSet, broker: BrokerSnapshotBundle) -> list[OrderPlanItem]:
    sell_by_group: dict[str, str] = {}
    items: list[OrderPlanItem] = []
    for decision in allocation.decisions:
        if decision.side == "SELL":
            item = _item_from_decision(decision, side=OrderPlanItemSide.SELL, allocation=allocation)
            items.append(item)
            if decision.replacement_group_id:
                sell_by_group[decision.replacement_group_id] = item.item_id
    available_buying_power = broker.balance.buying_power * (Decimal("1") - allocation.cash_buffer_ratio)
    used_buying_power = Decimal("0")
    for decision in allocation.decisions:
        if decision.side == "HOLD":
            items.append(_item_from_decision(decision, side=OrderPlanItemSide.HOLD, allocation=allocation))
        if decision.side == "BUY":
            cash_required = decision.estimated_value
            blocked = used_buying_power + cash_required > available_buying_power
            dependency = sell_by_group.get(decision.replacement_group_id, "")
            items.append(
                _item_from_decision(
                    decision,
                    side=OrderPlanItemSide.BUY,
                    allocation=allocation,
                    status="BLOCKED_BY_CASH" if blocked else "READY_FOR_REVIEW",
                    action="REPLACE_BUY_AFTER_FILL_PLAN" if dependency else "NEW_BUY_PLAN",
                    reason_code="BUYING_POWER_AFTER_CASH_BUFFER" if blocked else decision.reason_code,
                    depends_on_fill_item_id=dependency,
                    requires_broker_snapshot_refresh=bool(dependency),
                )
            )
            if not blocked:
                used_buying_power += cash_required
    return items


def _item_from_decision(
    decision,
    *,
    side: OrderPlanItemSide,
    allocation: AllocationDecisionSet,
    status: str = "READY_FOR_REVIEW",
    action: str | None = None,
    reason_code: str | None = None,
    depends_on_fill_item_id: str = "",
    requires_broker_snapshot_refresh: bool = False,
) -> OrderPlanItem:
    return OrderPlanItem(
        issue_code=decision.issue_code,
        issue_name=decision.issue_name,
        side=side,
        action=action or f"{side.value}_PLAN",
        quantity=decision.quantity,
        lot_size=allocation.lot_size,
        estimated_price=decision.estimated_price,
        estimated_value=decision.estimated_value,
        source_decision_id=decision.decision_id,
        reason_code=reason_code or decision.reason_code,
        cash_required=decision.estimated_value if side == OrderPlanItemSide.BUY else Decimal("0"),
        sell_first_group_id=decision.replacement_group_id,
        depends_on_fill_item_id=depends_on_fill_item_id,
        status=status,
        requires_broker_snapshot_refresh=requires_broker_snapshot_refresh,
    )

