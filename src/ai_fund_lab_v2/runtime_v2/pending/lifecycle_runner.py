"""Regular Runtime path for Pending lifecycle review and stale handling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.pending.lifecycle import PENDING_STATE_CONTRACT


PENDING_LIFECYCLE_SCHEMA_VERSION = "runtime_v2_pending_lifecycle_v1"
PENDING_SLOT_SCHEMA_VERSION = "runtime_v2_pending_slot_v1"
TERMINAL_STATES = {"CONSUMED", "EXPIRED", "CANCELLED", "REJECTED", "SUPERSEDED", "EMPTY"}
SUBMIT_BLOCKED_STATES = TERMINAL_STATES | {"REVIEW_REQUIRED"}


@dataclass(frozen=True)
class PendingLifecycleResult:
    status: str
    reason: str
    manifest_fields: dict[str, Any]

    def to_stage_details(self) -> dict[str, Any]:
        return dict(self.manifest_fields)


def run_pending_lifecycle_review(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    action: str = "review",
    now: datetime | None = None,
) -> PendingLifecycleResult:
    if action not in {"review", "expire", "cancel"}:
        raise ValueError("pending action must be review, expire, or cancel")
    root = Path(runtime_root)
    pending_path = root / "pending_order_plan" / "pending_order_plan.json"
    transitioned_at = _iso(now or datetime.now(timezone.utc))
    payload, read_status, read_reason = _read_json(pending_path)
    if read_status != "READY":
        return _result(
            status="REVIEW_REQUIRED",
            reason=read_reason,
            pending_path=pending_path,
            transitioned_at=transitioned_at,
            extra={"next_operator_action": "inspect pending slot evidence"},
        )
    state = _state(payload)
    if state == "EMPTY" or not bool(payload.get("active_pending", True)):
        return _result(
            status="NOOP",
            reason="pending_slot_empty",
            pending_path=pending_path,
            transitioned_at=transitioned_at,
            extra={
                "previous_state": "EMPTY",
                "new_state": "EMPTY",
                "idempotent_noop": True,
                "current_pending_path": str(pending_path),
                "next_operator_action": "pending slot already empty",
            },
        )
    pending_plan_id = str(payload.get("pending_plan_id") or "")
    if state in TERMINAL_STATES:
        history_path = _history_path(root, payload)
        return _result(
            status="NOOP",
            reason="pending_already_terminal",
            pending_path=pending_path,
            transitioned_at=transitioned_at,
            extra={
                "pending_plan_id": pending_plan_id,
                "previous_state": state,
                "new_state": state,
                "target_session_date": str(payload.get("target_session_date") or ""),
                "history_path": str(history_path) if history_path.is_file() else "",
                "idempotent_noop": True,
                "current_pending_path": str(pending_path),
                "next_operator_action": "pending already terminal",
            },
        )
    if state != "APPROVED":
        return _transition_to_review_required(
            root=root,
            pending_path=pending_path,
            payload=payload,
            reason=f"pending_state_{state.lower()}_requires_operator_review",
            transitioned_at=transitioned_at,
            submit_evidence=_submit_attempt_evidence(root=root, pending_plan_id=pending_plan_id),
        )
    submit_evidence = _submit_attempt_evidence(root=root, pending_plan_id=pending_plan_id)
    stale = _stale_reasons(payload=payload, business_date=business_date, transitioned_at=transitioned_at)
    if action == "cancel":
        return _transition_terminal(
            root=root,
            pending_path=pending_path,
            payload=payload,
            new_state="CANCELLED",
            reason="operator_cancelled_pending_regular_path",
            transitioned_at=transitioned_at,
            submit_evidence=submit_evidence,
            empty_slot=True,
        )
    if submit_evidence["unknown_submit_risk"]:
        return _transition_to_review_required(
            root=root,
            pending_path=pending_path,
            payload=payload,
            reason="possible_unknown_submit_outcome",
            transitioned_at=transitioned_at,
            submit_evidence=submit_evidence,
        )
    if stale:
        return _transition_terminal(
            root=root,
            pending_path=pending_path,
            payload=payload,
            new_state="EXPIRED",
            reason=";".join(stale),
            transitioned_at=transitioned_at,
            submit_evidence=submit_evidence,
            empty_slot=True,
        )
    return _result(
        status="NOOP",
        reason="active_pending_not_stale",
        pending_path=pending_path,
        transitioned_at=transitioned_at,
        extra={
            "pending_plan_id": pending_plan_id,
            "previous_state": state,
            "new_state": state,
            "target_session_date": str(payload.get("target_session_date") or ""),
            "approval_expires_at": _approval_expires_at(payload),
            "consumed": _consumed(payload),
            "submit_attempt_detected": submit_evidence["submit_attempt_detected"],
            "unknown_submit_risk": submit_evidence["unknown_submit_risk"],
            "submit_evidence_paths": submit_evidence["submit_manifest_paths"],
            "current_pending_path": str(pending_path),
            "idempotent_noop": True,
            "next_operator_action": "pending remains active; do not overwrite",
        },
    )


def _transition_terminal(
    *,
    root: Path,
    pending_path: Path,
    payload: dict[str, Any],
    new_state: str,
    reason: str,
    transitioned_at: str,
    submit_evidence: dict[str, Any],
    empty_slot: bool,
) -> PendingLifecycleResult:
    history_path = _write_history(
        root=root,
        pending_path=pending_path,
        payload=payload,
        new_state=new_state,
        reason=reason,
        transitioned_at=transitioned_at,
        submit_evidence=submit_evidence,
    )
    if empty_slot:
        _write_json(
            pending_path,
            _empty_slot_payload(
                payload=payload,
                new_state=new_state,
                transitioned_at=transitioned_at,
                history_path=history_path,
            ),
        )
    return _result(
        status=new_state,
        reason=reason,
        pending_path=pending_path,
        transitioned_at=transitioned_at,
        extra=_manifest_transition_fields(
            payload=payload,
            new_state=new_state,
            reason=reason,
            history_path=history_path,
            pending_path=pending_path,
            submit_evidence=submit_evidence,
            idempotent_noop=False,
        ),
    )


def _transition_to_review_required(
    *,
    root: Path,
    pending_path: Path,
    payload: dict[str, Any],
    reason: str,
    transitioned_at: str,
    submit_evidence: dict[str, Any],
) -> PendingLifecycleResult:
    history_path = _write_history(
        root=root,
        pending_path=pending_path,
        payload=payload,
        new_state="REVIEW_REQUIRED",
        reason=reason,
        transitioned_at=transitioned_at,
        submit_evidence=submit_evidence,
    )
    updated = dict(payload)
    updated["state"] = "REVIEW_REQUIRED"
    updated["status"] = "REVIEW_REQUIRED"
    updated["updated_at"] = transitioned_at
    updated["review_required"] = True
    updated["review_reason"] = reason
    updated["pending_lifecycle_history_path"] = str(history_path)
    _write_json(pending_path, updated)
    return _result(
        status="REVIEW_REQUIRED",
        reason=reason,
        pending_path=pending_path,
        transitioned_at=transitioned_at,
        extra=_manifest_transition_fields(
            payload=payload,
            new_state="REVIEW_REQUIRED",
            reason=reason,
            history_path=history_path,
            pending_path=pending_path,
            submit_evidence=submit_evidence,
            idempotent_noop=False,
        ),
    )


def _write_history(
    *,
    root: Path,
    pending_path: Path,
    payload: dict[str, Any],
    new_state: str,
    reason: str,
    transitioned_at: str,
    submit_evidence: dict[str, Any],
) -> Path:
    history_path = _history_path(root, payload)
    if history_path.exists():
        return history_path
    history = {
        "schema_version": PENDING_LIFECYCLE_SCHEMA_VERSION,
        "pending_plan_id": str(payload.get("pending_plan_id") or ""),
        "previous_state": _state(payload),
        "new_state": new_state,
        "transition_reason": reason,
        "transitioned_at": transitioned_at,
        "transitioned_by": "runtime_v2_pending_lifecycle",
        "source_pending_path": str(pending_path),
        "target_session_date": str(payload.get("target_session_date") or ""),
        "approval_status": str((payload.get("approval") or {}).get("approval_status") or ""),
        "approval_at": str((payload.get("approval") or {}).get("approved_at") or payload.get("approval_at") or ""),
        "approval_expires_at": _approval_expires_at(payload),
        "consumed": _consumed(payload),
        "policy_version": str(payload.get("policy_version") or (payload.get("approval") or {}).get("policy_version") or ""),
        "policy_hash": str(payload.get("pending_policy_hash") or (payload.get("approval") or {}).get("pending_policy_hash") or ""),
        "safety_decision_id": str(payload.get("safety_decision_id") or (payload.get("approval") or {}).get("safety_decision_id") or ""),
        "submit_attempt_detected": submit_evidence["submit_attempt_detected"],
        "unknown_submit_risk": submit_evidence["unknown_submit_risk"],
        "submit_manifest_paths": submit_evidence["submit_manifest_paths"],
        "pending_payload": payload,
    }
    _write_json(history_path, history)
    return history_path


def _empty_slot_payload(*, payload: dict[str, Any], new_state: str, transitioned_at: str, history_path: Path) -> dict[str, Any]:
    return {
        "schema_version": PENDING_SLOT_SCHEMA_VERSION,
        "status": "EMPTY",
        "state": "EMPTY",
        "active_pending": False,
        "last_pending_plan_id": str(payload.get("pending_plan_id") or ""),
        "last_terminal_state": new_state,
        "last_transition_at": transitioned_at,
        "history_path": str(history_path),
    }


def _manifest_transition_fields(
    *,
    payload: dict[str, Any],
    new_state: str,
    reason: str,
    history_path: Path,
    pending_path: Path,
    submit_evidence: dict[str, Any],
    idempotent_noop: bool,
) -> dict[str, Any]:
    return {
        "pending_plan_id": str(payload.get("pending_plan_id") or ""),
        "previous_state": _state(payload),
        "new_state": new_state,
        "transition_reason": reason,
        "target_session_date": str(payload.get("target_session_date") or ""),
        "approval_expires_at": _approval_expires_at(payload),
        "consumed": _consumed(payload),
        "submit_attempt_detected": submit_evidence["submit_attempt_detected"],
        "unknown_submit_risk": submit_evidence["unknown_submit_risk"],
        "submit_evidence_paths": submit_evidence["submit_manifest_paths"],
        "history_path": str(history_path),
        "current_pending_path": str(pending_path),
        "idempotent_noop": idempotent_noop,
        "next_operator_action": _next_action(new_state, submit_evidence["unknown_submit_risk"]),
    }


def _submit_attempt_evidence(*, root: Path, pending_plan_id: str) -> dict[str, Any]:
    manifest_root = root / "runtime_state" / "run_manifest"
    submit_paths: list[str] = []
    attempt = False
    unknown = False
    if manifest_root.exists():
        for path in sorted(manifest_root.glob("*/*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("job") != "submit":
                continue
            text = json.dumps(payload, ensure_ascii=False)
            if pending_plan_id and pending_plan_id not in text:
                continue
            submit_paths.append(str(path))
            prohibited = payload.get("prohibited_actions") or {}
            stages = payload.get("stages") or []
            submitted_count = int(payload.get("submitted_count") or payload.get("submit_submitted_count") or 0)
            stage_text = json.dumps(stages, ensure_ascii=False)
            request_attempted = "request_attempted" in stage_text or "broker_request" in stage_text
            attempt = attempt or submitted_count > 0 or bool(prohibited.get("demo_submit_executed")) or request_attempted
            unknown = unknown or "POST_SEND_UNKNOWN" in text or "unknown" in str(payload.get("final_state") or "").lower()
    return {
        "submit_attempt_detected": attempt,
        "unknown_submit_risk": attempt or unknown,
        "submit_manifest_paths": submit_paths,
    }


def _stale_reasons(*, payload: dict[str, Any], business_date: str, transitioned_at: str) -> list[str]:
    reasons: list[str] = []
    if str(payload.get("target_session_date") or "") < business_date:
        reasons.append("target_session_date_elapsed")
    approval_expires_at = _approval_expires_at(payload)
    if approval_expires_at and approval_expires_at <= transitioned_at:
        reasons.append("approval_expired")
    if _consumed(payload):
        return []
    if not str(payload.get("pending_policy_hash") or (payload.get("approval") or {}).get("pending_policy_hash") or ""):
        reasons.append("policy_hash_missing")
    if not str(payload.get("safety_decision_id") or (payload.get("approval") or {}).get("safety_decision_id") or ""):
        reasons.append("safety_decision_id_missing")
    return reasons


def _history_path(root: Path, payload: dict[str, Any]) -> Path:
    target_date = str(payload.get("target_session_date") or "unknown")
    plan_id = str(payload.get("pending_plan_id") or "unknown-pending")
    return root / "pending_order_plan" / "history" / target_date / f"{plan_id}.json"


def _result(
    *,
    status: str,
    reason: str,
    pending_path: Path,
    transitioned_at: str,
    extra: dict[str, Any] | None = None,
) -> PendingLifecycleResult:
    fields = {
        "pending_lifecycle_status": status,
        "transition_reason": reason,
        "transitioned_at": transitioned_at,
        "current_pending_path": str(pending_path),
        "pending_state_contract": PENDING_STATE_CONTRACT,
    }
    fields.update(extra or {})
    fields.setdefault("pending_plan_id", "")
    fields.setdefault("previous_state", "")
    fields.setdefault("new_state", "")
    fields.setdefault("target_session_date", "")
    fields.setdefault("approval_expires_at", "")
    fields.setdefault("consumed", False)
    fields.setdefault("submit_attempt_detected", False)
    fields.setdefault("unknown_submit_risk", False)
    fields.setdefault("submit_evidence_paths", [])
    fields.setdefault("history_path", "")
    fields.setdefault("idempotent_noop", False)
    fields.setdefault("next_operator_action", _next_action(fields["new_state"], fields["unknown_submit_risk"]))
    return PendingLifecycleResult(status=status, reason=reason, manifest_fields=fields)


def _next_action(new_state: str, unknown_submit_risk: bool) -> str:
    if unknown_submit_risk:
        return "review broker/submit evidence before changing Pending"
    if new_state == "EXPIRED":
        return "run data_readiness again"
    if new_state == "REVIEW_REQUIRED":
        return "operator review required"
    return "no pending lifecycle action required"


def _read_json(path: Path) -> tuple[dict[str, Any], str, str]:
    if not path.is_file():
        return {}, "MISSING", "pending slot missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, "INVALID", f"pending slot invalid json: {exc.msg}"
    if not isinstance(payload, dict):
        return {}, "INVALID", "pending slot must be a JSON object"
    return payload, "READY", ""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(payload: dict[str, Any]) -> str:
    return str(payload.get("state") or payload.get("status") or "").upper()


def _approval_expires_at(payload: dict[str, Any]) -> str:
    approval = payload.get("approval") or {}
    constraints = payload.get("submit_constraints") or {}
    return str(approval.get("approval_expires_at") or constraints.get("expires_at") or payload.get("approval_expires_at") or "")


def _consumed(payload: dict[str, Any]) -> bool:
    consume = payload.get("consume") or {}
    return bool(consume.get("consumed")) or _state(payload) == "CONSUMED"


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
