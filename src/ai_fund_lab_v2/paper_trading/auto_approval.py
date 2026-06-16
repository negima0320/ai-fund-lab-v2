from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.approval_mode import AUTO_APPROVAL_REVIEW_STATUS, AUTO_FOR_PAPER_TRADING, validate_approval_mode


AUTO_APPROVAL_CREATED = "AUTO_APPROVAL_CREATED"
AUTO_APPROVAL_BLOCKED = "AUTO_APPROVAL_BLOCKED"


@dataclass(frozen=True)
class AutoApprovalResult:
    status: str
    json_path: str = ""
    markdown_path: str = ""
    review_status: str = ""
    approved_count: int = 0
    blocked_count: int = 0
    blocked_reasons: tuple[str, ...] = ()
    broker_order_api_called: bool = False
    live_order_allowed: bool = False
    executable: bool = False
    virtual_fill_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def create_auto_approval_artifact(
    *,
    order_plan_path: Path | str,
    decision_for: str,
    virtual_order_date: str,
    output_root: Path | str = ".runtime/phase9/auto_approval",
    approval_mode: str = AUTO_FOR_PAPER_TRADING,
    execution_mode: str = "paper-trading",
) -> AutoApprovalResult:
    mode = validate_approval_mode(approval_mode=approval_mode, execution_mode=execution_mode)
    order_plan = _load_order_plan(order_plan_path)
    invariant_blocked = _order_plan_invariant_violations(order_plan)
    if not mode.allowed or invariant_blocked:
        return AutoApprovalResult(
            status=AUTO_APPROVAL_BLOCKED,
            blocked_reasons=tuple(list(mode.blocked_reasons) + invariant_blocked),
        )
    items = [dict(item) for item in order_plan.get("items", []) if isinstance(item, dict)]
    approved_items = [item for item in items if str(item.get("side") or "").upper() in {"BUY", "SELL"}]
    blocked_items = [item for item in items if str(item.get("side") or "").upper() not in {"BUY", "SELL"}]
    payload = {
        "artifact_type": "phase9_auto_approval_artifact",
        "order_plan_id": str(order_plan.get("run_id") or Path(order_plan_path).stem),
        "decision_for": decision_for,
        "virtual_order_date": virtual_order_date,
        "virtual_execution_date": order_plan.get("virtual_execution_date") or virtual_order_date,
        "approval_mode": AUTO_FOR_PAPER_TRADING,
        "execution_mode": execution_mode,
        "review_status": AUTO_APPROVAL_REVIEW_STATUS,
        "approved_items": approved_items,
        "blocked_items": blocked_items,
        "items": approved_items,
        "safety_checks": {
            "order_plan_executable_false": order_plan.get("executable") is False,
            "order_plan_live_order_allowed_false": order_plan.get("live_order_allowed") is False,
            "order_plan_requires_human_review_true": order_plan.get("requires_human_review") is True,
            "broker_order_api_called_false": True,
            "paper_trading_only": True,
        },
        "approved_at": utc_now_iso(),
        "reviewed_at": utc_now_iso(),
        "reviewer_note": "Paper Trading only. Not broker approval.",
        "broker_order_api_called": False,
        "live_order_allowed": False,
        "executable": False,
        "virtual_fill_executed": False,
        "note": "Paper Trading only. Not broker approval.",
    }
    directory = Path(output_root) / decision_for
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "auto_approval_artifact.json"
    md_path = directory / "auto_approval_artifact.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_auto_approval_markdown(payload), encoding="utf-8")
    return AutoApprovalResult(
        status=AUTO_APPROVAL_CREATED,
        json_path=str(json_path),
        markdown_path=str(md_path),
        review_status=AUTO_APPROVAL_REVIEW_STATUS,
        approved_count=len(approved_items),
        blocked_count=len(blocked_items),
    )


def render_auto_approval_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9 Auto Approval Artifact",
        "",
        f"- order_plan_id: {payload.get('order_plan_id')}",
        f"- decision_for: {payload.get('decision_for')}",
        f"- virtual_order_date: {payload.get('virtual_order_date')}",
        f"- approval_mode: {payload.get('approval_mode')}",
        f"- review_status: {payload.get('review_status')}",
        "- note: Paper Trading only. Not broker approval.",
        "",
        "## Safety Checks",
        "",
    ]
    for key, value in payload.get("safety_checks", {}).items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Approved Items", ""])
    approved = payload.get("approved_items", [])
    if not approved:
        lines.append("- none")
    for item in approved:
        lines.append(
            "- "
            f"{item.get('side')} {item.get('code') or item.get('issue_code')}"
            f" qty={item.get('quantity') or item.get('planned_quantity')}"
            f" amount={item.get('planned_amount')}"
            f" reason={item.get('reason') or item.get('short_reason')}"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- broker_order_api_called: false",
            "- live_order_allowed: false",
            "- executable: false",
            "- virtual_fill_executed: false",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_order_plan(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("OrderPlan artifact must be a JSON object.")
    return payload


def _order_plan_invariant_violations(order_plan: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    if order_plan.get("executable") is not False:
        blocked.append("order_plan_executable_not_false")
    if order_plan.get("live_order_allowed") is not False:
        blocked.append("order_plan_live_order_allowed_not_false")
    if order_plan.get("requires_human_review") is not True:
        blocked.append("order_plan_requires_human_review_not_true")
    return blocked

