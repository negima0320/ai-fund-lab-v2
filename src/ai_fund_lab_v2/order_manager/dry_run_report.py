from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.order_manager.approval_record import HumanReviewApprovalRecord
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger
from ai_fund_lab_v2.order_manager.reconciliation import OrderManagerReconciliationResult
from ai_fund_lab_v2.order_manager.schema import OrderPlan


def write_dry_run_report(
    *,
    order_plan: OrderPlan,
    reconciliation: OrderManagerReconciliationResult,
    safety_state: dict[str, Any],
    paper_ledger: PaperLedger | None = None,
    approval_record: HumanReviewApprovalRecord | None = None,
    runtime_dir: Path | str = ".runtime",
    reports_dir: Path | str = "reports/phase_reports",
) -> tuple[Path, Path, Path]:
    payload = render_dry_run_report_json(
        order_plan=order_plan,
        reconciliation=reconciliation,
        safety_state=safety_state,
        paper_ledger=paper_ledger,
        approval_record=approval_record,
    )
    markdown = render_dry_run_report_markdown(payload)
    runtime_audit_dir = Path(runtime_dir) / "order_manager" / "audit"
    runtime_audit_dir.mkdir(parents=True, exist_ok=True)
    runtime_json = runtime_audit_dir / f"{order_plan.plan_id}_dry_run_report.json"
    runtime_md = runtime_audit_dir / f"{order_plan.plan_id}_dry_run_report.md"
    reports_path = Path(reports_dir) / f"phase8f_order_manager_dry_run_{order_plan.plan_id}.md"
    reports_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_md.write_text(markdown, encoding="utf-8")
    reports_path.write_text(markdown, encoding="utf-8")
    return runtime_json, runtime_md, reports_path


def render_dry_run_report_json(
    *,
    order_plan: OrderPlan,
    reconciliation: OrderManagerReconciliationResult,
    safety_state: dict[str, Any],
    paper_ledger: PaperLedger | None = None,
    approval_record: HumanReviewApprovalRecord | None = None,
) -> dict[str, Any]:
    payload = {
        "report_type": "phase8f_order_manager_dry_run",
        "generated_at": utc_now_iso(),
        "order_plan": order_plan.to_dict(),
        "reconciliation": _jsonable(reconciliation),
        "safety_state": sanitize_mapping(safety_state),
        "paper_ledger_dry_run": _jsonable(paper_ledger) if paper_ledger is not None else None,
        "approval_record": _jsonable(approval_record) if approval_record is not None else None,
        "phase8_boundary": {
            "executable": False,
            "live_order_allowed": False,
            "requires_human_review": True,
            "dry_run_only": True,
        },
    }
    return sanitize_mapping(payload)


def render_dry_run_report_markdown(payload: dict[str, Any]) -> str:
    order_plan = payload["order_plan"]
    reconciliation = payload["reconciliation"]
    safety = payload["safety_state"]
    approval = payload.get("approval_record")
    paper = payload.get("paper_ledger_dry_run")
    lines = [
        "# Phase8-F Order Manager Dry-run Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- plan_id: {order_plan.get('plan_id')}",
        f"- status: {order_plan.get('status')}",
        f"- policy_id: {order_plan.get('policy_id')}",
        f"- broker_snapshot_id: {order_plan.get('broker_snapshot_id')}",
        f"- paper_ledger_id: {order_plan.get('paper_ledger_id')}",
        f"- safety_status: {order_plan.get('safety_status')}",
        f"- lock_state: {order_plan.get('lock_state')}",
        f"- executable: {str(order_plan.get('executable')).lower()}",
        f"- live_order_allowed: {str(order_plan.get('live_order_allowed')).lower()}",
        f"- requires_human_review: {str(order_plan.get('requires_human_review')).lower()}",
        "",
        "## Safety",
        "",
        f"- is_locked: {str(safety.get('is_locked')).lower()}",
        f"- status: {safety.get('status')}",
        f"- source: {safety.get('source')}",
        "",
        "## Reconciliation",
        "",
        f"- reconciliation_id: {reconciliation.get('reconciliation_id')}",
        f"- status: {reconciliation.get('status')}",
        f"- halt_candidate: {str(reconciliation.get('halt_candidate')).lower()}",
        f"- summary: {reconciliation.get('summary')}",
        "",
        "## Paper Ledger Dry-run",
        "",
        f"- ledger_id: {paper.get('ledger_id') if isinstance(paper, dict) else 'not_applied'}",
        f"- source: {paper.get('source') if isinstance(paper, dict) else 'paper'}",
        f"- execution_count: {len(paper.get('executions', [])) if isinstance(paper, dict) else 0}",
        "",
        "## Human Review Approval",
        "",
        f"- approval_id: {approval.get('approval_id') if isinstance(approval, dict) else 'none'}",
        f"- decision: {approval.get('decision') if isinstance(approval, dict) else 'none'}",
        "- approval_does_not_allow_live_order: true",
        "",
        "## Phase8 Boundary",
        "",
        "Phase8-F is dry-run only. Human approval records review only and never grants execution permission.",
    ]
    return "\n".join(lines) + "\n"


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
