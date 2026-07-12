"""Review Pending to Submit Pending promotion contract evidence.

This module produces dry-run evidence only. It never writes the authoritative
pending slot and never performs Submit or Broker Write.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.human_review import validate_human_review_artifact
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    load_runtime_safety_decision,
    safety_allows_action,
)


HUMAN_APPROVAL_SCHEMA_VERSION = "runtime_v2_human_submit_approval_v1"
PROMOTION_CANDIDATE_SCHEMA_VERSION = "runtime_v2_submit_pending_promotion_candidate_v1"
LINKAGE_SCHEMA_VERSION = "runtime_v2_review_pending_linkage_v1"
APPROVED_FOR_PENDING_PROMOTION = "APPROVED_FOR_PENDING_PROMOTION"
APPROVAL_STATUSES = {
    "DRAFT",
    APPROVED_FOR_PENDING_PROMOTION,
    "REJECTED",
    "REVOKED",
    "EXPIRED",
}


@dataclass(frozen=True)
class SubmitPendingPromotionReviewResult:
    status: str
    reason: str
    human_approval_path: str
    review_pending_linkage_path: str
    promotion_candidate_path: str
    promotion_candidate_status: str
    promotion_allowed: bool
    safety_submit_permission: str
    pending_slot_status: str
    generated_at: str

    def to_stage_details(self) -> dict[str, Any]:
        return {
            "submit_pending_promotion_review_status": self.status,
            "submit_pending_promotion_review_reason": self.reason,
            "human_approval_path": self.human_approval_path,
            "review_pending_linkage_path": self.review_pending_linkage_path,
            "promotion_candidate_path": self.promotion_candidate_path,
            "promotion_candidate_status": self.promotion_candidate_status,
            "promotion_allowed": self.promotion_allowed,
            "safety_submit_permission": self.safety_submit_permission,
            "pending_slot_status": self.pending_slot_status,
            "submit_executed": False,
            "broker_write_performed": False,
            "approval_apply_performed": False,
            "authoritative_pending_mutated": False,
            "apply_requested": False,
            "apply_executed": False,
        }


def run_submit_pending_promotion_review(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    capital_deployment_policy_path: Path | str,
    approved_issue_codes: tuple[str, ...] = ("4591",),
    human_approval_path: Path | str | None = None,
    now: datetime | None = None,
) -> SubmitPendingPromotionReviewResult:
    root = Path(runtime_root)
    now_dt = _ensure_utc(now or datetime.now(timezone.utc))
    generated_at = _iso(now_dt)
    review_pending_path = root / "runtime_state" / "sell_hold_review_only" / business_date / "review_pending.json"
    review_pending = _read_json(review_pending_path)
    review_output_path = Path(str(review_pending.get("review_output_path") or ""))
    if not review_output_path.is_absolute():
        review_output_path = _base_dir(root) / review_output_path
    review_output = _read_json(review_output_path)
    human_review = validate_human_review_artifact(runtime_root=root, business_date=business_date, now=now_dt)
    safety = load_runtime_safety_decision(runtime_root=root, business_date=business_date, mode=mode)
    policy = load_capital_deployment_policy(Path(capital_deployment_policy_path))
    policy_hash = capital_deployment_policy_hash(policy)
    current_path = root / "persistent_ledger" / "state.json"
    current = _read_json(current_path)
    broker_latest_path = root / "runtime_state" / "broker_readonly" / "latest.json"
    broker_latest = _read_json(broker_latest_path) if broker_latest_path.is_file() else {}
    broker_snapshot_path = _resolve_runtime_path(root, str(broker_latest.get("snapshot_path") or ""))
    broker_snapshot = _read_json(broker_snapshot_path) if broker_snapshot_path and broker_snapshot_path.is_file() else {}
    pending_slot_path = root / "pending_order_plan" / "pending_order_plan.json"
    pending_slot = _read_json(pending_slot_path)

    linkage = _build_review_pending_linkage(
        review_pending=review_pending,
        review_pending_path=review_pending_path,
        review_output=review_output,
        review_output_path=review_output_path,
        human_review_payload=human_review.payload,
        approved_issue_codes=approved_issue_codes,
        generated_at=generated_at,
    )
    linkage_dir = root / "runtime_state" / "sell_hold_review_only" / business_date
    linkage_path = linkage_dir / "review_pending_linkage_evidence.json"
    _write_json(linkage_path, linkage)

    approval_path = Path(human_approval_path) if human_approval_path else _default_approval_path(
        root=root,
        business_date=business_date,
        linkage=linkage,
    )
    if human_approval_path is None:
        approval = _build_acceptance_human_approval(
            business_date=business_date,
            generated_at=generated_at,
            now_dt=now_dt,
            review_pending_path=review_pending_path,
            review_pending_hash=linkage["source_review_pending_hash"],
            linkage=linkage,
            policy_hash=policy_hash,
            safety_decision_id=safety.safety_decision_id,
        )
        _write_json(approval_path, approval)
    else:
        approval = _read_json(approval_path) if approval_path.is_file() else {}

    validation = _validate_promotion_inputs(
        business_date=business_date,
        now_dt=now_dt,
        review_pending=review_pending,
        linkage=linkage,
        human_review_payload=human_review.payload,
        human_review_ready=human_review.ready,
        approval=approval,
        policy_hash=policy_hash,
        safety=safety,
        current=current,
        broker_latest=broker_latest,
        broker_snapshot=broker_snapshot,
        pending_slot=pending_slot,
    )
    selected_items = [
        item
        for item in linkage["items"]
        if item["review_item_id"] in set(approval.get("approved_item_ids") or ())
    ]
    candidate_id = "promotion-candidate-" + _short_hash(
        {
            "approval_id": approval.get("approval_id"),
            "review_pending_hash": linkage["source_review_pending_hash"],
            "selected_items": selected_items,
        }
    )
    safety_allowed, safety_status, safety_reason = safety_allows_action(safety, action="submit", side="SELL")
    non_safety_blocks = [
        reason for reason in validation["promotion_block_reasons"] if reason != "safety_submit_blocked"
    ]
    if non_safety_blocks:
        candidate_status = "REVIEW_REQUIRED"
        status = "REVIEW_REQUIRED"
        reason = "promotion_validation_review_required"
    elif not safety_allowed:
        candidate_status = "READY_BUT_SAFETY_BLOCKED"
        status = "PASS"
        reason = "promotion_contract_ready_with_safety_block"
    else:
        candidate_status = "READY_FOR_APPLY"
        status = "PASS"
        reason = "promotion_contract_ready_for_apply"

    candidate_dir = root / "runtime_state" / "pending_promotion_candidate" / business_date
    candidate_path = candidate_dir / f"{candidate_id}.json"
    candidate = {
        "schema_version": PROMOTION_CANDIDATE_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "business_date": business_date,
        "generated_at": generated_at,
        "source_review_pending_path": str(review_pending_path),
        "source_review_pending_hash": linkage["source_review_pending_hash"],
        "review_pending_linkage_path": str(linkage_path),
        "approval_id": approval.get("approval_id") or "",
        "approval_path": str(approval_path),
        "approval_hash": _hash_json(approval),
        "selected_items": selected_items,
        "rejected_items": [
            item for item in linkage["items"] if item["review_item_id"] not in set(approval.get("approved_item_ids") or ())
        ],
        "policy_hash": policy_hash,
        "safety_decision_id": safety.safety_decision_id,
        "current_state_id": str(current.get("asset_state_id") or ""),
        "current_state_path": str(current_path),
        "broker_snapshot_id": str(broker_latest.get("snapshot_path") or ""),
        "broker_snapshot_path": str(broker_snapshot_path) if broker_snapshot_path else "",
        "target_pending_plan_id": "pending-promotion-" + _short_hash(candidate_id),
        "target_session": business_date,
        "expires_at": approval.get("expires_at") or "",
        "promotion_status": candidate_status,
        "promotion_allowed": candidate_status == "READY_FOR_APPLY",
        "promotion_block_reasons": validation["promotion_block_reasons"],
        "validation": validation,
        "safety_submit_permission": "ALLOWED" if safety_allowed else safety_status,
        "safety_submit_reason": safety_reason,
        "apply_requested": False,
        "apply_executed": False,
        "submit_executed": False,
        "broker_write_performed": False,
        "authoritative_pending_mutated": False,
    }
    _write_json(candidate_path, candidate)
    return SubmitPendingPromotionReviewResult(
        status=status,
        reason=reason,
        human_approval_path=str(approval_path),
        review_pending_linkage_path=str(linkage_path),
        promotion_candidate_path=str(candidate_path),
        promotion_candidate_status=candidate_status,
        promotion_allowed=bool(candidate["promotion_allowed"]),
        safety_submit_permission=str(candidate["safety_submit_permission"]),
        pending_slot_status=str(validation["pending_slot_status"]),
        generated_at=generated_at,
    )


def _build_review_pending_linkage(
    *,
    review_pending: dict[str, Any],
    review_pending_path: Path,
    review_output: dict[str, Any],
    review_output_path: Path,
    human_review_payload: dict[str, Any],
    approved_issue_codes: tuple[str, ...],
    generated_at: str,
) -> dict[str, Any]:
    review_output_hash = _hash_json(review_output)
    review_pending_hash = _hash_json(review_pending)
    items = []
    approved_set = set(approved_issue_codes)
    for item in review_pending.get("items") or ():
        issue = str(item.get("issue_code") or "")
        side = "SELL" if float(item.get("runtime_sell_quantity") or 0) > 0 else "HOLD"
        review_item_id = f"review-item-{issue}"
        linked = {
            "business_date": review_pending.get("business_date") or "",
            "issue_code": issue,
            "side": side,
            "review_item_id": review_item_id,
            "source_human_review_id": human_review_payload.get("review_id") or "",
            "source_safety_event_id": human_review_payload.get("event_id") or "",
            "source_safety_review_id": human_review_payload.get("review_id") or "",
            "source_pm_decision_id": "pm-decision-" + _short_hash(
                {
                    "issue_code": issue,
                    "review_decision": item.get("review_decision"),
                    "reason": item.get("reason"),
                    "review_output_hash": review_output_hash,
                }
            ),
            "source_review_output_id": "review-output-" + _short_hash(review_output_hash),
            "source_review_output_hash": review_output_hash,
            "runtime_sell_quantity": float(item.get("runtime_sell_quantity") or 0),
            "review_decision": item.get("review_decision") or "",
            "eligible_for_approval_fixture": issue in approved_set and side == "SELL",
        }
        linked["review_item_hash"] = _hash_json(linked)
        items.append(linked)
    return {
        "schema_version": LINKAGE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_review_pending_path": str(review_pending_path),
        "source_review_pending_hash": review_pending_hash,
        "source_review_output_path": str(review_output_path),
        "source_review_output_hash": review_output_hash,
        "submit_allowed": False,
        "broker_write_allowed": False,
        "authoritative_submit_pending": False,
        "items": items,
    }


def _build_acceptance_human_approval(
    *,
    business_date: str,
    generated_at: str,
    now_dt: datetime,
    review_pending_path: Path,
    review_pending_hash: str,
    linkage: dict[str, Any],
    policy_hash: str,
    safety_decision_id: str,
) -> dict[str, Any]:
    approved = [item for item in linkage["items"] if item.get("eligible_for_approval_fixture")]
    approved_item_ids = [item["review_item_id"] for item in approved]
    approval_id = "human-submit-approval-" + _short_hash({"approved": approved_item_ids, "at": generated_at})
    return {
        "schema_version": HUMAN_APPROVAL_SCHEMA_VERSION,
        "approval_id": approval_id,
        "approval_status": APPROVED_FOR_PENDING_PROMOTION,
        "business_date": business_date,
        "approved_at": generated_at,
        "expires_at": _iso(now_dt.replace(hour=23, minute=59, second=59, microsecond=0)),
        "revoked_at": None,
        "review_pending_path": str(review_pending_path),
        "review_pending_hash": review_pending_hash,
        "source_human_review_id": approved[0]["source_human_review_id"] if approved else "",
        "source_safety_event_id": approved[0]["source_safety_event_id"] if approved else "",
        "source_safety_review_id": approved[0]["source_safety_review_id"] if approved else "",
        "approved_item_ids": approved_item_ids,
        "rejected_item_ids": [item["review_item_id"] for item in linkage["items"] if item["review_item_id"] not in approved_item_ids],
        "approved_side": "SELL",
        "approved_quantities": {item["review_item_id"]: item["runtime_sell_quantity"] for item in approved},
        "approved_issue_codes": {item["review_item_id"]: item["issue_code"] for item in approved},
        "approved_review_item_hashes": {item["review_item_id"]: item["review_item_hash"] for item in approved},
        "policy_hash": policy_hash,
        "safety_decision_id": safety_decision_id,
        "automatic_trade_authorized": False,
        "broker_write_authorized": False,
        "authoritative_pending_promotion_authorized": True,
        "reviewer_type": "human_operator",
        "acceptance_fixture": True,
    }


def _validate_promotion_inputs(
    *,
    business_date: str,
    now_dt: datetime,
    review_pending: dict[str, Any],
    linkage: dict[str, Any],
    human_review_payload: dict[str, Any],
    human_review_ready: bool,
    approval: dict[str, Any],
    policy_hash: str,
    safety: Any,
    current: dict[str, Any],
    broker_latest: dict[str, Any],
    broker_snapshot: dict[str, Any],
    pending_slot: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    checks: dict[str, str] = {}
    checks["review_pending_schema"] = _pass_or(
        review_pending.get("schema_version") == "runtime_v2_review_pending_v1",
        "review_pending_schema_invalid",
        reasons,
    )
    checks["human_review_linkage"] = _pass_or(human_review_ready, "human_review_not_ready", reasons)
    checks["approval_schema"] = _pass_or(
        approval.get("schema_version") == HUMAN_APPROVAL_SCHEMA_VERSION,
        "human_approval_schema_invalid",
        reasons,
    )
    status = str(approval.get("approval_status") or "")
    checks["approval_status"] = _pass_or(
        status == APPROVED_FOR_PENDING_PROMOTION,
        "human_approval_status_not_approved_for_pending_promotion",
        reasons,
    )
    if status not in APPROVAL_STATUSES:
        reasons.append("human_approval_status_unknown")
        checks["approval_status_known"] = "REVIEW_REQUIRED"
    else:
        checks["approval_status_known"] = "PASS"
    approved_at = _parse_dt(str(approval.get("approved_at") or ""))
    expires_at = _parse_dt(str(approval.get("expires_at") or ""))
    checks["approval_expires_at_present"] = _pass_or(expires_at is not None, "approval_expires_at_missing", reasons)
    if expires_at is not None:
        checks["approval_not_expired"] = _pass_or(expires_at > now_dt, "approval_expired", reasons)
    checks["approval_approved_at_present"] = _pass_or(approved_at is not None, "approval_approved_at_missing", reasons)
    if approved_at is not None:
        checks["approval_not_future"] = _pass_or(approved_at <= now_dt, "approval_approved_at_future", reasons)
    checks["approval_business_date"] = _pass_or(
        approval.get("business_date") == business_date,
        "approval_business_date_mismatch",
        reasons,
    )
    revoked_at = str(approval.get("revoked_at") or "")
    checks["approval_not_revoked"] = _pass_or(
        not revoked_at and status != "REVOKED",
        "approval_revoked",
        reasons,
    )
    checks["review_pending_hash"] = _pass_or(
        approval.get("review_pending_hash") == linkage.get("source_review_pending_hash"),
        "review_pending_hash_mismatch",
        reasons,
    )
    for key, reason in (
        ("source_human_review_id", "human_review_id_mismatch"),
        ("source_safety_event_id", "safety_event_id_mismatch"),
        ("source_safety_review_id", "safety_review_id_mismatch"),
    ):
        expected = str(human_review_payload.get("review_id" if key != "source_safety_event_id" else "event_id") or "")
        checks[key] = _pass_or(str(approval.get(key) or "") == expected, reason, reasons)
    checks["policy_hash"] = _pass_or(approval.get("policy_hash") == policy_hash, "policy_hash_mismatch", reasons)
    checks["safety_decision_id"] = _pass_or(
        approval.get("safety_decision_id") == safety.safety_decision_id,
        "safety_decision_id_mismatch",
        reasons,
    )
    item_by_id = {item["review_item_id"]: item for item in linkage.get("items") or []}
    approved_ids = [str(item_id) for item_id in approval.get("approved_item_ids") or []]
    checks["approved_item_ids_present"] = _pass_or(bool(approved_ids), "approved_item_ids_missing", reasons)
    for item_id in approved_ids:
        item = item_by_id.get(item_id)
        if item is None:
            reasons.append("approved_item_out_of_scope")
            continue
        if item["side"] != approval.get("approved_side"):
            reasons.append("approved_side_mismatch")
        approved_qty = float((approval.get("approved_quantities") or {}).get(item_id) or -1)
        if approved_qty != float(item["runtime_sell_quantity"]):
            reasons.append("approved_quantity_mismatch")
        approved_hash = (approval.get("approved_review_item_hashes") or {}).get(item_id)
        if approved_hash != item["review_item_hash"]:
            reasons.append("review_item_hash_mismatch")
    checks["approved_items"] = "PASS" if not any(r in reasons for r in (
        "approved_item_out_of_scope",
        "approved_side_mismatch",
        "approved_quantity_mismatch",
        "review_item_hash_mismatch",
    )) else "REVIEW_REQUIRED"
    checks["current_freshness"] = _pass_or(
        current.get("current_position_status") == "READY" and current.get("current_valuation_status") == "READY",
        "current_not_ready",
        reasons,
    )
    checks["broker_freshness"] = _pass_or(
        broker_latest.get("freshness_status") == "READY" and broker_latest.get("authenticity_status") == "READY",
        "broker_not_ready",
        reasons,
    )
    broker_positions = broker_snapshot.get("positions") or []
    broker_issue_codes = {str(item.get("issue_code") or "") for item in broker_positions if isinstance(item, dict)}
    missing_broker = [
        item_by_id[item_id]["issue_code"]
        for item_id in approved_ids
        if item_id in item_by_id and item_by_id[item_id]["issue_code"] not in broker_issue_codes
    ]
    checks["broker_available_quantity"] = "SKIPPED_DUE_SAFETY_SUBMIT_BLOCK" if missing_broker else "PASS"
    safety_allowed, safety_status, _ = safety_allows_action(safety, action="submit", side="SELL")
    if not safety_allowed:
        reasons.append("safety_submit_blocked")
    checks["safety_submit_scope"] = "PASS" if safety_allowed else safety_status
    pending_state = str(pending_slot.get("state") or pending_slot.get("status") or "")
    active_pending = bool(pending_slot.get("active_pending", pending_state not in {"EMPTY", ""}))
    pending_ok = pending_state == "EMPTY" and not active_pending
    checks["pending_slot_empty"] = _pass_or(pending_ok, "pending_slot_not_empty", reasons)
    return {
        "validation_checks": checks,
        "promotion_block_reasons": sorted(set(reasons)),
        "pending_slot_status": pending_state or "UNKNOWN",
        "broker_available_quantity_missing_symbols": missing_broker,
        "submit_allowed_by_safety": safety_allowed,
    }


def _default_approval_path(*, root: Path, business_date: str, linkage: dict[str, Any]) -> Path:
    seed = _short_hash({"business_date": business_date, "review_pending_hash": linkage["source_review_pending_hash"]})
    return root / "runtime_state" / "human_approval" / business_date / f"human-submit-approval-{seed}.json"


def _resolve_runtime_path(root: Path, value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return _base_dir(root) / path


def _base_dir(root: Path) -> Path:
    return root.parent if root.name == ".runtime" else Path(".")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _short_hash(payload: Any) -> str:
    return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()[:16]


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _ensure_utc(parsed)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _ensure_utc(value).isoformat()


def _pass_or(condition: bool, reason: str, reasons: list[str]) -> str:
    if condition:
        return "PASS"
    reasons.append(reason)
    return "REVIEW_REQUIRED"
