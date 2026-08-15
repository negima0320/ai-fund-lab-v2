"""Regular Runtime path for Pending lifecycle review and stale handling."""

from __future__ import annotations

import hashlib
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
    submit_evidence = _submit_attempt_evidence(root=root, pending_plan_id=pending_plan_id)
    mixed_terminal = _historical_mixed_item_terminalization_authority(
        root=root,
        business_date=business_date,
        mode=mode,
        payload=payload,
    )
    if mixed_terminal["status"] == "PASS":
        return _transition_terminal(
            root=root,
            pending_path=pending_path,
            payload=payload,
            new_state="CONSUMED",
            reason="historical_mixed_filled_and_ca_quarantined_items_terminal",
            transitioned_at=transitioned_at,
            submit_evidence={
                **submit_evidence,
                "unknown_submit_risk": False,
                "item_lifecycle_authority": mixed_terminal,
            },
            empty_slot=True,
        )
    buy_review_terminal = _buy_item_scoped_review_no_submission_terminalization_authority(
        root=root,
        business_date=business_date,
        payload=payload,
        submit_evidence=submit_evidence,
    )
    if buy_review_terminal["status"] == "PASS":
        return _transition_terminal(
            root=root,
            pending_path=pending_path,
            payload=payload,
            new_state="EXPIRED",
            reason="buy_item_scoped_review_no_submission_terminal",
            transitioned_at=transitioned_at,
            submit_evidence={
                **submit_evidence,
                "unknown_submit_risk": False,
                "buy_item_scoped_review_no_submission_terminalization": buy_review_terminal,
            },
            empty_slot=True,
        )
    if buy_review_terminal["status"] == "REVIEW_REQUIRED":
        return _transition_to_review_required(
            root=root,
            pending_path=pending_path,
            payload=payload,
            reason=buy_review_terminal["reason"],
            transitioned_at=transitioned_at,
            submit_evidence={
                **submit_evidence,
                "buy_item_scoped_review_no_submission_terminalization": buy_review_terminal,
            },
        )
    if state != "APPROVED":
        return _transition_to_review_required(
            root=root,
            pending_path=pending_path,
            payload=payload,
            reason=f"pending_state_{state.lower()}_requires_operator_review",
            transitioned_at=transitioned_at,
            submit_evidence=submit_evidence,
        )
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
    quarantine_terminal = _historical_ca_quarantine_terminalization_authority(
        root=root,
        business_date=business_date,
        mode=mode,
        payload=payload,
        submit_evidence=submit_evidence,
    )
    if quarantine_terminal["status"] == "PASS":
        return _transition_terminal(
            root=root,
            pending_path=pending_path,
            payload=payload,
            new_state="EXPIRED",
            reason="historical_corporate_action_quarantine_not_submitted_non_retryable",
            transitioned_at=transitioned_at,
            submit_evidence={
                **submit_evidence,
                "corporate_action_quarantine_terminalization": quarantine_terminal,
            },
            empty_slot=True,
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
        existing = _read_json_dict(history_path)
        if (
            str(existing.get("new_state") or "") == new_state
            and str(existing.get("transition_reason") or "") == reason
        ):
            return history_path
        history_path = _conflict_history_path(history_path=history_path, new_state=new_state, reason=reason)
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
        "corporate_action_quarantine_terminalization": submit_evidence.get(
            "corporate_action_quarantine_terminalization",
            {"status": "NOT_APPLICABLE"},
        ),
        "item_lifecycle_authority": submit_evidence.get("item_lifecycle_authority", {"status": "NOT_APPLICABLE"}),
        "buy_item_scoped_review_no_submission_terminalization": submit_evidence.get(
            "buy_item_scoped_review_no_submission_terminalization",
            {"status": "NOT_APPLICABLE"},
        ),
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
        "item_lifecycle_authority": submit_evidence.get("item_lifecycle_authority", {"status": "NOT_APPLICABLE"}),
        "buy_item_scoped_review_no_submission_terminalization": submit_evidence.get(
            "buy_item_scoped_review_no_submission_terminalization",
            {"status": "NOT_APPLICABLE"},
        ),
        "pending_lifecycle_terminal_status": new_state if new_state in TERMINAL_STATES else "",
        "pending_lifecycle_terminal_reason": reason if new_state in TERMINAL_STATES else "",
        "broker_write_performed": bool(submit_evidence.get("broker_write_performed", False)),
        "fail_open_used": False,
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


def _buy_item_scoped_review_no_submission_terminalization_authority(
    *,
    root: Path,
    business_date: str,
    payload: dict[str, Any],
    submit_evidence: dict[str, Any],
) -> dict[str, Any]:
    base = _buy_item_scoped_review_pending_evidence(payload=payload, business_date=business_date)
    if base["status"] != "PASS":
        return base
    if submit_evidence.get("unknown_submit_risk"):
        return {**base, "status": "REVIEW_REQUIRED", "reason": "unknown_submit_risk"}
    submit = _latest_job_manifest(root=root, business_date=business_date, job="submit")
    if submit is None:
        return {**base, "status": "REVIEW_REQUIRED", "reason": "buy_item_scoped_review_submit_no_submission_authority_missing"}
    submit_path, submit_payload = submit
    submit_details = _manifest_stage_details(submit_payload, "runtime_v2_submit_pipeline")
    submit_checks = _submit_no_submission_checks(
        pending_payload=payload,
        submit_payload=submit_payload,
        submit_details=submit_details,
        business_date=business_date,
    )
    execution = _latest_job_manifest(root=root, business_date=business_date, job="execution")
    if execution is None:
        return {
            **base,
            "status": "REVIEW_REQUIRED",
            "reason": "buy_item_scoped_review_execution_no_action_authority_missing",
            "submit_manifest_path": str(submit_path),
            "submit_checks": submit_checks,
        }
    execution_path, execution_payload = execution
    execution_details = _manifest_stage_details(execution_payload, "runtime_v2_execution_readonly_pipeline")
    execution_checks = _execution_no_action_checks(
        execution_payload=execution_payload,
        execution_details=execution_details,
        business_date=business_date,
        submit_manifest_path=submit_path,
    )
    broker_write_performed = _broker_write_performed(submit_payload) or _broker_write_performed(execution_payload)
    checks = {
        **base["checks"],
        **{f"submit_{key}": value for key, value in submit_checks.items()},
        **{f"execution_{key}": value for key, value in execution_checks.items()},
        "no_broker_write": not broker_write_performed,
    }
    status = "PASS" if all(checks.values()) else "REVIEW_REQUIRED"
    return {
        **base,
        "status": status,
        "reason": (
            "buy_item_scoped_review_no_submission_terminal"
            if status == "PASS"
            else "buy_item_scoped_review_no_submission_terminalization_checks_failed"
        ),
        "checks": checks,
        "submit_manifest_path": str(submit_path),
        "execution_manifest_path": str(execution_path),
        "submit_status": str(submit_payload.get("final_state") or submit_details.get("status") or ""),
        "submit_no_action_reason": str(
            submit_payload.get("no_order_authority_reason")
            or submit_payload.get("no_action_reason")
            or submit_details.get("no_order_authority_reason")
            or submit_details.get("no_action_reason")
            or ""
        ),
        "execution_status": str(execution_details.get("status") or execution_payload.get("final_state") or ""),
        "execution_no_action_reason": str(
            execution_details.get("reason") or execution_payload.get("reason") or execution_details.get("no_action_reason") or ""
        ),
        "pending_lifecycle_terminal_status": "EXPIRED",
        "pending_lifecycle_terminal_reason": "buy_item_scoped_review_no_submission_terminal",
        "broker_write_performed": broker_write_performed,
        "fail_open_used": False,
        "buy_batch_atomicity_preserved": True,
        "partial_buy_submit_allowed": False,
        "reviewed_buy_submitted": False,
    }


def _buy_item_scoped_review_pending_evidence(*, payload: dict[str, Any], business_date: str) -> dict[str, Any]:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    item_ids = [str(item.get("pending_item_id") or "") for item in items if isinstance(item, dict)]
    approved_item_ids = _str_list(payload.get("approved_item_ids"))
    review_buy_ids = _str_list(payload.get("review_required_buy_item_ids"))
    review_sell_ids = _str_list(payload.get("review_required_sell_item_ids"))
    checks = {
        "pending_state_review_required": _state(payload) == "REVIEW_REQUIRED",
        "pending_unconsumed": not _consumed(payload),
        "pending_target_session_same_day": str(payload.get("target_session_date") or "") == business_date,
        "review_scope_buy_item_scoped": str(payload.get("review_scope") or "") == "BUY_ITEM_SCOPED_REVIEW",
        "sell_continuation_allowed": bool(payload.get("sell_continuation_allowed")),
        "approved_item_ids_empty": not approved_item_ids,
        "review_required_buy_item_ids_present": bool(review_buy_ids),
        "review_required_sell_item_ids_empty": not review_sell_ids,
        "items_present": bool(items),
        "all_items_objects": bool(items) and all(isinstance(item, dict) for item in items),
        "all_items_buy": bool(items) and all(str(item.get("side") or "").upper() == "BUY" for item in items if isinstance(item, dict)),
        "no_item_approved": bool(items) and not any(bool(item.get("approved")) for item in items if isinstance(item, dict)),
        "review_buy_ids_known": bool(review_buy_ids) and set(review_buy_ids).issubset(set(item_ids)),
    }
    applicable = (
        _state(payload) == "REVIEW_REQUIRED"
        and str(payload.get("review_scope") or "") == "BUY_ITEM_SCOPED_REVIEW"
    )
    if not applicable:
        return {
            "status": "NOT_APPLICABLE",
            "reason": "pending_not_buy_item_scoped_review",
            "checks": checks,
        }
    if not all(checks.values()):
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "buy_item_scoped_review_pending_shape_invalid",
            "checks": checks,
            "pending_plan_id": str(payload.get("pending_plan_id") or ""),
            "pending_state": _state(payload),
            "review_scope": str(payload.get("review_scope") or ""),
            "approved_item_ids": approved_item_ids,
            "review_required_buy_item_ids": review_buy_ids,
            "review_required_sell_item_ids": review_sell_ids,
            "sell_continuation_allowed": bool(payload.get("sell_continuation_allowed")),
        }
    return {
        "status": "PASS",
        "reason": "buy_item_scoped_review_pending_shape_valid",
        "checks": checks,
        "pending_plan_id": str(payload.get("pending_plan_id") or ""),
        "pending_state": _state(payload),
        "review_scope": str(payload.get("review_scope") or ""),
        "approved_item_ids": approved_item_ids,
        "approved_buy_item_ids": _str_list(payload.get("approved_buy_item_ids")),
        "approved_sell_item_ids": _str_list(payload.get("approved_sell_item_ids")),
        "review_required_buy_item_ids": review_buy_ids,
        "review_required_sell_item_ids": review_sell_ids,
        "sell_continuation_allowed": bool(payload.get("sell_continuation_allowed")),
        "item_ids": item_ids,
    }


def _submit_no_submission_checks(
    *,
    pending_payload: dict[str, Any],
    submit_payload: dict[str, Any],
    submit_details: dict[str, Any],
    business_date: str,
) -> dict[str, bool]:
    evidence = submit_payload.get("no_order_authority_evidence")
    if not isinstance(evidence, dict):
        evidence = submit_details.get("no_order_authority_evidence") if isinstance(submit_details.get("no_order_authority_evidence"), dict) else {}
    pending_plan_id = str(pending_payload.get("pending_plan_id") or "")
    evidence_plan_id = str(evidence.get("pending_plan_id") or "")
    return {
        "job": str(submit_payload.get("job") or "") == "submit",
        "same_business_date": str(submit_payload.get("business_date") or "") == business_date,
        "exit_code_zero": _int_value(submit_payload.get("exit_code"), 0) == 0,
        "final_state_loaded": str(submit_payload.get("final_state") or "") == "CURRENT_STATE_LOADED",
        "pending_plan_id_matches": evidence_plan_id == pending_plan_id,
        "pending_valid": str(submit_payload.get("pending_classification") or "") == "VALID",
        "pending_plan_present": bool(submit_payload.get("pending_plan_present")),
        "submit_action_no_submission_required": str(submit_payload.get("submit_action") or "") == "NO_SUBMISSION_REQUIRED",
        "submitted_count_zero": _int_value(submit_payload.get("submitted_count"), -1) == 0,
        "blocked_count_zero": _int_value(submit_payload.get("blocked_count"), -1) == 0,
        "review_required_false": not bool(submit_payload.get("review_required")),
        "halt_required_false": not bool(submit_payload.get("halt_required")),
        "no_order_authority_pass": str(submit_payload.get("no_order_authority_status") or "") == "PASS",
        "authority_type": str(evidence.get("authority_type") or "") == "BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION",
        "evidence_status_pass": str(evidence.get("status") or "") == "PASS",
        "batch_atomicity_preserved": bool(evidence.get("buy_batch_atomicity_preserved")),
        "partial_buy_submit_disallowed": not bool(evidence.get("partial_buy_submit_allowed")),
        "reviewed_buy_not_submitted": not bool(evidence.get("reviewed_buy_submitted")),
        "no_broker_write": not _broker_write_performed(submit_payload),
    }


def _execution_no_action_checks(
    *,
    execution_payload: dict[str, Any],
    execution_details: dict[str, Any],
    business_date: str,
    submit_manifest_path: Path,
) -> dict[str, bool]:
    return {
        "job": str(execution_payload.get("job") or "") == "execution",
        "same_business_date": str(execution_payload.get("business_date") or "") == business_date,
        "exit_code_zero": _int_value(execution_payload.get("exit_code"), 0) == 0,
        "final_state_loaded": str(execution_payload.get("final_state") or "") == "CURRENT_STATE_LOADED",
        "stage_pass": str(execution_details.get("status") or "") == "PASS",
        "execution_action_no_action": str(execution_details.get("execution_action") or "") == "NO_ACTION",
        "submitted_order_count_zero": _int_value(execution_details.get("submitted_order_count"), -1) == 0,
        "fill_count_zero": _int_value(execution_details.get("fill_count"), -1) == 0,
        "pending_lifecycle_required": str(execution_details.get("pending_terminalization_status") or "") == "PENDING_LIFECYCLE_REQUIRED",
        "pending_not_consumed": not bool(execution_details.get("pending_consumed")),
        "pending_not_mutated": not bool(execution_details.get("pending_mutated")),
        "pending_plan_present": bool(execution_details.get("pending_plan_present")),
        "submit_authority_pass": str(execution_details.get("submit_authority_status") or "") == "PASS",
        "submit_action_no_submission_required": str(execution_details.get("submit_action") or "") == "NO_SUBMISSION_REQUIRED",
        "submit_authority_path_matches": Path(str(execution_details.get("submit_authority_path") or "")).name == submit_manifest_path.name,
        "no_broker_write": not _broker_write_performed(execution_payload),
    }


def _latest_job_manifest(*, root: Path, business_date: str, job: str) -> tuple[Path, dict[str, Any]] | None:
    manifest_dir = root / "runtime_state" / "run_manifest" / business_date
    manifests = sorted(manifest_dir.glob(f"runtime-v2-{job}-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in manifests:
        payload = _read_json_dict(path)
        if payload and str(payload.get("job") or "") == job:
            return path, payload
    return None


def _manifest_stage_details(payload: dict[str, Any], stage_name: str) -> dict[str, Any]:
    for stage in payload.get("stages") or []:
        if not isinstance(stage, dict):
            continue
        if str(stage.get("name") or "") == stage_name:
            details = stage.get("details")
            return details if isinstance(details, dict) else {}
    return {}


def _broker_write_performed(payload: dict[str, Any]) -> bool:
    prohibited = payload.get("prohibited_actions") if isinstance(payload.get("prohibited_actions"), dict) else {}
    return (
        bool(payload.get("broker_write"))
        or bool(payload.get("external_delivery"))
        or bool(prohibited.get("demo_submit_executed"))
        or bool(prohibited.get("production_order_executed"))
        or bool(prohibited.get("broker_write"))
        or bool(prohibited.get("external_delivery"))
    )


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _historical_ca_quarantine_terminalization_authority(
    *,
    root: Path,
    business_date: str,
    mode: str,
    payload: dict[str, Any],
    submit_evidence: dict[str, Any],
) -> dict[str, Any]:
    if mode != "historical":
        return {"status": "NOT_APPLICABLE", "reason": "not_historical"}
    if _state(payload) != "APPROVED":
        return {"status": "NOT_APPLICABLE", "reason": "pending_not_approved"}
    if _consumed(payload):
        return {"status": "NOT_APPLICABLE", "reason": "pending_already_consumed"}
    if submit_evidence.get("unknown_submit_risk"):
        return {"status": "REVIEW_REQUIRED", "reason": "unknown_submit_risk"}
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    if not items:
        return {"status": "NOT_APPLICABLE", "reason": "pending_items_missing"}
    if str(payload.get("target_session_date") or "") != business_date:
        return {"status": "NOT_APPLICABLE", "reason": "target_session_date_not_current_business_date"}
    submit = _latest_submit_manifest(root=root, business_date=business_date)
    if submit is None:
        return {"status": "NOT_APPLICABLE", "reason": "submit_manifest_missing"}
    submit_path, submit_payload = submit
    continuation_path = _historical_quarantine_continuation_path(submit_payload, business_date)
    continuation = _read_json_dict(continuation_path)
    checks = _historical_ca_quarantine_terminalization_checks(
        pending_payload=payload,
        submit_payload=submit_payload,
        continuation=continuation,
        business_date=business_date,
        submit_manifest_path=submit_path,
    )
    if not all(checks.values()):
        return {
            "status": "NOT_APPLICABLE",
            "reason": "historical_ca_quarantine_terminalization_checks_failed",
            "checks": checks,
        }
    return {
        "status": "PASS",
        "reason": "historical_corporate_action_quarantine_not_submitted_non_retryable",
        "checks": checks,
        "submit_manifest_path": str(submit_path),
        "continuation_path": str(continuation_path),
        "affected_symbols": list(continuation.get("affected_symbols") or ()),
    }


def _historical_mixed_item_terminalization_authority(
    *,
    root: Path,
    business_date: str,
    mode: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if mode != "historical":
        return {"status": "NOT_APPLICABLE", "reason": "not_historical"}
    if _state(payload) not in {"APPROVED", "REVIEW_REQUIRED"}:
        return {"status": "NOT_APPLICABLE", "reason": "pending_state_not_mixed_terminalizable"}
    if _consumed(payload):
        return {"status": "NOT_APPLICABLE", "reason": "pending_already_consumed"}
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    if not items:
        return {"status": "NOT_APPLICABLE", "reason": "pending_items_missing"}
    if str(payload.get("target_session_date") or "") != business_date:
        return {"status": "NOT_APPLICABLE", "reason": "target_session_date_not_current_business_date"}
    submit = _latest_submit_manifest(root=root, business_date=business_date)
    if submit is None:
        return {"status": "NOT_APPLICABLE", "reason": "submit_manifest_missing"}
    submit_path, submit_payload = submit
    if str(submit_payload.get("final_state") or "") == "POST_SEND_UNKNOWN":
        return {"status": "REVIEW_REQUIRED", "reason": "post_send_unknown"}
    submitted_count = _int_value(submit_payload.get("submitted_count"), 0)
    blocked_count = _int_value(submit_payload.get("blocked_count"), 0)
    if submitted_count <= 0 or blocked_count <= 0:
        return {"status": "NOT_APPLICABLE", "reason": "not_mixed_submitted_and_blocked"}
    continuation_path = _historical_quarantine_continuation_path(submit_payload, business_date)
    continuation = _read_json_dict(continuation_path)
    base_checks = _historical_mixed_item_terminalization_checks(
        submit_payload=submit_payload,
        continuation=continuation,
        business_date=business_date,
        submit_manifest_path=submit_path,
    )
    item_outcomes = _derive_mixed_item_terminal_outcomes(
        root=root,
        pending_items=items,
        submit_payload=submit_payload,
        continuation=continuation,
        business_date=business_date,
    )
    terminal_count = sum(1 for item in item_outcomes if bool(item.get("terminal")))
    broker_uncertain = any(bool(item.get("broker_uncertainty")) for item in item_outcomes)
    checks = {
        **base_checks,
        "all_items_classified": len(item_outcomes) == len(items) > 0,
        "all_items_terminal": terminal_count == len(items) > 0,
        "no_broker_uncertainty": not broker_uncertain,
        "has_filled_item": any(str(item.get("outcome") or "") == "FILLED" for item in item_outcomes),
        "has_quarantined_not_submitted_item": any(
            str(item.get("outcome") or "") == "QUARANTINED_NOT_SUBMITTED" for item in item_outcomes
        ),
        "no_unresolved_review_required_item": not any(
            str(item.get("outcome") or "") == "REVIEW_REQUIRED" for item in item_outcomes
        ),
    }
    if not all(checks.values()):
        return {
            "status": "NOT_APPLICABLE",
            "reason": "historical_mixed_item_terminalization_checks_failed",
            "checks": checks,
            "item_outcomes": item_outcomes,
            "submit_manifest_path": str(submit_path),
            "continuation_path": str(continuation_path),
        }
    return {
        "status": "PASS",
        "reason": "historical_mixed_filled_and_ca_quarantined_items_terminal",
        "checks": checks,
        "item_outcomes": item_outcomes,
        "submit_manifest_path": str(submit_path),
        "continuation_path": str(continuation_path),
        "derived_plan_state": "CONSUMED",
    }


def _historical_mixed_item_terminalization_checks(
    *,
    submit_payload: dict[str, Any],
    continuation: dict[str, Any],
    business_date: str,
    submit_manifest_path: Path,
) -> dict[str, bool]:
    prohibited = submit_payload.get("prohibited_actions") if isinstance(submit_payload.get("prohibited_actions"), dict) else {}
    continuation_checks = continuation.get("checks") if isinstance(continuation.get("checks"), dict) else {}
    text = json.dumps(submit_payload, ensure_ascii=False)
    return {
        "mode_historical": _manifest_indicates_historical(submit_payload),
        "same_business_date": str(submit_payload.get("business_date") or "") == business_date,
        "submit_review_required": str(submit_payload.get("final_state") or "") == "REVIEW_REQUIRED",
        "submitted_count_positive": _int_value(submit_payload.get("submitted_count"), 0) > 0,
        "blocked_count_positive": _int_value(submit_payload.get("blocked_count"), 0) > 0,
        "no_post_send_unknown": "POST_SEND_UNKNOWN" not in text,
        "no_broker_write": (
            not bool(submit_payload.get("broker_write"))
            and not bool(submit_payload.get("external_delivery"))
            and not bool(prohibited.get("demo_submit_executed"))
            and not bool(prohibited.get("production_order_executed"))
            and not bool(prohibited.get("broker_write"))
            and not bool(prohibited.get("external_delivery"))
        ),
        "continuation_artifact_present": bool(continuation),
        "continuation_status": str(continuation.get("status") or "") == "COMPLETED_WITH_SYMBOL_QUARANTINE",
        "continuation_business_date": str(continuation.get("business_date") or "") == business_date,
        "continuation_scope": str(continuation.get("scope") or "") == "CORPORATE_ACTION_SYMBOL_ONLY",
        "production_never": str(continuation.get("production_applicability") or "") == "NEVER",
        "run_continuation_historical_only": (
            str(continuation.get("corporate_action_run_continuation_eligibility") or "")
            == "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY"
        ),
        "classifier_checks_pass": all(bool(value) for value in continuation_checks.values()) if continuation_checks else False,
        "continuation_runtime_manifest_bound": (
            str(continuation.get("runtime_manifest_path") or "") in {"", str(submit_manifest_path)}
            or Path(str(continuation.get("runtime_manifest_path") or "")).name == submit_manifest_path.name
            or str(continuation.get("runtime_manifest_path") or "").endswith(
                f"/daily/{business_date}/submit/runtime_manifest.json"
            )
        ),
    }


def _latest_submit_manifest(*, root: Path, business_date: str) -> tuple[Path, dict[str, Any]] | None:
    manifest_dir = root / "runtime_state" / "run_manifest" / business_date
    manifests = sorted(manifest_dir.glob("runtime-v2-submit-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in manifests:
        payload = _read_json_dict(path)
        if payload and str(payload.get("job") or "") == "submit":
            return path, payload
    return None


def _historical_quarantine_continuation_path(submit_payload: dict[str, Any], business_date: str) -> Path:
    evidence_root = str(submit_payload.get("runtime_test_evidence_root") or "")
    run_id = str(submit_payload.get("runtime_test_run_id") or "")
    if evidence_root and Path(evidence_root).name == run_id:
        run_dir = Path(evidence_root)
    else:
        run_dir = Path(evidence_root) / "runs" / run_id if evidence_root and run_id else Path()
    return run_dir / "daily" / business_date / "submit" / "corporate_action_symbol_quarantine_continuation.json"


def _historical_ca_quarantine_terminalization_checks(
    *,
    pending_payload: dict[str, Any],
    submit_payload: dict[str, Any],
    continuation: dict[str, Any],
    business_date: str,
    submit_manifest_path: Path,
) -> dict[str, bool]:
    guard_items = submit_payload.get("submit_guard_item_evidence")
    guard_items = guard_items if isinstance(guard_items, list) else []
    pending_items = pending_payload.get("items") if isinstance(pending_payload.get("items"), list) else []
    pending_ids = {str(item.get("pending_item_id") or "") for item in pending_items if isinstance(item, dict)}
    pending_symbols = {str(item.get("symbol") or "").strip().upper() for item in pending_items if isinstance(item, dict)}
    affected_symbols = {
        str(symbol).strip().upper()
        for symbol in continuation.get("affected_symbols") or ()
        if str(symbol).strip()
    }
    continuation_checks = continuation.get("checks") if isinstance(continuation.get("checks"), dict) else {}
    prohibited = submit_payload.get("prohibited_actions") if isinstance(submit_payload.get("prohibited_actions"), dict) else {}
    submitted_count = _int_value(submit_payload.get("submitted_count"), 0)
    blocked_count = _int_value(submit_payload.get("blocked_count"), 0)
    pending_item_count = _int_value(submit_payload.get("pending_item_count"), 0)
    ca_blocked_items = [
        item
        for item in guard_items
        if str(item.get("pending_item_id") or "") in pending_ids
        and str(item.get("submit_item_status") or "") == "REVIEW_REQUIRED"
        and str(item.get("guard_decision") or "") == "BLOCKED"
        and str(item.get("guard_reason") or item.get("blocked_at_submit_reason") or "") == "corporate_action_event_not_resolved"
        and str(item.get("violated_policy") or "") == "historical_corporate_action_symbol_quarantine"
        and str(item.get("submit_status") or "NOT_SUBMITTED") in {"", "NOT_SUBMITTED"}
    ]
    return {
        "mode_historical": _manifest_indicates_historical(submit_payload),
        "same_business_date": str(submit_payload.get("business_date") or "") == business_date,
        "pending_approved": _state(pending_payload) == "APPROVED",
        "pending_unconsumed": not _consumed(pending_payload),
        "pending_target_session_same_day": str(pending_payload.get("target_session_date") or "") == business_date,
        "continuation_artifact_present": bool(continuation),
        "continuation_status": str(continuation.get("status") or "") == "COMPLETED_WITH_SYMBOL_QUARANTINE",
        "continuation_business_date": str(continuation.get("business_date") or "") == business_date,
        "continuation_job": str(continuation.get("job") or "") == "submit",
        "continuation_scope": str(continuation.get("scope") or "") == "CORPORATE_ACTION_SYMBOL_ONLY",
        "production_never": str(continuation.get("production_applicability") or "") == "NEVER",
        "run_continuation_historical_only": (
            str(continuation.get("corporate_action_run_continuation_eligibility") or "")
            == "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY"
        ),
        "affected_symbol_matches_pending": bool(affected_symbols) and pending_symbols.issubset(affected_symbols),
        "submitted_count_zero": submitted_count == 0,
        "blocked_count_matches_pending": blocked_count == len(pending_items) > 0,
        "pending_count_matches_guard": pending_item_count == len(guard_items) == len(pending_items) > 0,
        "all_pending_items_ca_blocked": len(ca_blocked_items) == len(pending_items) == blocked_count,
        "no_generic_review_mixed_in": blocked_count == len(ca_blocked_items),
        "submit_review_required": str(submit_payload.get("final_state") or "") == "REVIEW_REQUIRED",
        "submit_nonzero": _int_value(submit_payload.get("exit_code"), -1) != 0,
        "no_broker_write": (
            not bool(submit_payload.get("broker_write"))
            and not bool(submit_payload.get("external_delivery"))
            and not bool(prohibited.get("demo_submit_executed"))
            and not bool(prohibited.get("production_order_executed"))
            and not bool(prohibited.get("broker_write"))
            and not bool(prohibited.get("external_delivery"))
        ),
        "continuation_runtime_manifest_bound": (
            str(continuation.get("runtime_manifest_path") or "") in {"", str(submit_manifest_path)}
            or Path(str(continuation.get("runtime_manifest_path") or "")).name == submit_manifest_path.name
            or str(continuation.get("runtime_manifest_path") or "").endswith(
                f"/daily/{business_date}/submit/runtime_manifest.json"
            )
        ),
        "classifier_checks_pass": all(bool(value) for value in continuation_checks.values()) if continuation_checks else False,
    }


def _derive_mixed_item_terminal_outcomes(
    *,
    root: Path,
    pending_items: list[Any],
    submit_payload: dict[str, Any],
    continuation: dict[str, Any],
    business_date: str,
) -> list[dict[str, Any]]:
    guard_items = submit_payload.get("submit_guard_item_evidence")
    guard_items = guard_items if isinstance(guard_items, list) else []
    affected_symbols = {str(symbol).strip().upper() for symbol in continuation.get("affected_symbols") or () if str(symbol).strip()}
    ledger_orders = _read_ledger_jsonl(root / "persistent_ledger" / "orders.jsonl")
    outcomes: list[dict[str, Any]] = []
    for item in pending_items:
        if not isinstance(item, dict):
            continue
        pending_item_id = str(item.get("pending_item_id") or "")
        symbol = str(item.get("symbol") or "").strip().upper()
        side = str(item.get("side") or "").strip().upper()
        quantity = _float_value(item.get("quantity"))
        guard = next((guard_item for guard_item in guard_items if str(guard_item.get("pending_item_id") or "") == pending_item_id), {})
        base = {
            "pending_item_id": pending_item_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "terminal": False,
            "broker_uncertainty": False,
            "source": "",
        }
        if _is_ca_quarantine_guard_item(guard) and symbol in affected_symbols:
            outcomes.append(
                {
                    **base,
                    "outcome": "QUARANTINED_NOT_SUBMITTED",
                    "terminal": True,
                    "source": "submit_guard_historical_corporate_action_quarantine",
                }
            )
            continue
        order = _matching_filled_ledger_order(
            ledger_orders=ledger_orders,
            pending_item_id=pending_item_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            business_date=business_date,
        )
        if order:
            outcomes.append(
                {
                    **base,
                    "outcome": "FILLED",
                    "terminal": True,
                    "source": "ledger_order_full_fill",
                    "order_id": str(order.get("order_id") or ""),
                    "ledger_record_id": str(order.get("record_id") or ""),
                }
            )
            continue
        if str(guard.get("submit_item_status") or "") == "PASS":
            outcomes.append({**base, "outcome": "REVIEW_REQUIRED", "source": "submitted_item_fill_not_confirmed"})
            continue
        outcomes.append({**base, "outcome": "REVIEW_REQUIRED", "source": "unclassified_submit_item"})
    return outcomes


def _is_ca_quarantine_guard_item(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    return (
        str(item.get("submit_item_status") or "") == "REVIEW_REQUIRED"
        and str(item.get("guard_decision") or "") == "BLOCKED"
        and str(item.get("guard_reason") or item.get("blocked_at_submit_reason") or "") == "corporate_action_event_not_resolved"
        and str(item.get("violated_policy") or "") == "historical_corporate_action_symbol_quarantine"
        and str(item.get("submit_status") or "NOT_SUBMITTED") in {"", "NOT_SUBMITTED"}
    )


def _matching_filled_ledger_order(
    *,
    ledger_orders: list[dict[str, Any]],
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: float,
    business_date: str,
) -> dict[str, Any]:
    for order in ledger_orders:
        if str(order.get("business_date") or order.get("created_at") or "")[:10] not in {"", business_date}:
            continue
        order_pending_item_id = str(order.get("pending_item_id") or "")
        order_symbol = str(order.get("symbol") or "").strip().upper()
        order_side = str(order.get("side") or "").strip().upper()
        order_quantity = _float_value(order.get("quantity"))
        status = str(order.get("status") or "").lower()
        id_match = bool(pending_item_id and order_pending_item_id == pending_item_id)
        symbol_match = order_symbol == symbol and order_side == side and abs(order_quantity - quantity) < 0.000001
        if (id_match or symbol_match) and status in {"filled", "全部約定", "full_fill", "fully_filled"}:
            return order
    return {}


def _read_ledger_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _float_value(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _manifest_indicates_historical(payload: dict[str, Any]) -> bool:
    if str(payload.get("run_type") or "").upper() == "HISTORICAL":
        return True
    if str(payload.get("runtime_mode") or payload.get("mode") or "").lower() == "historical":
        return True
    return bool(payload.get("historical_replay"))


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _int_value(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _stale_reasons(*, payload: dict[str, Any], business_date: str, transitioned_at: str) -> list[str]:
    reasons: list[str] = []
    if str(payload.get("target_session_date") or "") < business_date:
        reasons.append("target_session_date_elapsed")
    approval_expires_at = _approval_expires_at(payload)
    if approval_expires_at and _expired(approval_expires_at, transitioned_at):
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


def _conflict_history_path(*, history_path: Path, new_state: str, reason: str) -> Path:
    suffix = hashlib.sha256(f"{new_state}:{reason}".encode("utf-8")).hexdigest()[:12]
    return history_path.with_name(f"{history_path.stem}-{suffix}{history_path.suffix}")


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


def _expired(expires_at: str, transitioned_at: str) -> bool:
    expires = _parse_datetime(expires_at)
    transitioned = _parse_datetime(transitioned_at)
    if expires is None or transitioned is None:
        return expires_at <= transitioned_at
    return expires <= transitioned


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _consumed(payload: dict[str, Any]) -> bool:
    consume = payload.get("consume") or {}
    return bool(consume.get("consumed")) or _state(payload) == "CONSUMED"


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
