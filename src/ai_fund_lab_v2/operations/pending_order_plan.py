from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, utc_now_iso, write_json


PENDING_ORDER_PLAN_SCHEMA_VERSION = 1
PENDING_ORDER_PLAN_STATES = frozenset(
    {
        "PENDING_APPROVAL",
        "APPROVED",
        "SUBMITTING",
        "SUBMITTED",
        "CONSUMED",
        "EXPIRED",
        "BLOCKED",
    }
)
UNCONSUMED_PENDING_STATES = frozenset({"PENDING_APPROVAL", "APPROVED", "SUBMITTING"})
TERMINAL_PENDING_STATES = frozenset({"SUBMITTED", "CONSUMED", "EXPIRED"})
PLANNING_CUTOFF_JST = time(15, 30)
JST = ZoneInfo("Asia/Tokyo")
STALE_SUBMITTING_SECONDS = 30 * 60


@dataclass(frozen=True)
class PendingOrderPlanPromotionResult:
    status: str
    promoted: bool
    blocked_reason: str
    pending_order_plan_path: str
    history_path: str
    intended_submit_date: str
    target_session_date: str
    pending_plan_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "promoted": self.promoted,
            "blocked_reason": self.blocked_reason,
            "pending_order_plan_path": self.pending_order_plan_path,
            "history_path": self.history_path,
            "intended_submit_date": self.intended_submit_date,
            "target_session_date": self.target_session_date,
            "pending_plan_id": self.pending_plan_id,
            "submit_source_of_truth": "pending_order_plan",
        }


def current_jst() -> datetime:
    return datetime.now(JST)


def pending_order_plan_path(root: Path | str) -> Path:
    return OperationPaths(Path(root)).dir("pending_order_plan") / "pending_order_plan.json"


def pending_order_plan_history_path(root: Path | str, *, plan_created_date: str, pending_plan_id: str) -> Path:
    safe_id = _safe_filename(pending_plan_id)
    return OperationPaths(Path(root)).root / "pending_order_plan" / "history" / plan_created_date / f"{safe_id}.json"


def pending_order_plan_consumed_path(root: Path | str, *, submit_date: str, pending_plan_id: str) -> Path:
    safe_id = _safe_filename(pending_plan_id)
    return OperationPaths(Path(root)).root / "pending_order_plan" / "consumed" / submit_date / f"{safe_id}.json"


def read_pending_order_plan(root: Path | str) -> dict[str, Any]:
    path = pending_order_plan_path(root)
    if not path.exists():
        return {
            "artifact_type": "pending_order_plan",
            "state": "MISSING",
            "state_missing": True,
            "path": str(path),
        }
    payload = read_json(path)
    payload.setdefault("state_missing", False)
    payload.setdefault("path", str(path))
    return payload


def load_pending_order_plan_for_submit(
    *,
    root: Path | str,
    submit_run_date: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    pending = read_pending_order_plan(root)
    metadata = _pending_submit_metadata(root, pending)
    if pending.get("state_missing") is True:
        return {
            "status": "BLOCK",
            "classification": "BLOCK",
            "block_reasons": ["pending_order_plan_missing"],
            "review_reasons": [],
            "pending": pending,
            "order_plan": {},
            "approval": {},
            "metadata": metadata,
        }
    state = str(pending.get("state") or "")
    if state == "SUBMITTING":
        updated_at = _parse_datetime(str(pending.get("updated_at") or ""))
        current = now_utc or datetime.now(timezone.utc)
        stale = updated_at is None or (current - updated_at).total_seconds() >= STALE_SUBMITTING_SECONDS
        return {
            "status": "REVIEW_REQUIRED",
            "classification": "REVIEW_REQUIRED",
            "block_reasons": [],
            "review_reasons": ["pending_state_submitting_stale" if stale else "pending_state_submitting_in_progress"],
            "pending": pending,
            "order_plan": {},
            "approval": {},
            "metadata": metadata,
        }
    block_reasons: list[str] = []
    if state in TERMINAL_PENDING_STATES:
        block_reasons.append(f"pending_state_terminal:{state.lower()}")
    elif state != "APPROVED":
        block_reasons.append(f"pending_state_not_approved:{state or 'missing'}")
    if str(pending.get("intended_submit_date") or "") != submit_run_date:
        block_reasons.append("intended_submit_date_mismatch")
    if str(pending.get("target_session_date") or "") != submit_run_date:
        block_reasons.append("target_session_date_mismatch")
    constraints = pending.get("submit_constraints") or {}
    if constraints.get("allow_dated_order_plan_fallback") is not False:
        block_reasons.append("dated_order_plan_fallback_not_false")

    source_path = _resolve_artifact_path(root, str((pending.get("source_order_plan") or {}).get("path") or ""))
    approval_path = _resolve_artifact_path(root, str((pending.get("approval") or {}).get("path") or ""))
    order_plan = read_json(source_path) if source_path and source_path.exists() else {}
    approval = read_json(approval_path) if approval_path and approval_path.exists() else {}
    if not source_path or not source_path.exists():
        block_reasons.append("source_order_plan_path_missing")
    elif stable_hash(order_plan) != str((pending.get("source_order_plan") or {}).get("hash") or ""):
        block_reasons.append("source_order_plan_hash_mismatch")
    if not approval_path or not approval_path.exists():
        block_reasons.append("approval_path_missing")
    elif stable_hash(approval) != str((pending.get("approval") or {}).get("hash") or ""):
        block_reasons.append("approval_hash_mismatch")
    if str((pending.get("approval") or {}).get("status") or "") != "APPROVED":
        block_reasons.append("pending_approval_status_not_approved")
    if approval and str(approval.get("status") or "") != "APPROVED":
        block_reasons.append("approval_artifact_status_not_approved")
    pending_item_ids = {str(item.get("item_id") or "") for item in pending.get("items", []) if isinstance(item, dict)}
    pending_approved_ids = {str(item_id) for item_id in (pending.get("approval") or {}).get("approved_item_ids", [])}
    artifact_approved_ids = {str(item_id) for item_id in approval.get("approved_item_ids", [])} if approval else set()
    if not pending_approved_ids.issubset(pending_item_ids):
        block_reasons.append("pending_approved_item_ids_not_in_pending_items")
    if artifact_approved_ids and not artifact_approved_ids.issubset(pending_item_ids):
        block_reasons.append("approval_artifact_approved_item_ids_not_in_pending_items")
    if artifact_approved_ids and pending_approved_ids != artifact_approved_ids:
        block_reasons.append("approved_item_ids_mismatch")
    expires_at = str((pending.get("approval") or {}).get("approval_expires_at") or approval.get("approval_expires_at") or "")
    expiry = _parse_datetime(expires_at)
    if not expires_at:
        block_reasons.append("approval_expires_at_missing")
    elif expiry is None:
        block_reasons.append("approval_expires_at_invalid")
    elif expiry <= (now_utc or datetime.now(timezone.utc)):
        block_reasons.append("approval_expired")
    if approval and approval.get("production_order_allowed") is not False:
        block_reasons.append("production_order_allowed_must_be_false")

    metadata = _pending_submit_metadata(root, pending, source_path=source_path, approval_path=approval_path)
    return {
        "status": "PASS" if not block_reasons else "BLOCK",
        "classification": "PASS" if not block_reasons else "BLOCK",
        "block_reasons": block_reasons,
        "review_reasons": [],
        "pending": pending,
        "order_plan": order_plan if not block_reasons else {},
        "approval": approval if not block_reasons else {},
        "metadata": metadata,
    }


def validate_pending_order_plan(payload: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if payload.get("artifact_type") != "pending_order_plan":
        reasons.append("artifact_type_not_pending_order_plan")
    if int(payload.get("schema_version") or 0) != PENDING_ORDER_PLAN_SCHEMA_VERSION:
        reasons.append("schema_version_mismatch")
    if str(payload.get("state") or "") not in PENDING_ORDER_PLAN_STATES:
        reasons.append("invalid_state")
    for field in ("pending_plan_id", "environment", "plan_created_date", "intended_submit_date", "target_session_date"):
        if not str(payload.get(field) or ""):
            reasons.append(f"{field}_missing")
    source = payload.get("source_order_plan") or {}
    for field in ("path", "hash", "status"):
        if not str(source.get(field) or ""):
            reasons.append(f"source_order_plan_{field}_missing")
    approval = payload.get("approval") or {}
    if "required" not in approval:
        reasons.append("approval_required_missing")
    if "status" not in approval:
        reasons.append("approval_status_missing")
    constraints = payload.get("submit_constraints") or {}
    if constraints.get("allow_dated_order_plan_fallback") is not False:
        reasons.append("allow_dated_order_plan_fallback_must_be_false")
    if not isinstance(payload.get("items"), list):
        reasons.append("items_not_list")
    if _contains_forbidden_saved_value(payload):
        reasons.append("forbidden_secret_or_raw_saved")
    return {"status": "PASS" if not reasons else "BLOCK", "reasons": reasons}


def write_pending_order_plan(root: Path | str, payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_pending_order_plan(payload)
    if validation["status"] != "PASS":
        raise ValueError("invalid pending_order_plan: " + ",".join(validation["reasons"]))
    current_path = pending_order_plan_path(root)
    history_path = pending_order_plan_history_path(
        root,
        plan_created_date=str(payload["plan_created_date"]),
        pending_plan_id=str(payload["pending_plan_id"]),
    )
    write_json(current_path, payload)
    write_json(history_path, payload)
    return {"pending_order_plan_path": str(current_path), "history_path": str(history_path), "validation": validation}


def link_approval_to_pending_order_plan(
    *,
    root: Path | str,
    order_plan: dict[str, Any],
    order_plan_path: Path,
    approval: dict[str, Any],
    approval_path: Path,
) -> dict[str, Any]:
    pending = read_pending_order_plan(root)
    if pending.get("state_missing") is True:
        return {
            "status": "SKIPPED_PENDING_MISSING",
            "linked": False,
            "pending_order_plan_path": str(pending_order_plan_path(root)),
            "reasons": ["pending_order_plan_missing"],
        }
    reasons = _approval_linkage_reasons(
        root=root,
        pending=pending,
        order_plan=order_plan,
        order_plan_path=order_plan_path,
        approval=approval,
    )
    approval_status = str(approval.get("status") or "")
    approval_hash = stable_hash(approval)
    source_hash = stable_hash(order_plan)
    pending.setdefault("approval", {})
    pending["approval"].update(
        {
            "status": approval_status,
            "approval_id": str(approval.get("approval_id") or ""),
            "path": _relative_artifact_path(root, approval_path),
            "hash": approval_hash,
            "approved_item_ids": list(approval.get("approved_item_ids") or []),
            "approval_expires_at": str(approval.get("approval_expires_at") or ""),
            "approval_max_notional": str(approval.get("approval_max_notional") or approval.get("max_notional") or ""),
            "approval_max_notional_source": str(approval.get("approval_max_notional_source") or ""),
            "source_order_plan_hash": source_hash,
            "linkage_status": "PASS" if not reasons else "BLOCK",
            "linkage_reasons": reasons,
        }
    )
    pending["updated_at"] = utc_now_iso()
    if not reasons and approval_status == "APPROVED":
        pending["state"] = "APPROVED"
        pending["promotion"]["blocked_reason"] = ""
        pending["approval"]["review_reason"] = ""
    elif approval_status in {"BLOCK", "BLOCKED", "REVIEW_REQUIRED"} or reasons:
        pending["state"] = "BLOCKED"
        pending["promotion"]["blocked_reason"] = ",".join(reasons or [f"approval_status_{approval_status.lower()}"])
        pending["approval"]["review_reason"] = ",".join(reasons or [f"approval_status_{approval_status.lower()}"])
    else:
        pending["state"] = "PENDING_APPROVAL"
        pending["approval"]["review_reason"] = f"approval_status_{approval_status.lower() or 'missing'}"
    write_result = write_pending_order_plan(root, pending)
    return {
        "status": "LINKED" if pending["state"] == "APPROVED" else "REVIEW_REQUIRED",
        "linked": pending["state"] == "APPROVED",
        "pending_state": pending["state"],
        "pending_order_plan_path": write_result["pending_order_plan_path"],
        "history_path": write_result["history_path"],
        "reasons": reasons,
        "approval_hash": approval_hash,
        "source_order_plan_hash": source_hash,
    }


def promote_order_plan_to_pending_if_allowed(
    *,
    root: Path | str,
    order_plan: dict[str, Any],
    order_plan_path: Path,
    market_calendar: dict[str, Any],
    promotion_source: str,
    now_jst: datetime | None = None,
) -> dict[str, Any]:
    paths = OperationPaths(Path(root))
    plan_created_date = str(order_plan.get("business_date") or market_calendar.get("trade_date") or "")
    intended_submit_date = str(market_calendar.get("next_business_day") or "")
    target_session_date = intended_submit_date
    plan_id = str(order_plan.get("plan_id") or "")
    pending_plan_id = f"pending_{plan_created_date}_{plan_id}" if plan_id else ""
    blocked_reason = _pending_promotion_blocked_reason(
        root=paths.root,
        plan_created_date=plan_created_date,
        intended_submit_date=intended_submit_date,
        target_session_date=target_session_date,
        now_jst=now_jst or current_jst(),
    )
    if blocked_reason:
        return PendingOrderPlanPromotionResult(
            status="SKIPPED",
            promoted=False,
            blocked_reason=blocked_reason,
            pending_order_plan_path=str(pending_order_plan_path(paths.root)),
            history_path="",
            intended_submit_date=intended_submit_date,
            target_session_date=target_session_date,
            pending_plan_id=pending_plan_id,
        ).to_dict()
    payload = build_pending_order_plan(
        root=paths.root,
        order_plan=order_plan,
        order_plan_path=order_plan_path,
        plan_created_date=plan_created_date,
        intended_submit_date=intended_submit_date,
        target_session_date=target_session_date,
        promotion_source=promotion_source,
    )
    write_result = write_pending_order_plan(paths.root, payload)
    return PendingOrderPlanPromotionResult(
        status="PROMOTED",
        promoted=True,
        blocked_reason="",
        pending_order_plan_path=write_result["pending_order_plan_path"],
        history_path=write_result["history_path"],
        intended_submit_date=intended_submit_date,
        target_session_date=target_session_date,
        pending_plan_id=str(payload["pending_plan_id"]),
    ).to_dict()


def build_pending_order_plan(
    *,
    root: Path | str,
    order_plan: dict[str, Any],
    order_plan_path: Path,
    plan_created_date: str,
    intended_submit_date: str,
    target_session_date: str,
    promotion_source: str,
) -> dict[str, Any]:
    now = utc_now_iso()
    plan_id = str(order_plan.get("plan_id") or "")
    pending_plan_id = f"pending_{plan_created_date}_{plan_id}"
    source_hash = stable_hash(order_plan)
    rel_order_plan_path = _relative_artifact_path(root, order_plan_path)
    return {
        "artifact_type": "pending_order_plan",
        "schema_version": PENDING_ORDER_PLAN_SCHEMA_VERSION,
        "pending_plan_id": pending_plan_id,
        "state": "PENDING_APPROVAL",
        "environment": str(order_plan.get("environment") or ""),
        "created_at": now,
        "updated_at": now,
        "plan_created_date": plan_created_date,
        "intended_submit_date": intended_submit_date,
        "target_session_date": target_session_date,
        "source_order_plan": {
            "plan_id": plan_id,
            "path": rel_order_plan_path,
            "hash": source_hash,
            "status": str(order_plan.get("status") or ""),
            "buy_item_count": int(order_plan.get("buy_item_count") or 0),
            "sell_item_count": int(order_plan.get("sell_item_count") or 0),
        },
        "approval": {
            "required": bool(order_plan.get("requires_approval", True)),
            "status": "PENDING",
            "path": "",
            "hash": "",
            "approval_id": "",
            "approved_item_ids": [],
            "approval_expires_at": "",
            "approval_max_notional": "",
            "approval_max_notional_source": "",
        },
        "items": list(order_plan.get("items") or []),
        "submit_constraints": {
            "submit_source": "pending_order_plan_only",
            "allow_dated_order_plan_fallback": False,
            "production_order_allowed": False,
            "requires_unconsumed_state": True,
            "requires_intended_submit_date_match": True,
        },
        "promotion": {
            "source": promotion_source,
            "promoted": True,
            "promotion_policy": "after_close_next_business_session_only",
            "blocked_reason": "",
        },
        "consume": {
            "consumed_at": "",
            "submit_run_date": "",
            "submitted_orders_path": "",
            "submitted_order_count": 0,
            "accepted_order_count": 0,
            "status": "",
        },
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _pending_promotion_blocked_reason(
    *,
    root: Path,
    plan_created_date: str,
    intended_submit_date: str,
    target_session_date: str,
    now_jst: datetime,
) -> str:
    if not plan_created_date:
        return "plan_created_date_missing"
    if not intended_submit_date:
        return "intended_submit_date_missing"
    if target_session_date != intended_submit_date:
        return "target_session_date_mismatch"
    if now_jst.date().isoformat() != plan_created_date:
        return "not_plan_created_date_runtime"
    if now_jst.timetz().replace(tzinfo=None) < PLANNING_CUTOFF_JST:
        return "before_market_close_planning_cutoff"
    existing = read_pending_order_plan(root)
    if existing.get("state") in UNCONSUMED_PENDING_STATES:
        existing_target = str(existing.get("target_session_date") or "")
        if not existing_target or existing_target <= target_session_date:
            return "unconsumed_pending_order_plan_conflict"
    return ""


def _approval_linkage_reasons(
    *,
    root: Path | str,
    pending: dict[str, Any],
    order_plan: dict[str, Any],
    order_plan_path: Path,
    approval: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    source = pending.get("source_order_plan") or {}
    expected_order_path = str(source.get("path") or "")
    actual_order_path = _relative_artifact_path(root, order_plan_path)
    if expected_order_path != actual_order_path:
        reasons.append("source_order_plan_path_mismatch")
    if str(source.get("hash") or "") != stable_hash(order_plan):
        reasons.append("source_order_plan_hash_mismatch")
    if str(approval.get("plan_id") or "") != str(source.get("plan_id") or ""):
        reasons.append("approval_plan_id_mismatch")
    pending_item_ids = {str(item.get("item_id") or "") for item in pending.get("items", []) if isinstance(item, dict)}
    approved_item_ids = {str(item_id) for item_id in approval.get("approved_item_ids", [])}
    if not approved_item_ids.issubset(pending_item_ids):
        reasons.append("approved_item_ids_not_in_pending_items")
    if approval.get("production_order_allowed") is not False:
        reasons.append("production_order_allowed_must_be_false")
    if str(approval.get("status") or "") == "APPROVED" and not str(approval.get("approval_expires_at") or ""):
        reasons.append("approval_expires_at_missing")
    return reasons


def _contains_forbidden_saved_value(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"raw_request_saved", "raw_response_saved", "secret_saved"} and item is not False:
                return True
            if key in {"raw_request", "raw_response", "secret", "password", "token", "session"}:
                return True
            if _contains_forbidden_saved_value(item):
                return True
    if isinstance(value, list):
        return any(_contains_forbidden_saved_value(item) for item in value)
    return False


def _pending_submit_metadata(
    root: Path | str,
    pending: dict[str, Any],
    *,
    source_path: Path | None = None,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    source = pending.get("source_order_plan") or {}
    approval = pending.get("approval") or {}
    return {
        "pending_plan_id": str(pending.get("pending_plan_id") or ""),
        "pending_plan_path": str(pending_order_plan_path(root)),
        "plan_created_date": str(pending.get("plan_created_date") or ""),
        "intended_submit_date": str(pending.get("intended_submit_date") or ""),
        "target_session_date": str(pending.get("target_session_date") or ""),
        "source_order_plan": {
            "path": str(source.get("path") or ""),
            "hash": str(source.get("hash") or ""),
            "resolved_path": str(source_path or ""),
        },
        "approval": {
            "path": str(approval.get("path") or ""),
            "hash": str(approval.get("hash") or ""),
            "resolved_path": str(approval_path or ""),
        },
        "submit_source": "pending_order_plan",
        "dated_order_plan_fallback_used": False,
    }


def _resolve_artifact_path(root: Path | str, value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(root) / path


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _relative_artifact_path(root: Path | str, path: Path) -> str:
    root_path = Path(root)
    try:
        return str(path.relative_to(root_path))
    except ValueError:
        return str(path)


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)[:180]
