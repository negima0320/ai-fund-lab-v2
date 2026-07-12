"""Authoritative Runtime Operation State contract.

This artifact records Runtime control state only. Asset state remains owned by
``persistent_ledger/state.json`` and pending lifecycle remains owned by
``pending_order_plan/pending_order_plan.json``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.state_machine.models import RuntimeState


RUNTIME_OPERATION_STATE_SCHEMA_VERSION = "runtime_v2_operation_state_v1"
RUNTIME_OPERATION_STATE_ROLE = "authoritative_runtime_operation_state"


@dataclass(frozen=True)
class RuntimeOperationStateResult:
    status: str
    reason: str
    artifact_path: str
    payload: dict[str, Any]
    missing_fields: tuple[str, ...] = ()
    stale_fields: tuple[str, ...] = ()

    @property
    def manifest_fields(self) -> dict[str, Any]:
        return {
            "runtime_state_status": self.status,
            "runtime_state_reason": self.reason,
            "runtime_state_artifact_path": self.artifact_path,
            "runtime_state_schema_version": self.payload.get("schema_version") or "",
            "runtime_state_role": self.payload.get("role") or "",
            "runtime_state_business_date": self.payload.get("business_date") or "",
            "runtime_state_generated_at": self.payload.get("generated_at") or "",
            "runtime_state_current_state": self.payload.get("state") or "",
            "runtime_state_safety_state": self.payload.get("safety_state") or "",
            "runtime_state_missing_fields": list(self.missing_fields),
            "runtime_state_stale_fields": list(self.stale_fields),
            "runtime_state_production_equivalent": bool(self.payload.get("production_equivalent")),
        }


def produce_runtime_operation_state(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    state: str = RuntimeState.CURRENT_STATE_LOADED.value,
    safety_state: str = "NORMAL",
    reason: str = "runtime_state_refresh",
    now: datetime | None = None,
) -> RuntimeOperationStateResult:
    """Write the authoritative runtime operation state artifact."""

    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    payload = {
        "schema_version": RUNTIME_OPERATION_STATE_SCHEMA_VERSION,
        "role": RUNTIME_OPERATION_STATE_ROLE,
        "business_date": business_date,
        "generated_at": generated_at,
        "updated_at": generated_at,
        "environment": mode,
        "runtime_mode": mode,
        "state": state,
        "safety_state": safety_state,
        "current_safety_state": safety_state,
        "source": "runtime_v2_runtime_state_producer",
        "producer": "runtime_operation_state_refresh",
        "reason": reason,
        "asset_state_source": "persistent_ledger/state.json",
        "pending_state_source": "pending_order_plan/pending_order_plan.json",
        "asset_state_is_authoritative_here": False,
        "pending_state_is_authoritative_here": False,
        "production_equivalent": mode == "production",
    }
    path = Path(runtime_root) / "runtime_state" / "current_state.json"
    _atomic_write_json(path, payload)
    return validate_runtime_operation_state(
        runtime_root=runtime_root,
        business_date=business_date,
        mode=mode,
    )


def validate_runtime_operation_state(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
) -> RuntimeOperationStateResult:
    """Validate the runtime operation state artifact against the contract."""

    path = Path(runtime_root) / "runtime_state" / "current_state.json"
    if not path.exists():
        return RuntimeOperationStateResult(
            status="REVIEW_REQUIRED",
            reason="runtime_state_missing",
            artifact_path=str(path),
            payload={},
            missing_fields=("runtime_state",),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return RuntimeOperationStateResult(
            status="HALT",
            reason="runtime_state_invalid_json",
            artifact_path=str(path),
            payload={},
            missing_fields=("runtime_state_valid_json",),
        )
    if not isinstance(payload, dict):
        return RuntimeOperationStateResult(
            status="HALT",
            reason="runtime_state_not_object",
            artifact_path=str(path),
            payload={},
            missing_fields=("runtime_state_object",),
        )

    missing = [
        key
        for key in (
            "schema_version",
            "role",
            "business_date",
            "generated_at",
            "environment",
            "state",
            "safety_state",
            "source",
        )
        if not payload.get(key)
    ]
    stale: list[str] = []
    if payload.get("schema_version") != RUNTIME_OPERATION_STATE_SCHEMA_VERSION:
        stale.append("schema_version")
    if payload.get("role") != RUNTIME_OPERATION_STATE_ROLE:
        stale.append("role")
    if str(payload.get("business_date") or "") != business_date:
        stale.append("business_date")
    if str(payload.get("environment") or payload.get("runtime_mode") or "") != mode:
        stale.append("environment")
    try:
        RuntimeState(str(payload.get("state") or ""))
    except ValueError:
        stale.append("state")

    if missing:
        return RuntimeOperationStateResult(
            status="REVIEW_REQUIRED",
            reason="runtime_state_contract_missing_fields",
            artifact_path=str(path),
            payload=payload,
            missing_fields=tuple(sorted(set(missing))),
            stale_fields=tuple(sorted(set(stale))),
        )
    if stale:
        return RuntimeOperationStateResult(
            status="REVIEW_REQUIRED",
            reason="runtime_state_contract_stale_or_invalid",
            artifact_path=str(path),
            payload=payload,
            stale_fields=tuple(sorted(set(stale))),
        )
    return RuntimeOperationStateResult(
        status="READY",
        reason="runtime_state_ready",
        artifact_path=str(path),
        payload=payload,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)
