from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.order_manager.reconciliation import OrderManagerReconciliationResult
from ai_fund_lab_v2.order_manager.schema import OrderPlan


def write_human_review_report(
    *,
    order_plan: OrderPlan,
    reconciliation: OrderManagerReconciliationResult,
    runtime_dir: Path | str = ".runtime",
    reports_dir: Path | str = "docs/phase_reports",
) -> tuple[Path, Path]:
    content = render_human_review_report(order_plan=order_plan, reconciliation=reconciliation)
    runtime_path = _review_dir(runtime_dir) / f"{order_plan.plan_id}.md"
    docs_path = Path(reports_dir) / f"phase8d_human_review_{order_plan.plan_id}.md"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(content, encoding="utf-8")
    docs_path.write_text(content, encoding="utf-8")
    return runtime_path, docs_path


def render_human_review_report(*, order_plan: OrderPlan, reconciliation: OrderManagerReconciliationResult) -> str:
    buy_items = [item for item in order_plan.items if item.side.value == "BUY"]
    sell_items = [item for item in order_plan.items if item.side.value == "SELL"]
    hold_items = [item for item in order_plan.items if item.side.value == "HOLD"]
    lines = [
        "# Phase8 Human Review Report",
        "",
        f"- plan_id: {order_plan.plan_id}",
        f"- plan_status: {order_plan.plan_status.value}",
        f"- generated_at: {utc_now_iso()}",
        f"- safety_status: {order_plan.safety_status}",
        f"- broker_snapshot_id: {order_plan.broker_snapshot_id}",
        f"- paper_ledger_id: {order_plan.paper_ledger_id}",
        f"- executable: {str(order_plan.executable).lower()}",
        f"- live_order_allowed: {str(order_plan.live_order_allowed).lower()}",
        f"- requires_human_review: {str(order_plan.requires_human_review).lower()}",
        "",
        "## Reconciliation Summary",
        "",
        f"- reconciliation_id: {reconciliation.reconciliation_id}",
        f"- status: {reconciliation.status}",
        f"- warning: {str(reconciliation.warning).lower()}",
        f"- halt_candidate: {str(reconciliation.halt_candidate).lower()}",
        f"- summary: {reconciliation.summary}",
        "",
        "## Mismatches",
        "",
    ]
    if reconciliation.mismatches:
        for mismatch in reconciliation.mismatches:
            lines.append(
                f"- {mismatch.mismatch_type}: {mismatch.detail} "
                f"(broker={mismatch.broker_value}, paper={mismatch.paper_value})"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## SELL_FIRST_BUY_AFTER_FILL Dependencies",
            "",
            *_dependency_lines(order_plan),
            "",
            "## Blocked Reasons",
            "",
            *_blocked_reason_lines(order_plan),
            "",
            "## Approval Record Notice",
            "",
            "Human approval in Phase8 records review only.",
            "Approval does not allow live order.",
            "",
            "## BUY Candidates",
            "",
            *_item_lines(buy_items),
            "",
            "## SELL Candidates",
            "",
            *_item_lines(sell_items),
            "",
            "## HOLD Candidates",
            "",
            *_item_lines(hold_items),
            "",
            "## Phase8 Boundary",
            "",
            "Phase8では実発注しない。",
            "This report is for human review only.",
        ]
    )
    return "\n".join(lines) + "\n"


def _item_lines(items) -> list[str]:
    if not items:
        return ["- none"]
    return [
        f"- {item.side.value} {item.issue_code} {item.issue_name} qty={item.quantity} "
        f"action={item.action} executable={str(item.executable).lower()}"
        for item in items
    ]


def _dependency_lines(order_plan: OrderPlan) -> list[str]:
    lines: list[str] = []
    by_id = {item.item_id: item for item in order_plan.items}
    for item in order_plan.items:
        if item.depends_on_fill_item_id:
            dependency = by_id.get(item.depends_on_fill_item_id)
            lines.append(
                f"- BUY {item.issue_code} depends_on={item.depends_on_fill_item_id} "
                f"dependency_side={dependency.side.value if dependency else 'UNKNOWN'} "
                f"requires_broker_snapshot_refresh={str(item.requires_broker_snapshot_refresh).lower()}"
            )
    return lines or ["- none"]


def _blocked_reason_lines(order_plan: OrderPlan) -> list[str]:
    return [f"- {reason}" for reason in order_plan.blocked_reasons] or ["- none"]


def _review_dir(runtime_dir: Path | str) -> Path:
    return Path(runtime_dir) / "order_manager" / "review"
