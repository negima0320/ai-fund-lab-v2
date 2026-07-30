"""Runtime v2 Safety / Operation Guard decision contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SAFETY_DECISION_RELATIVE_PATH = Path("runtime_state") / "safety" / "latest_safety_decision.json"


@dataclass(frozen=True)
class RuntimeSafetyDecision:
    safety_decision_id: str
    safety_policy_version: str
    safety_source: str
    business_date: str
    runtime_mode: str
    decision: str
    reason: str
    review_required: bool
    block_buy: bool
    block_sell: bool
    block_submit: bool
    halt_runtime: bool
    emergency_stop: bool
    generated_at: str
    expires_at: str
    safety_status: str
    action_permissions: dict[str, str] | None = None
    human_review_artifact_refs: list[dict[str, Any]] | None = None
    artifact_path: str = ""

    def to_manifest_fields(self) -> dict[str, Any]:
        return {
            "safety_decision_id": self.safety_decision_id,
            "safety_policy_version": self.safety_policy_version,
            "safety_source": self.safety_source,
            "safety_decision": self.decision,
            "safety_reason": self.reason,
            "safety_status": self.safety_status,
            "safety_block_buy": self.block_buy,
            "safety_block_sell": self.block_sell,
            "safety_block_submit": self.block_submit,
            "safety_halt_runtime": self.halt_runtime,
            "safety_emergency_stop": self.emergency_stop,
            "safety_review_required": self.review_required,
            "safety_generated_at": self.generated_at,
            "safety_expires_at": self.expires_at,
            "safety_action_permissions": dict(self.action_permissions or {}),
            "safety_human_review_artifact_refs": list(self.human_review_artifact_refs or []),
            "safety_artifact_path": self.artifact_path,
        }


def load_runtime_safety_decision(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
) -> RuntimeSafetyDecision:
    path = Path(runtime_root) / SAFETY_DECISION_RELATIVE_PATH
    if not path.exists():
        return _missing_decision(path=path, business_date=business_date, mode=mode)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return RuntimeSafetyDecision(
            safety_decision_id="",
            safety_policy_version="",
            safety_source="",
            business_date=business_date,
            runtime_mode=mode,
            decision="REVIEW_REQUIRED",
            reason=f"safety decision invalid json: {exc.msg}",
            review_required=True,
            block_buy=True,
            block_sell=True,
            block_submit=True,
            halt_runtime=False,
            emergency_stop=False,
            generated_at="",
            expires_at="",
            safety_status="SAFETY_INVALID",
            action_permissions=_fail_closed_action_permissions(),
            artifact_path=str(path),
        )
    return _decision_from_payload(payload, path=path, business_date=business_date, mode=mode)


def safety_allows_action(decision: RuntimeSafetyDecision, *, action: str, side: str = "") -> tuple[bool, str, str]:
    if decision.safety_status != "PASS":
        return False, "REVIEW_REQUIRED", decision.reason or decision.safety_status
    if decision.halt_runtime or decision.emergency_stop or decision.decision == "HALT":
        return False, "HALT", decision.reason or "safety halt runtime"
    if decision.decision == "BLOCKED":
        return False, "BLOCKED", decision.reason or "safety decision blocked"
    scoped = _scoped_permission(decision, action=action, side=side)
    if scoped:
        if scoped in {"ALLOWED", "ALLOWED_FOR_REVIEW", "ALLOWED_FOR_ACCEPTANCE", "ALLOWED_FOR_REPLAY"}:
            return True, "PASS", decision.reason or f"safety action scope {scoped.lower()}"
        if scoped == "REVIEW_REQUIRED":
            return False, "REVIEW_REQUIRED", decision.reason or "safety action scope review required"
        return False, "BLOCKED", decision.reason or "safety action scope blocked"
    if decision.action_permissions is not None:
        return False, "REVIEW_REQUIRED", decision.reason or "safety action scope missing"
    if decision.decision == "NEUTRAL":
        return False, "REVIEW_REQUIRED", decision.reason or "safety neutral decision requires scoped permissions"
    if decision.decision == "REVIEW_REQUIRED" or decision.review_required:
        return False, "REVIEW_REQUIRED", decision.reason or "safety review required"
    if action == "submit" and decision.block_submit:
        return False, "REVIEW_REQUIRED", decision.reason or "safety blocks submit"
    side_upper = side.upper()
    if side_upper == "BUY" and decision.block_buy:
        return False, "REVIEW_REQUIRED", decision.reason or "safety blocks BUY"
    if side_upper == "SELL" and decision.block_sell:
        return False, "REVIEW_REQUIRED", decision.reason or "safety blocks SELL"
    return True, "PASS", decision.reason or "safety allow"


def safety_manifest_fields(decision: RuntimeSafetyDecision | None) -> dict[str, Any]:
    if decision is None:
        return {}
    return decision.to_manifest_fields()


def safety_decision_to_payload(decision: RuntimeSafetyDecision) -> dict[str, Any]:
    return asdict(decision)


def _decision_from_payload(
    payload: dict[str, Any],
    *,
    path: Path,
    business_date: str,
    mode: str,
) -> RuntimeSafetyDecision:
    decision = str(payload.get("decision") or "").upper()
    if decision not in {"ALLOW", "NEUTRAL", "REVIEW_REQUIRED", "BLOCKED", "HALT"}:
        decision = "REVIEW_REQUIRED"
    review_required = _bool(payload.get("review_required"), default=decision == "REVIEW_REQUIRED")
    halt_runtime = _bool(payload.get("halt_runtime"), default=decision == "HALT")
    emergency_stop = _bool(payload.get("emergency_stop"), default=False)
    freshness_status = str(payload.get("freshness_status") or payload.get("safety_temporal_status") or "").upper()
    safety_status = "PASS"
    if freshness_status in {"STALE", "EXPIRED"}:
        safety_status = f"SAFETY_{freshness_status}"
    raw_action_permissions = payload.get("action_permissions")
    return RuntimeSafetyDecision(
        safety_decision_id=str(payload.get("safety_decision_id") or ""),
        safety_policy_version=str(payload.get("safety_policy_version") or ""),
        safety_source=str(payload.get("safety_source") or ""),
        business_date=str(payload.get("business_date") or business_date),
        runtime_mode=str(payload.get("runtime_mode") or mode),
        decision=decision,
        reason=str(payload.get("reason") or ""),
        review_required=review_required,
        block_buy=_bool(payload.get("block_buy"), default=False),
        block_sell=_bool(payload.get("block_sell"), default=False),
        block_submit=_bool(payload.get("block_submit"), default=False),
        halt_runtime=halt_runtime,
        emergency_stop=emergency_stop,
        generated_at=str(payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        safety_status=safety_status,
        action_permissions=dict(raw_action_permissions) if isinstance(raw_action_permissions, dict) else None,
        human_review_artifact_refs=list(payload.get("human_review_artifact_refs") or []),
        artifact_path=str(path),
    )


def _missing_decision(*, path: Path, business_date: str, mode: str) -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="",
        safety_policy_version="",
        safety_source="",
        business_date=business_date,
        runtime_mode=mode,
        decision="REVIEW_REQUIRED",
        reason="safety decision evidence missing",
        review_required=True,
        block_buy=True,
        block_sell=True,
        block_submit=True,
        halt_runtime=False,
        emergency_stop=False,
        generated_at="",
        expires_at="",
        safety_status="SAFETY_MISSING",
        action_permissions=_fail_closed_action_permissions(),
        artifact_path=str(path),
    )


def _bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _scoped_permission(decision: RuntimeSafetyDecision, *, action: str, side: str) -> str:
    permissions = {str(key).lower(): str(value).upper() for key, value in (decision.action_permissions or {}).items()}
    action_key = str(action or "").lower()
    side_key = str(side or "").upper()
    candidates: list[str] = []
    if action_key == "planning" and side_key == "BUY":
        candidates.append("buy_planning")
    elif action_key == "planning" and side_key == "SELL":
        candidates.extend(["sell_planning", "sell_hold_review"])
    elif action_key == "inference" and side_key == "BUY":
        candidates.append("buy_inference")
    elif action_key == "inference" and side_key == "SELL":
        candidates.append("sell_hold_inference")
    elif action_key == "submit" and side_key == "BUY":
        candidates.append("buy_submit")
    elif action_key == "submit" and side_key == "SELL":
        candidates.append("sell_submit")
    elif action_key:
        candidates.append(action_key)
    for key in candidates:
        if key in permissions:
            return permissions[key]
    return ""


def _fail_closed_action_permissions() -> dict[str, str]:
    return {
        "buy_inference": "BLOCKED",
        "buy_planning": "BLOCKED",
        "sell_hold_inference": "BLOCKED",
        "sell_planning": "BLOCKED",
        "buy_submit": "BLOCKED",
        "sell_submit": "BLOCKED",
        "auto_sell": "BLOCKED",
        "human_review": "ALLOWED",
        "broker_write": "BLOCKED",
    }
