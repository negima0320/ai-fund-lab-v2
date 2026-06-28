from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState, safety_id, utc_now_iso
from ai_fund_lab_v2.safety_phase11.recovery import RecoveryDecision
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine, coerce_state


@dataclass(frozen=True)
class ManualUnlockApproval:
    approved_by: str
    reason: str
    target_state: SafetyState
    source_state: SafetyState
    safety_report_path: str
    recovery_evidence: tuple[str, ...]
    expires_at: str
    active: bool = True
    approved_at: str = field(default_factory=utc_now_iso)
    approval_id: str = field(default_factory=lambda: safety_id("manual_unlock_approval"))
    auto_trade_executed: bool = False
    auto_recovery_executed: bool = False
    raw_response_saved: bool = False


@dataclass(frozen=True)
class ManualUnlockValidation:
    valid: bool
    reason_codes: tuple[str, ...]
    next_state: SafetyState
    requires_latest_safety_check_ok: bool = True
    auto_recovery_executed: bool = False


def create_manual_unlock_approval(
    *,
    approved_by: str,
    reason: str,
    source_state: SafetyState | str,
    safety_report_path: str,
    recovery_evidence: tuple[str, ...],
    expires_at: str | None = None,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    source = coerce_state(source_state)
    approval = ManualUnlockApproval(
        approved_by=approved_by,
        reason=reason,
        target_state=SafetyState.MANUAL_APPROVED,
        source_state=source,
        safety_report_path=safety_report_path,
        recovery_evidence=recovery_evidence,
        expires_at=expires_at or (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
        active=True,
    )
    path = manual_unlock_path(runtime_dir)
    _write_json(path, _safe_approval_payload(approval))
    return path


def read_manual_unlock_approval(runtime_dir: Path | str = ".runtime") -> dict[str, Any]:
    path = manual_unlock_path(runtime_dir)
    if not path.exists():
        return {"active": False, "source": "missing", "path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["path"] = str(path)
    return payload


def validate_manual_unlock_approval(payload: dict[str, Any], *, now: datetime | None = None) -> ManualUnlockValidation:
    reasons: list[str] = []
    source = _parse_state(payload.get("source_state"))
    target = _parse_state(payload.get("target_state"))
    if not payload.get("active", False):
        reasons.append("approval_inactive")
    if source not in {SafetyState.BUY_STOP, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
        reasons.append("invalid_source_state")
    if target is not SafetyState.MANUAL_APPROVED:
        reasons.append("invalid_target_state")
    if not payload.get("safety_report_path"):
        reasons.append("missing_safety_report_path")
    if not payload.get("recovery_evidence"):
        reasons.append("missing_recovery_evidence")
    if _is_expired(str(payload.get("expires_at") or ""), now=now):
        reasons.append("approval_expired")
    if reasons:
        return ManualUnlockValidation(valid=False, reason_codes=tuple(reasons), next_state=source or SafetyState.EMERGENCY_STOP)
    transition = SafetyStateMachine(current_state=source).validate_transition(source, SafetyState.RECOVERY_CANDIDATE)
    if not transition.allowed:
        return ManualUnlockValidation(valid=False, reason_codes=("recovery_candidate_transition_invalid",), next_state=source)
    transition = SafetyStateMachine(current_state=SafetyState.RECOVERY_CANDIDATE).validate_transition(
        SafetyState.RECOVERY_CANDIDATE, SafetyState.MANUAL_APPROVED
    )
    return ManualUnlockValidation(valid=transition.allowed, reason_codes=() if transition.allowed else ("manual_approved_transition_invalid",), next_state=transition.to_state)


def validate_normal_return_after_manual_approval(
    *,
    current_state: SafetyState | str,
    latest_safety_decision: SafetyDecision | str,
) -> ManualUnlockValidation:
    state = coerce_state(current_state)
    if state is not SafetyState.MANUAL_APPROVED:
        return ManualUnlockValidation(valid=False, reason_codes=("state_not_manual_approved",), next_state=state)
    decision = latest_safety_decision if isinstance(latest_safety_decision, SafetyDecision) else SafetyDecision(str(latest_safety_decision))
    if decision is not SafetyDecision.ALLOW:
        return ManualUnlockValidation(valid=False, reason_codes=("latest_safety_check_not_allow",), next_state=state)
    transition = SafetyStateMachine(current_state=state).validate_transition(state, SafetyState.NORMAL)
    return ManualUnlockValidation(valid=transition.allowed, reason_codes=() if transition.allowed else ("normal_transition_invalid",), next_state=transition.to_state)


def approval_from_recovery_decision(
    recovery: RecoveryDecision,
    *,
    approved_by: str,
    reason: str,
    source_state: SafetyState | str,
    safety_report_path: str,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    if not recovery.recovery_candidate:
        raise ValueError("manual unlock approval requires recovery_candidate=true")
    return create_manual_unlock_approval(
        approved_by=approved_by,
        reason=reason,
        source_state=source_state,
        safety_report_path=safety_report_path,
        recovery_evidence=recovery.satisfied_evidence,
        runtime_dir=runtime_dir,
    )


def manual_unlock_path(runtime_dir: Path | str) -> Path:
    return Path(runtime_dir) / "safety" / "phase11" / "state" / "manual_unlock_approval.json"


def _safe_approval_payload(approval: ManualUnlockApproval) -> dict[str, Any]:
    payload = asdict(approval)
    payload["target_state"] = approval.target_state.value
    payload["source_state"] = approval.source_state.value
    payload["recovery_evidence"] = list(approval.recovery_evidence)
    return _phase11_sanitize(payload)


def _parse_state(value: Any) -> SafetyState | None:
    try:
        return SafetyState(str(value))
    except ValueError:
        return None


def _is_expired(expires_at: str, *, now: datetime | None = None) -> bool:
    if not expires_at:
        return True
    try:
        parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= (now or datetime.now(timezone.utc))
