from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso


REVIEW_STATUSES = {"pending", "approved", "rejected", "needs_change", "auto_approved_for_paper_trading"}


@dataclass(frozen=True)
class HumanReviewArtifactResult:
    status: str
    json_path: str
    markdown_path: str
    review_status: str
    order_plan_id: str
    order_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_human_review_request(
    *,
    order_plan_path: Path | str,
    decision_for: str,
    virtual_order_date: str,
    output_root: Path | str = ".runtime/phase9/human_review",
    safety_status: str = "READY_FOR_REVIEW",
) -> HumanReviewArtifactResult:
    order_plan = _load_order_plan(order_plan_path)
    _validate_order_plan_invariants(order_plan)
    items = [dict(item) for item in order_plan.get("items", []) if isinstance(item, dict)]
    order_plan_id = str(order_plan.get("run_id") or Path(order_plan_path).stem)
    payload = {
        "artifact_type": "phase9_human_review_request",
        "order_plan_id": order_plan_id,
        "decision_for": decision_for,
        "virtual_order_date": virtual_order_date,
        "virtual_execution_date": order_plan.get("virtual_execution_date") or virtual_order_date,
        "review_status": "pending",
        "reviewed_at": "",
        "reviewer_note": "",
        "safety_status": safety_status,
        "checklist": [
            "OrderPlan executable=false",
            "OrderPlan live_order_allowed=false",
            "OrderPlan requires_human_review=true",
            "Position size and cash constraints reviewed",
            "No Broker order submission",
        ],
        "items": items,
        "created_at": utc_now_iso(),
    }
    directory = Path(output_root) / decision_for
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "human_review_request.json"
    md_path = directory / "human_review_request.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_human_review_markdown(payload), encoding="utf-8")
    return HumanReviewArtifactResult(
        status="HUMAN_REVIEW_REQUEST_READY",
        json_path=str(json_path),
        markdown_path=str(md_path),
        review_status="pending",
        order_plan_id=order_plan_id,
        order_count=len(items),
    )


def render_human_review_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9 Human Review Request",
        "",
        f"- order_plan_id: {payload.get('order_plan_id')}",
        f"- decision_for: {payload.get('decision_for')}",
        f"- virtual_order_date: {payload.get('virtual_order_date')}",
        f"- virtual_execution_date: {payload.get('virtual_execution_date')}",
        f"- review_status: {payload.get('review_status')}",
        f"- safety_status: {payload.get('safety_status')}",
        "",
        "## Review Input Template",
        "",
        "- review_status: approved | rejected | needs_change",
        "- reviewed_at:",
        "- reviewer_note:",
        "",
        "## Checklist",
        "",
    ]
    for item in payload.get("checklist", []):
        lines.append(f"- [ ] {item}")
    lines.extend(["", "## OrderPlan Items", ""])
    items = payload.get("items", [])
    if not items:
        lines.append("- none")
    for item in items:
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
            "- executable: false",
            "- live_order_allowed: false",
            "- requires_human_review: true",
            "- broker_order_api_called: false",
        ]
    )
    return "\n".join(lines) + "\n"


def load_human_review(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Human review artifact must be a JSON object.")
    status = str(payload.get("review_status") or "").lower()
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Unsupported review_status: {status}")
    return payload


def _load_order_plan(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("OrderPlan artifact must be a JSON object.")
    return payload


def _validate_order_plan_invariants(order_plan: dict[str, Any]) -> None:
    if order_plan.get("executable") is not False:
        raise ValueError("OrderPlan must have executable=false.")
    if order_plan.get("live_order_allowed") is not False:
        raise ValueError("OrderPlan must have live_order_allowed=false.")
    if order_plan.get("requires_human_review") is not True:
        raise ValueError("OrderPlan must have requires_human_review=true.")
