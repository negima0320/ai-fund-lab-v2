"""Authoritative Submit Pending apply review evidence.

This module is deliberately review-only. It builds an apply candidate and
precondition evidence, but it never writes the authoritative Pending slot and
never performs Submit or Broker Write.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.pending_promotion import (
    APPROVED_FOR_PENDING_PROMOTION,
    HUMAN_APPROVAL_SCHEMA_VERSION,
    PROMOTION_CANDIDATE_SCHEMA_VERSION,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    load_runtime_safety_decision,
    safety_allows_action,
)


APPLY_CANDIDATE_SCHEMA_VERSION = "runtime_v2_authoritative_pending_apply_candidate_v1"
AUTHORITATIVE_PENDING_CANDIDATE_SCHEMA_VERSION = "runtime_v2_authoritative_pending_plan_candidate_v1"


@dataclass(frozen=True)
class AuthoritativePendingApplyReviewResult:
    status: str
    reason: str
    apply_candidate_path: str
    apply_candidate_status: str
    apply_allowed: bool
    apply_preconditions_status: str
    toctou_revalidation_status: str
    safety_apply_permission: str
    pending_slot_status: str
    generated_at: str

    def to_stage_details(self) -> dict[str, Any]:
        return {
            "authoritative_pending_apply_review_status": self.status,
            "authoritative_pending_apply_review_reason": self.reason,
            "authoritative_pending_apply_candidate_path": self.apply_candidate_path,
            "apply_candidate_status": self.apply_candidate_status,
            "apply_allowed": self.apply_allowed,
            "apply_preconditions_status": self.apply_preconditions_status,
            "toctou_revalidation_status": self.toctou_revalidation_status,
            "safety_apply_permission": self.safety_apply_permission,
            "pending_slot_status": self.pending_slot_status,
            "submit_executed": False,
            "execution_executed": False,
            "broker_write_performed": False,
            "authoritative_pending_mutated": False,
            "apply_requested": False,
            "apply_executed": False,
        }


def run_authoritative_pending_apply_review(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    capital_deployment_policy_path: Path | str,
    promotion_candidate_path: Path | str | None = None,
    now: datetime | None = None,
) -> AuthoritativePendingApplyReviewResult:
    root = Path(runtime_root)
    now_dt = _ensure_utc(now or datetime.now(timezone.utc))
    generated_at = _iso(now_dt)
    candidate_path = (
        Path(promotion_candidate_path)
        if promotion_candidate_path
        else _latest_promotion_candidate_path(root=root, business_date=business_date)
    )
    promotion_candidate = _read_json(candidate_path) if candidate_path and candidate_path.is_file() else {}
    approval_path = _resolve_runtime_path(root, str(promotion_candidate.get("approval_path") or ""))
    approval = _read_json(approval_path) if approval_path and approval_path.is_file() else {}
    policy = load_capital_deployment_policy(Path(capital_deployment_policy_path))
    policy_hash = capital_deployment_policy_hash(policy)
    safety = load_runtime_safety_decision(runtime_root=root, business_date=business_date, mode=mode)
    current_path = root / "persistent_ledger" / "state.json"
    current = _read_json(current_path)
    broker_latest_path = root / "runtime_state" / "broker_readonly" / "latest.json"
    broker_latest = _read_json(broker_latest_path) if broker_latest_path.is_file() else {}
    broker_snapshot_path = _resolve_runtime_path(root, str(broker_latest.get("snapshot_path") or ""))
    broker_snapshot = _read_json(broker_snapshot_path) if broker_snapshot_path and broker_snapshot_path.is_file() else {}
    pending_slot_path = root / "pending_order_plan" / "pending_order_plan.json"
    pending_slot = _read_json(pending_slot_path)

    validation = _validate_apply_inputs(
        business_date=business_date,
        now_dt=now_dt,
        promotion_candidate_path=candidate_path,
        promotion_candidate=promotion_candidate,
        approval=approval,
        policy_hash=policy_hash,
        safety=safety,
        current=current,
        broker_latest=broker_latest,
        broker_snapshot=broker_snapshot,
        pending_slot=pending_slot,
    )
    apply_allowed_by_safety, safety_status, safety_reason = safety_allows_action(
        safety,
        action="submit",
        side="SELL",
    )
    non_safety_blocks = [
        reason for reason in validation["apply_block_reasons"] if reason != "safety_submit_blocked"
    ]
    if non_safety_blocks:
        apply_status = "REVIEW_REQUIRED"
        status = "REVIEW_REQUIRED"
        reason = "authoritative_pending_apply_preconditions_review_required"
    elif not apply_allowed_by_safety:
        apply_status = "READY_BUT_SAFETY_BLOCKED"
        status = "PASS"
        reason = "authoritative_pending_apply_contract_ready_but_safety_blocked"
    else:
        apply_status = "READY_FOR_AUTHORITATIVE_APPLY"
        status = "PASS"
        reason = "authoritative_pending_apply_contract_ready"

    apply_candidate_id = "apply-candidate-" + _short_hash(
        {
            "promotion_candidate": promotion_candidate.get("candidate_id"),
            "promotion_candidate_hash": _hash_json(promotion_candidate),
            "approval_hash": _hash_json(approval),
            "target_pending_plan_id": promotion_candidate.get("target_pending_plan_id"),
        }
    )
    pending_candidate = _build_authoritative_pending_candidate(
        apply_candidate_id=apply_candidate_id,
        promotion_candidate=promotion_candidate,
        approval=approval,
        business_date=business_date,
        mode=mode,
        generated_at=generated_at,
        apply_status=apply_status,
        safety=safety,
        validation=validation,
    )
    apply_candidate = {
        "schema_version": APPLY_CANDIDATE_SCHEMA_VERSION,
        "apply_candidate_id": apply_candidate_id,
        "generated_at": generated_at,
        "business_date": business_date,
        "runtime_mode": mode,
        "source_promotion_candidate_id": str(promotion_candidate.get("candidate_id") or ""),
        "source_promotion_candidate_path": str(candidate_path) if candidate_path else "",
        "source_promotion_candidate_hash": _hash_json(promotion_candidate),
        "source_approval_id": str(approval.get("approval_id") or ""),
        "source_approval_path": str(approval_path) if approval_path else "",
        "source_approval_hash": _hash_json(approval),
        "target_pending_plan_id": str(promotion_candidate.get("target_pending_plan_id") or ""),
        "target_session": str(promotion_candidate.get("target_session") or ""),
        "side": "SELL",
        "items": pending_candidate["items"],
        "constraints": pending_candidate["constraints"],
        "policy_hash": policy_hash,
        "safety_decision_id": safety.safety_decision_id,
        "current_state_id": str(current.get("asset_state_id") or ""),
        "broker_snapshot_id": str(broker_latest.get("snapshot_path") or ""),
        "expires_at": str(promotion_candidate.get("expires_at") or approval.get("expires_at") or ""),
        "apply_status": apply_status,
        "apply_allowed": apply_status == "READY_FOR_AUTHORITATIVE_APPLY",
        "apply_block_reasons": validation["apply_block_reasons"],
        "apply_requested": False,
        "apply_executed": False,
        "authoritative_pending_mutated": False,
        "submit_executed": False,
        "execution_executed": False,
        "broker_write_performed": False,
        "apply_preconditions_status": validation["apply_preconditions_status"],
        "toctou_revalidation_status": validation["toctou_revalidation_status"],
        "safety_apply_permission": "ALLOWED" if apply_allowed_by_safety else safety_status,
        "safety_apply_reason": safety_reason,
        "pending_slot_status": validation["pending_slot_status"],
        "before_pending_snapshot": {
            "path": str(pending_slot_path),
            "hash": _hash_json(pending_slot),
            "state": str(pending_slot.get("state") or pending_slot.get("status") or ""),
            "active_pending": bool(pending_slot.get("active_pending", False)),
        },
        "after_pending_snapshot": {
            "path": str(pending_slot_path),
            "hash": _hash_json(pending_slot),
            "unchanged": True,
        },
        "authoritative_pending_candidate": pending_candidate,
        "apply_contract": _apply_contract(),
        "atomicity_contract": _atomicity_contract(),
        "idempotency_contract": _idempotency_contract(),
        "backup_history_contract": _backup_history_contract(),
        "validation": validation,
    }
    output_dir = root / "runtime_state" / "authoritative_pending_apply_candidate" / business_date
    output_path = output_dir / f"{apply_candidate_id}.json"
    _write_json(output_path, apply_candidate)
    return AuthoritativePendingApplyReviewResult(
        status=status,
        reason=reason,
        apply_candidate_path=str(output_path),
        apply_candidate_status=apply_status,
        apply_allowed=bool(apply_candidate["apply_allowed"]),
        apply_preconditions_status=str(validation["apply_preconditions_status"]),
        toctou_revalidation_status=str(validation["toctou_revalidation_status"]),
        safety_apply_permission=str(apply_candidate["safety_apply_permission"]),
        pending_slot_status=str(validation["pending_slot_status"]),
        generated_at=generated_at,
    )


def _validate_apply_inputs(
    *,
    business_date: str,
    now_dt: datetime,
    promotion_candidate_path: Path | None,
    promotion_candidate: dict[str, Any],
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
    promotion_hash = _hash_json(promotion_candidate)
    approval_hash = _hash_json(approval)
    checks["promotion_candidate_path"] = _pass_or(
        bool(promotion_candidate_path and promotion_candidate_path.is_file()),
        "promotion_candidate_missing",
        reasons,
    )
    checks["promotion_candidate_schema"] = _pass_or(
        promotion_candidate.get("schema_version") == PROMOTION_CANDIDATE_SCHEMA_VERSION,
        "promotion_candidate_schema_invalid",
        reasons,
    )
    status = str(promotion_candidate.get("promotion_status") or "")
    checks["promotion_candidate_status"] = _pass_or(
        status in {"READY_BUT_SAFETY_BLOCKED", "READY_FOR_APPLY"},
        "promotion_candidate_status_not_apply_eligible",
        reasons,
    )
    checks["promotion_apply_requested_false"] = _pass_or(
        promotion_candidate.get("apply_requested") is False,
        "promotion_apply_requested_already_true",
        reasons,
    )
    checks["promotion_apply_executed_false"] = _pass_or(
        promotion_candidate.get("apply_executed") is False,
        "promotion_candidate_already_applied",
        reasons,
    )
    declared_candidate_hash = str(promotion_candidate.get("candidate_hash") or "")
    if declared_candidate_hash:
        checks["promotion_candidate_hash"] = _pass_or(
            declared_candidate_hash == promotion_hash,
            "promotion_candidate_hash_mismatch",
            reasons,
        )
    else:
        checks["promotion_candidate_hash"] = "PASS_NOT_DECLARED"
    checks["approval_schema"] = _pass_or(
        approval.get("schema_version") == HUMAN_APPROVAL_SCHEMA_VERSION,
        "human_approval_schema_invalid",
        reasons,
    )
    checks["approval_status"] = _pass_or(
        approval.get("approval_status") == APPROVED_FOR_PENDING_PROMOTION,
        "human_approval_status_not_approved_for_pending_promotion",
        reasons,
    )
    checks["approval_hash"] = _pass_or(
        promotion_candidate.get("approval_hash") == approval_hash,
        "approval_hash_mismatch",
        reasons,
    )
    checks["approval_business_date"] = _pass_or(
        approval.get("business_date") == business_date,
        "approval_business_date_mismatch",
        reasons,
    )
    expires_at = _parse_dt(str(approval.get("expires_at") or promotion_candidate.get("expires_at") or ""))
    checks["approval_expires_at_present"] = _pass_or(expires_at is not None, "approval_expires_at_missing", reasons)
    if expires_at is not None:
        checks["approval_not_expired"] = _pass_or(expires_at > now_dt, "approval_expired", reasons)
    checks["approval_not_revoked"] = _pass_or(
        not approval.get("revoked_at") and approval.get("approval_status") != "REVOKED",
        "approval_revoked",
        reasons,
    )
    checks["approval_not_consumed"] = _pass_or(
        not approval.get("approval_consumed") and not approval.get("consumed_at"),
        "approval_already_consumed",
        reasons,
    )
    checks["approval_authorizes_pending_promotion"] = _pass_or(
        approval.get("authoritative_pending_promotion_authorized") is True,
        "approval_does_not_authorize_authoritative_pending_promotion",
        reasons,
    )
    checks["approval_does_not_authorize_trade"] = _pass_or(
        approval.get("automatic_trade_authorized") is False and approval.get("broker_write_authorized") is False,
        "approval_trade_authority_scope_invalid",
        reasons,
    )
    checks["review_pending_hash"] = _pass_or(
        promotion_candidate.get("source_review_pending_hash") == approval.get("review_pending_hash"),
        "review_pending_hash_mismatch",
        reasons,
    )
    checks["policy_hash"] = _pass_or(
        promotion_candidate.get("policy_hash") == policy_hash and approval.get("policy_hash") == policy_hash,
        "policy_hash_mismatch",
        reasons,
    )
    checks["safety_decision_id"] = _pass_or(
        promotion_candidate.get("safety_decision_id") == safety.safety_decision_id
        and approval.get("safety_decision_id") == safety.safety_decision_id,
        "safety_decision_id_mismatch",
        reasons,
    )
    checks["current_state_id"] = _pass_or(
        promotion_candidate.get("current_state_id") == current.get("asset_state_id"),
        "current_state_id_mismatch",
        reasons,
    )
    checks["current_ready"] = _pass_or(
        current.get("current_position_status") == "READY" and current.get("current_valuation_status") == "READY",
        "current_not_ready",
        reasons,
    )
    checks["broker_snapshot_id"] = _pass_or(
        promotion_candidate.get("broker_snapshot_id") == broker_latest.get("snapshot_path"),
        "broker_snapshot_id_mismatch",
        reasons,
    )
    checks["broker_freshness"] = _pass_or(
        broker_latest.get("freshness_status") == "READY" and broker_latest.get("authenticity_status") == "READY",
        "broker_not_ready",
        reasons,
    )
    checks["target_session"] = _pass_or(
        promotion_candidate.get("target_session") == business_date,
        "target_session_mismatch",
        reasons,
    )
    pending_state = str(pending_slot.get("state") or pending_slot.get("status") or "")
    active_pending = bool(pending_slot.get("active_pending", pending_state not in {"EMPTY", ""}))
    checks["pending_slot_empty"] = _pass_or(
        pending_state == "EMPTY" and not active_pending,
        "pending_slot_not_empty",
        reasons,
    )
    selected_items = list(promotion_candidate.get("selected_items") or [])
    approved_ids = {str(item_id) for item_id in approval.get("approved_item_ids") or []}
    checks["selected_items_present"] = _pass_or(bool(selected_items), "selected_items_missing", reasons)
    current_quantities = _current_quantities(current)
    broker_quantities = _broker_available_quantities(broker_snapshot)
    safety_allowed, _, _ = safety_allows_action(safety, action="submit", side="SELL")
    item_checks: list[dict[str, Any]] = []
    for item in selected_items:
        item_id = str(item.get("review_item_id") or "")
        issue_code = str(item.get("issue_code") or "")
        quantity = float(item.get("runtime_sell_quantity") or 0)
        item_reasons: list[str] = []
        if item_id not in approved_ids:
            item_reasons.append("selected_item_not_approved")
        if str(item.get("side") or "") != "SELL":
            item_reasons.append("selected_item_side_not_sell")
        if quantity <= 0:
            item_reasons.append("selected_item_quantity_not_positive")
        if quantity > current_quantities.get(issue_code, 0.0):
            item_reasons.append("sell_quantity_exceeds_runtime_owned_current")
        if safety_allowed and quantity > broker_quantities.get(issue_code, 0.0):
            item_reasons.append("sell_quantity_exceeds_broker_available_quantity")
        review_hash = (approval.get("approved_review_item_hashes") or {}).get(item_id)
        if review_hash != item.get("review_item_hash"):
            item_reasons.append("review_item_hash_mismatch")
        reasons.extend(item_reasons)
        item_checks.append(
            {
                "review_item_id": item_id,
                "issue_code": issue_code,
                "quantity": quantity,
                "runtime_owned_current_quantity": current_quantities.get(issue_code, 0.0),
                "broker_available_quantity": broker_quantities.get(issue_code, 0.0),
                "broker_quantity_validation": "PASS"
                if safety_allowed and quantity <= broker_quantities.get(issue_code, 0.0)
                else ("SKIPPED_DUE_SAFETY_APPLY_BLOCK" if not safety_allowed else "REVIEW_REQUIRED"),
                "reasons": sorted(set(item_reasons)),
            }
        )
    if not safety_allowed:
        reasons.append("safety_submit_blocked")
    checks["safety_apply_scope"] = "PASS" if safety_allowed else "REVIEW_REQUIRED"
    apply_reasons = sorted(set(reasons))
    non_safety = [reason for reason in apply_reasons if reason != "safety_submit_blocked"]
    return {
        "validation_checks": checks,
        "item_checks": item_checks,
        "apply_block_reasons": apply_reasons,
        "apply_preconditions_status": "PASS" if not non_safety else "REVIEW_REQUIRED",
        "toctou_revalidation_status": "PASS" if not non_safety else "REVIEW_REQUIRED",
        "pending_slot_status": pending_state or "UNKNOWN",
        "safety_submit_allowed": safety_allowed,
        "broker_quantity_validation_scope": "SKIPPED_DUE_SAFETY_APPLY_BLOCK" if not safety_allowed else "EVALUATED",
        "order_condition_status": "REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY",
        "order_condition_reason": "Promotion Candidate and Human Approval do not authorize order_type or price_condition.",
    }


def _build_authoritative_pending_candidate(
    *,
    apply_candidate_id: str,
    promotion_candidate: dict[str, Any],
    approval: dict[str, Any],
    business_date: str,
    mode: str,
    generated_at: str,
    apply_status: str,
    safety: Any,
    validation: dict[str, Any],
) -> dict[str, Any]:
    items = []
    for item in promotion_candidate.get("selected_items") or []:
        review_item_id = str(item.get("review_item_id") or "")
        issue_code = str(item.get("issue_code") or "")
        items.append(
            {
                "pending_item_id": "pending-item-" + _short_hash(
                    {
                        "review_item_id": review_item_id,
                        "approval_id": approval.get("approval_id"),
                        "target_pending_plan_id": promotion_candidate.get("target_pending_plan_id"),
                    }
                ),
                "issue_code": issue_code,
                "broker_issue_code": issue_code,
                "side": str(item.get("side") or "SELL"),
                "quantity": float(item.get("runtime_sell_quantity") or 0),
                "order_type": "REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY",
                "price_condition": "REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY",
                "target_session": str(promotion_candidate.get("target_session") or business_date),
                "source_review_item_id": review_item_id,
                "source_human_review_id": str(item.get("source_human_review_id") or ""),
                "source_safety_event_id": str(item.get("source_safety_event_id") or ""),
                "source_pm_decision_id": str(item.get("source_pm_decision_id") or ""),
                "approval_id": str(approval.get("approval_id") or ""),
                "review_item_hash": str(item.get("review_item_hash") or ""),
                "policy_hash": str(promotion_candidate.get("policy_hash") or ""),
            }
        )
    return {
        "schema_version": AUTHORITATIVE_PENDING_CANDIDATE_SCHEMA_VERSION,
        "candidate_only": True,
        "pending_plan_id": str(promotion_candidate.get("target_pending_plan_id") or ""),
        "target_state_if_applied": "APPROVED",
        "environment": mode,
        "created_at": generated_at,
        "updated_at": generated_at,
        "plan_created_date": business_date,
        "intended_submit_date": business_date,
        "target_session_date": str(promotion_candidate.get("target_session") or business_date),
        "source_order_plan": {
            "order_plan_id": str(promotion_candidate.get("candidate_id") or ""),
            "path": str(promotion_candidate.get("source_review_pending_path") or ""),
            "artifact_hash": str(promotion_candidate.get("source_review_pending_hash") or ""),
        },
        "approval": {
            "approval_id": str(approval.get("approval_id") or ""),
            "approval_hash": _hash_json(approval),
            "approval_status": str(approval.get("approval_status") or ""),
            "approved_item_ids": list(approval.get("approved_item_ids") or []),
            "approval_expires_at": str(approval.get("expires_at") or ""),
            "automatic_trade_authorized": False,
            "broker_write_authorized": False,
        },
        "approved_item_ids": [item["source_review_item_id"] for item in items],
        "items": items,
        "constraints": {
            "expires_at": str(promotion_candidate.get("expires_at") or approval.get("expires_at") or ""),
            "allow_post_send_unknown_resubmit": False,
            "requires_order_condition_resolution": True,
            "order_condition_status": validation["order_condition_status"],
        },
        "safety_decision_id": safety.safety_decision_id,
        "safety_decision": safety.decision,
        "apply_status": apply_status,
        "apply_candidate_id": apply_candidate_id,
    }


def _apply_contract() -> dict[str, str]:
    return {
        "producer": "authoritative_pending_apply_review",
        "input_artifact": "Submit Pending Promotion Candidate plus Human Approval",
        "output_artifact": "Authoritative Pending Apply Candidate",
        "authority": "Human Approval authorizes pending promotion only; Safety must allow Submit before real Apply.",
        "apply_request": "false in BL evidence; future real Apply requires explicit operator request.",
        "apply_execution": "false in BL evidence; no authoritative Pending mutation.",
        "consumer": "future Submit Scope reads only authoritative Pending, not this candidate.",
    }


def _atomicity_contract() -> dict[str, Any]:
    return {
        "status": "READY",
        "rules": [
            "future real Apply writes all approved items atomically",
            "original Pending slot is preserved on partial failure",
            "success history is written only after complete Pending slot publish",
            "current pointer update occurs only after complete publish",
            "backup and apply manifest are required before publish",
        ],
    }


def _idempotency_contract() -> dict[str, Any]:
    return {
        "status": "READY",
        "rules": [
            "same apply candidate rerun cannot duplicate Pending",
            "applied candidate cannot be reused",
            "same approval cannot be consumed twice",
            "different candidate cannot reuse the same pending_plan_id",
            "retry after failed no-mutation attempt is allowed after revalidation",
        ],
    }


def _backup_history_contract() -> dict[str, Any]:
    return {
        "status": "READY",
        "required_artifacts": [
            "before_pending_snapshot",
            "after_pending_snapshot",
            "apply_manifest",
            "promotion_candidate_ref",
            "human_approval_ref",
            "terminal_or_failure_history",
        ],
    }


def _latest_promotion_candidate_path(*, root: Path, business_date: str) -> Path | None:
    directory = root / "runtime_state" / "pending_promotion_candidate" / business_date
    paths = sorted(directory.glob("promotion-candidate-*.json"))
    return paths[-1] if paths else None


def _current_quantities(current: dict[str, Any]) -> dict[str, float]:
    quantities: dict[str, float] = {}
    for item in current.get("positions") or []:
        if isinstance(item, dict):
            symbol = str(item.get("symbol") or item.get("issue_code") or "")
            quantities[symbol] = quantities.get(symbol, 0.0) + float(item.get("quantity") or 0)
    return quantities


def _broker_available_quantities(snapshot: dict[str, Any]) -> dict[str, float]:
    quantities: dict[str, float] = {}
    for item in snapshot.get("positions") or []:
        if isinstance(item, dict):
            issue = str(item.get("issue_code") or item.get("symbol") or "")
            value = item.get("available_quantity", item.get("quantity", 0))
            quantities[issue] = quantities.get(issue, 0.0) + float(value or 0)
    return quantities


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
