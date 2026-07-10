"""Runtime Safety Decision producer for Runtime v2.

The producer does not decide Safety by itself. It normalizes authoritative
Safety evidence into the RuntimeSafetyDecision contract consumed by Runtime v2.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.runtime_v2.safety_decision import (
    SAFETY_DECISION_RELATIVE_PATH,
    RuntimeSafetyDecision,
    safety_decision_to_payload,
)


HISTORY_RELATIVE_ROOT = Path("runtime_state") / "safety" / "history"
DEFAULT_SOURCE_RELATIVE_ROOT = Path("reports") / "safety" / "phase11"
AUTHORITATIVE_SAFETY_SOURCE = "phase11_safety_report_v2"


@dataclass(frozen=True)
class RuntimeSafetyProducerResult:
    status: str
    reason: str
    decision: RuntimeSafetyDecision
    source_artifact_path: str
    runtime_safety_decision_path: str
    history_path: str
    manifest_fields: dict[str, Any]

    def to_stage_details(self) -> dict[str, Any]:
        return dict(self.manifest_fields)


def produce_runtime_safety_decision(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    source_artifact_path: Path | str | None = None,
    now: datetime | None = None,
) -> RuntimeSafetyProducerResult:
    root = Path(runtime_root)
    now_dt = now or datetime.now(timezone.utc)
    source_path = _resolve_source_path(root=root, business_date=business_date, source_artifact_path=source_artifact_path)
    source_payload, source_status, source_reason = _load_source_payload(source_path)
    decision = _decision_from_source(
        source_payload=source_payload,
        source_path=source_path,
        source_status=source_status,
        source_reason=source_reason,
        runtime_root=root,
        business_date=business_date,
        mode=mode,
        now=now_dt,
    )
    latest_path = root / SAFETY_DECISION_RELATIVE_PATH
    history_path = root / HISTORY_RELATIVE_ROOT / business_date / (decision.safety_decision_id + ".json")
    payload = safety_decision_to_payload(decision)
    _atomic_write_json(latest_path, payload)
    _atomic_write_json(history_path, payload)
    status = _producer_status(decision)
    manifest_fields = _manifest_fields(
        status=status,
        decision=decision,
        source_payload=source_payload,
        source_path=source_path,
        latest_path=latest_path,
        history_path=history_path,
        source_status=source_status,
        source_reason=source_reason,
    )
    return RuntimeSafetyProducerResult(
        status=status,
        reason=decision.reason,
        decision=decision,
        source_artifact_path=str(source_path),
        runtime_safety_decision_path=str(latest_path),
        history_path=str(history_path),
        manifest_fields=manifest_fields,
    )


def _resolve_source_path(
    *,
    root: Path,
    business_date: str,
    source_artifact_path: Path | str | None,
) -> Path:
    if source_artifact_path:
        return Path(source_artifact_path)
    base = root.parent if root.name == ".runtime" else Path(".")
    return base / DEFAULT_SOURCE_RELATIVE_ROOT / f"{business_date}_safety_report.json"


def _load_source_payload(path: Path) -> tuple[dict[str, Any], str, str]:
    if not path.exists():
        return {}, "SOURCE_MISSING", "authoritative safety source missing"
    if not path.is_file():
        return {}, "SOURCE_INVALID", "authoritative safety source is not a file"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, "SOURCE_INVALID", f"authoritative safety source invalid json: {exc.msg}"
    if not isinstance(payload, dict):
        return {}, "SOURCE_INVALID", "authoritative safety source must be a JSON object"
    return payload, "SOURCE_PRESENT", ""


def _decision_from_source(
    *,
    source_payload: dict[str, Any],
    source_path: Path,
    source_status: str,
    source_reason: str,
    runtime_root: Path,
    business_date: str,
    mode: str,
    now: datetime,
) -> RuntimeSafetyDecision:
    reasons: list[str] = []
    source_valid = source_status == "SOURCE_PRESENT"
    if not source_valid:
        reasons.append(source_reason)

    schema_version = str(source_payload.get("schema_version") or "")
    if source_valid and schema_version != AUTHORITATIVE_SAFETY_SOURCE:
        source_valid = False
        reasons.append("authoritative safety source schema mismatch")

    source_business_date = str(source_payload.get("business_date") or "")
    if source_valid and source_business_date != business_date:
        source_valid = False
        reasons.append("business_date mismatch")

    source_mode = str(source_payload.get("environment") or source_payload.get("runtime_mode") or "")
    if source_valid and source_mode and source_mode != mode:
        source_valid = False
        reasons.append("mode mismatch")
    if source_valid and not source_mode:
        source_valid = False
        reasons.append("mode missing")

    generated_at = str(source_payload.get("generated_at") or "")
    expires_at = str(source_payload.get("expires_at") or "")
    generated_dt = _parse_datetime(generated_at)
    expires_dt = _parse_datetime(expires_at)
    if source_valid and generated_dt is None:
        source_valid = False
        reasons.append("generated_at missing or invalid")
    if source_valid and expires_dt is None:
        source_valid = False
        reasons.append("expires_at missing or invalid")
    if source_valid and expires_dt is not None and expires_dt <= now:
        source_valid = False
        reasons.append("source expired")

    lock_payload = _latest_lock_payload(runtime_root)
    lock_conflict = _lock_conflict(source_payload, lock_payload)
    if lock_conflict:
        source_valid = False
        reasons.append(lock_conflict)

    if not source_valid:
        return _runtime_decision(
            source_path=source_path,
            business_date=business_date,
            mode=mode,
            decision="REVIEW_REQUIRED",
            reason="; ".join(reason for reason in reasons if reason) or "safety source invalid",
            review_required=True,
            block_buy=True,
            block_sell=True,
            block_submit=True,
            halt_runtime=False,
            emergency_stop=False,
            generated_at=_iso(now),
            expires_at="",
            safety_status="SAFETY_SOURCE_INVALID",
            policy_version=schema_version or "",
        )

    mapped = _map_phase11_report(source_payload)
    if lock_payload and bool(lock_payload.get("is_locked")):
        mapped["decision"] = "HALT" if str(lock_payload.get("status") or "").upper() == "HALT" else "BLOCKED"
        mapped["reason"] = "trading lock active: " + str(lock_payload.get("reason") or "locked")
        mapped["review_required"] = True
        mapped["block_buy"] = True
        mapped["block_sell"] = True
        mapped["block_submit"] = True
        mapped["halt_runtime"] = mapped["decision"] == "HALT"

    return _runtime_decision(
        source_path=source_path,
        business_date=business_date,
        mode=mode,
        decision=mapped["decision"],
        reason=mapped["reason"],
        review_required=mapped["review_required"],
        block_buy=mapped["block_buy"],
        block_sell=mapped["block_sell"],
        block_submit=mapped["block_submit"],
        halt_runtime=mapped["halt_runtime"],
        emergency_stop=mapped["emergency_stop"],
        generated_at=generated_at,
        expires_at=expires_at,
        safety_status="PASS",
        policy_version=schema_version,
    )


def _map_phase11_report(payload: dict[str, Any]) -> dict[str, Any]:
    overall = str(payload.get("overall_decision") or "REVIEW_REQUIRED").upper()
    next_state = str(payload.get("next_recommended_safety_state") or "").upper()
    blocked_actions = {str(item).lower() for item in payload.get("blocked_actions") or ()}
    review_items = tuple(item for item in payload.get("review_required_items") or () if isinstance(item, dict))
    emergency = (
        overall == "EMERGENCY_STOP"
        or next_state in {"SYSTEM_EMERGENCY_STOP", "EMERGENCY_STOP"}
        or bool(payload.get("emergency_candidates"))
    )
    if emergency:
        decision = "HALT"
    elif overall == "ALLOW":
        decision = "ALLOW"
    elif overall == "BLOCK":
        decision = "BLOCKED"
    else:
        decision = "REVIEW_REQUIRED"

    block_buy = (
        decision != "ALLOW"
        or "new_buy" in blocked_actions
        or "new_buy_without_human_review" in blocked_actions
        or "new_buy_during_buy_stop" in blocked_actions
        or bool(payload.get("buy_review_required"))
        or bool(payload.get("buy_opportunity_review"))
    )
    block_sell = bool(payload.get("sell_review_required")) or "auto_sell" in blocked_actions or decision == "HALT"
    block_submit = (
        decision != "ALLOW"
        or "all_order_submission" in blocked_actions
        or "broker_order_api" in blocked_actions
        or "demo_order_submit" in blocked_actions
        or "production_order_submit" in blocked_actions
    )
    reason = str(payload.get("transition_reason") or overall or decision)
    if review_items and decision == "REVIEW_REQUIRED":
        reason = "; ".join(str(item.get("reason_code") or item.get("message") or "") for item in review_items[:3])
    return {
        "decision": decision,
        "reason": reason or decision,
        "review_required": decision != "ALLOW" or bool(review_items),
        "block_buy": block_buy,
        "block_sell": block_sell,
        "block_submit": block_submit,
        "halt_runtime": decision == "HALT",
        "emergency_stop": emergency,
    }


def _runtime_decision(
    *,
    source_path: Path,
    business_date: str,
    mode: str,
    decision: str,
    reason: str,
    review_required: bool,
    block_buy: bool,
    block_sell: bool,
    block_submit: bool,
    halt_runtime: bool,
    emergency_stop: bool,
    generated_at: str,
    expires_at: str,
    safety_status: str,
    policy_version: str,
) -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="runtime-safety-decision-" + uuid4().hex[:16],
        safety_policy_version=policy_version,
        safety_source=str(source_path),
        business_date=business_date,
        runtime_mode=mode,
        decision=decision,
        reason=reason,
        review_required=review_required,
        block_buy=block_buy,
        block_sell=block_sell,
        block_submit=block_submit,
        halt_runtime=halt_runtime,
        emergency_stop=emergency_stop,
        generated_at=generated_at,
        expires_at=expires_at,
        safety_status=safety_status,
        artifact_path="",
    )


def _manifest_fields(
    *,
    status: str,
    decision: RuntimeSafetyDecision,
    source_payload: dict[str, Any],
    source_path: Path,
    latest_path: Path,
    history_path: Path,
    source_status: str,
    source_reason: str,
) -> dict[str, Any]:
    return {
        "safety_producer_status": status,
        "authoritative_safety_source": AUTHORITATIVE_SAFETY_SOURCE,
        "source_artifact_path": str(source_path),
        "source_policy_version": str(source_payload.get("schema_version") or ""),
        "source_business_date": str(source_payload.get("business_date") or ""),
        "source_generated_at": str(source_payload.get("generated_at") or ""),
        "source_expires_at": str(source_payload.get("expires_at") or ""),
        "source_freshness_status": _source_freshness_status(decision, source_status, source_reason),
        "runtime_safety_decision_path": str(latest_path),
        "runtime_safety_decision_history_path": str(history_path),
        "safety_decision_id": decision.safety_decision_id,
        "safety_policy_version": decision.safety_policy_version,
        "safety_decision": decision.decision,
        "safety_reason": decision.reason,
        "block_buy": decision.block_buy,
        "block_sell": decision.block_sell,
        "block_submit": decision.block_submit,
        "halt_runtime": decision.halt_runtime,
        "emergency_stop": decision.emergency_stop,
        "review_required": decision.review_required,
        "production_equivalent": False,
    }


def _source_freshness_status(decision: RuntimeSafetyDecision, source_status: str, source_reason: str) -> str:
    if source_status != "SOURCE_PRESENT":
        return source_status + (":" + source_reason if source_reason else "")
    if decision.safety_status != "PASS":
        return "REVIEW_REQUIRED:" + decision.reason
    return "PASS"


def _producer_status(decision: RuntimeSafetyDecision) -> str:
    if decision.halt_runtime or decision.emergency_stop or decision.decision == "HALT":
        return "HALT"
    if decision.decision == "BLOCKED":
        return "BLOCKED"
    if decision.review_required or decision.decision == "REVIEW_REQUIRED" or decision.safety_status != "PASS":
        return "REVIEW_REQUIRED"
    return "PASS"


def _latest_lock_payload(runtime_root: Path) -> dict[str, Any] | None:
    lock_dir = runtime_root / "safety" / "locks"
    if not lock_dir.exists():
        return None
    locks = sorted(path for path in lock_dir.glob("*.json") if path.is_file())
    if not locks:
        return None
    try:
        payload = json.loads(locks[-1].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"is_locked": True, "status": "HALT", "reason": "trading lock invalid json"}
    return payload if isinstance(payload, dict) else {"is_locked": True, "status": "HALT", "reason": "trading lock invalid"}


def _lock_conflict(source_payload: dict[str, Any], lock_payload: dict[str, Any] | None) -> str:
    if not lock_payload:
        return ""
    source_allows = str(source_payload.get("overall_decision") or "").upper() == "ALLOW"
    if source_allows and bool(lock_payload.get("is_locked")):
        return "conflicting Safety evidence: source allows while trading lock is active"
    return ""


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
