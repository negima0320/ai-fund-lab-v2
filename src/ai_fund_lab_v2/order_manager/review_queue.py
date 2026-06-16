from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.order_manager.order_plan_history import read_order_plan_history


@dataclass(frozen=True)
class ReviewQueueEntry:
    plan_id: str
    plan_status: str
    review_status: str
    generated_at: str
    approval_id: str = ""
    reviewer: str = ""
    approval_does_not_allow_live_order: bool = True


def build_review_queue(runtime_dir: Path | str = ".runtime") -> dict[str, Any]:
    runtime = Path(runtime_dir)
    history = read_order_plan_history(runtime)
    approvals = _load_approvals(runtime)
    entries: list[ReviewQueueEntry] = []
    for plan in history.plans:
        approval = approvals.get(plan.plan_id)
        review_status = _review_status(plan.plan_status.value, approval)
        entries.append(
            ReviewQueueEntry(
                plan_id=plan.plan_id,
                plan_status=plan.plan_status.value,
                review_status=review_status,
                generated_at=plan.generated_at or plan.created_at,
                approval_id=str(approval.get("approval_id", "")) if approval else "",
                reviewer=str(approval.get("reviewer", "")) if approval else "",
                approval_does_not_allow_live_order=True,
            )
        )
    grouped = {"pending_review": [], "approved": [], "rejected": [], "needs_change": [], "invalid_blocked": []}
    for entry in entries:
        grouped.setdefault(entry.review_status, []).append(sanitize_mapping(entry.__dict__))
    return {
        "queue_type": "phase8g_review_queue",
        "generated_at": utc_now_iso(),
        "approval_does_not_allow_live_order": True,
        "counts": {key: len(value) for key, value in grouped.items()},
        "groups": grouped,
        "warnings": list(history.warnings),
    }


def write_review_queue(
    runtime_dir: Path | str = ".runtime",
    *,
    output_dir: Path | str | None = None,
    fmt: str = "json",
) -> Path:
    payload = build_review_queue(runtime_dir)
    output = Path(output_dir) if output_dir is not None else Path(runtime_dir) / "order_manager" / "review"
    output.mkdir(parents=True, exist_ok=True)
    if fmt == "md":
        path = output / "phase8g_review_queue.md"
        path.write_text(render_review_queue_markdown(payload), encoding="utf-8")
        return path
    path = output / "phase8g_review_queue.json"
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render_review_queue_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase8-G Review Queue",
        "",
        f"- generated_at: {payload['generated_at']}",
        "- approval_does_not_allow_live_order: true",
        "",
    ]
    for group, entries in payload["groups"].items():
        lines.extend([f"## {group}", ""])
        if entries:
            for entry in entries:
                lines.append(
                    f"- plan_id={entry['plan_id']} plan_status={entry['plan_status']} "
                    f"approval_id={entry.get('approval_id', '')}"
                )
        else:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines)


def _load_approvals(runtime_dir: Path) -> dict[str, dict[str, Any]]:
    directory = runtime_dir / "order_manager" / "review"
    approvals: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return approvals
    for path in sorted(directory.glob("approval_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("approval_does_not_allow_live_order") is not True:
            continue
        plan_id = str(payload.get("plan_id", ""))
        if plan_id:
            approvals[plan_id] = sanitize_mapping(payload)
    return approvals


def _review_status(plan_status: str, approval: dict[str, Any] | None) -> str:
    if plan_status in {"INVALID_INPUT", "BLOCKED", "REVIEW_ONLY_LOCKED", "REVIEW_ONLY_RECONCILIATION_HALT"}:
        return "invalid_blocked"
    if not approval:
        return "pending_review"
    decision = str(approval.get("decision", ""))
    if decision in {"approved", "rejected", "needs_change"}:
        return decision
    return "pending_review"
