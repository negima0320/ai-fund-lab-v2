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
    if decision not in {"ALLOW", "REVIEW_REQUIRED", "BLOCKED", "HALT"}:
        decision = "REVIEW_REQUIRED"
    review_required = _bool(payload.get("review_required"), default=decision == "REVIEW_REQUIRED")
    halt_runtime = _bool(payload.get("halt_runtime"), default=decision == "HALT")
    emergency_stop = _bool(payload.get("emergency_stop"), default=False)
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
        safety_status="PASS",
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
        artifact_path=str(path),
    )


def _bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
