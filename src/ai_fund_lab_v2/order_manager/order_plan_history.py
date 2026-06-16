from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.order_manager.order_plan_store import OrderPlanStoreError, load_order_plan, order_plan_directory
from ai_fund_lab_v2.order_manager.schema import OrderPlan


@dataclass(frozen=True)
class OrderPlanHistory:
    plans: tuple[OrderPlan, ...]
    warnings: tuple[str, ...] = ()


def read_order_plan_history(
    runtime_dir: Path | str = ".runtime",
    *,
    status_filter: str | None = None,
    skip_invalid: bool = True,
) -> OrderPlanHistory:
    directory = order_plan_directory(runtime_dir)
    if not directory.exists():
        return OrderPlanHistory(plans=(), warnings=(f"missing plan directory: {directory}",))
    plans: list[OrderPlan] = []
    warnings: list[str] = []
    for path in sorted(directory.glob("*.json")):
        try:
            plan = load_order_plan(path)
        except OrderPlanStoreError as exc:
            if not skip_invalid:
                raise
            warnings.append(f"skipped invalid plan: {path.name}: {exc}")
            continue
        if status_filter and plan.plan_status.value != status_filter:
            continue
        plans.append(plan)
    plans.sort(key=lambda plan: (plan.generated_at or plan.created_at, plan.plan_id), reverse=True)
    return OrderPlanHistory(plans=tuple(plans), warnings=tuple(warnings))


def load_latest_order_plan(runtime_dir: Path | str = ".runtime", *, status_filter: str | None = None) -> OrderPlan:
    history = read_order_plan_history(runtime_dir, status_filter=status_filter)
    if not history.plans:
        raise OrderPlanStoreError("No stored OrderPlan found.")
    return history.plans[0]


def load_order_plan_by_id(plan_id: str, runtime_dir: Path | str = ".runtime") -> OrderPlan:
    path = order_plan_directory(runtime_dir) / f"{plan_id}.json"
    if not path.exists():
        raise OrderPlanStoreError(f"Stored OrderPlan not found: {plan_id}")
    return load_order_plan(path)


def sanitized_order_plan_summary(order_plan: OrderPlan) -> dict[str, Any]:
    payload = {
        "plan_id": order_plan.plan_id,
        "generated_at": order_plan.generated_at or order_plan.created_at,
        "schema_version": order_plan.schema_version,
        "source": order_plan.source,
        "status": order_plan.plan_status.value,
        "policy_id": order_plan.policy_id,
        "broker_snapshot_id": order_plan.broker_snapshot_id,
        "paper_ledger_id": order_plan.paper_ledger_id,
        "executable": False,
        "live_order_allowed": False,
        "requires_human_review": True,
        "item_count": len(order_plan.items),
    }
    return sanitize_mapping(payload)
