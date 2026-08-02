"""Canonical no-order authority materialization for EMPTY Pending plans."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "phase24_e1_empty_pending_no_order_authority.v1"


def materialize_empty_pending_no_order_authority(
    payload: Mapping[str, Any],
    *,
    runtime_root: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    authority_reason: str,
    sell_order_plan_path: Path | str,
    sell_approval_path: Path | str,
    sell_reason: str,
    add_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pending = dict(payload)
    pending_plan_id = str(pending.get("pending_plan_id") or "")
    source_artifacts = _source_artifacts(
        runtime_root=runtime_root,
        business_date=business_date,
        sell_order_plan_path=Path(sell_order_plan_path),
        sell_approval_path=Path(sell_approval_path),
    )
    reason_codes = _reason_codes(
        sell_reason=sell_reason,
        add_evidence=add_evidence,
        source_artifacts=source_artifacts,
    )
    authority = {
        "schema_version": SCHEMA_VERSION,
        "authority_type": "EMPTY_PENDING_NO_ORDER_AUTHORITY",
        "authority_id": f"no-order-authority-{business_date}-{_short_hash(pending_plan_id + authority_reason)}",
        "status": "NO_ORDER_AUTHORIZED",
        "authority_status": "PASS",
        "authority_reason": authority_reason,
        "authority_reason_codes": reason_codes,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "environment": environment,
        "pending_plan_id": pending_plan_id,
        "pending_state": "EMPTY",
        "pending_item_count": 0,
        "source_artifact_paths": {str(artifact["role"]): str(artifact["path"]) for artifact in source_artifacts},
        "source_artifacts": source_artifacts,
        "planning_lineage_context": {
            "schema_version": "phase24_e1_no_order_lineage.v1",
            "business_date": business_date,
            "environment": environment,
            "pending_plan_id": pending_plan_id,
            "reason_codes": reason_codes,
            "source_artifacts": source_artifacts,
        },
        "pm_add_consumer": dict(add_evidence or {}),
        "sell_no_order_context": {
            "status": "NO_SIGNAL" if str(sell_reason).startswith("NO_SIGNAL") else "NO_ORDER",
            "reason": sell_reason,
        },
        "future_information_used": False,
        "latest_fallback_used": False,
        "broker_write_performed": False,
        "no_executable_order_items": True,
    }
    authority["authority_hash"] = authority_hash(authority)
    pending.update(
        {
            "business_date": business_date,
            "target_session_date": target_session_date,
            "environment": environment,
            "status": "EMPTY",
            "state": "EMPTY",
            "active_pending": False,
            "items": [],
            "approved_item_ids": [],
            "no_order_authority": authority,
            "no_order_authority_status": "PASS",
            "no_order_authority_reason": authority_reason,
            "no_order_authority_evidence": authority,
            "planning_authority_version": SCHEMA_VERSION,
            "planning_authority_source": authority["authority_id"],
            "planning_authority_hash": authority["authority_hash"],
            "planning_lineage_context": authority["planning_lineage_context"],
        }
    )
    return pending


def validate_materialized_no_order_authority(
    payload: Mapping[str, Any],
    *,
    runtime_root: Path,
    business_date: str,
    environment: str,
) -> str:
    authority = payload.get("no_order_authority")
    if not isinstance(authority, Mapping):
        return "pending EMPTY no_order_authority missing"
    if str(authority.get("status") or "") != "NO_ORDER_AUTHORIZED":
        return "pending EMPTY no_order_authority status mismatch"
    if str(authority.get("authority_status") or "") != "PASS":
        return "pending EMPTY no_order_authority authority_status mismatch"
    if str(authority.get("business_date") or "") != business_date:
        return "pending EMPTY no_order_authority business_date mismatch"
    if str(authority.get("environment") or "") != environment:
        return "pending EMPTY no_order_authority environment mismatch"
    if str(authority.get("pending_plan_id") or "") != str(payload.get("pending_plan_id") or ""):
        return "pending EMPTY no_order_authority pending_plan_id mismatch"
    pending_item_count = authority.get("pending_item_count")
    if not isinstance(pending_item_count, int) or isinstance(pending_item_count, bool) or pending_item_count != 0:
        return "pending EMPTY no_order_authority pending_item_count mismatch"
    if not bool(authority.get("no_executable_order_items")):
        return "pending EMPTY no_order_authority executable contradiction"
    recorded_hash = str(authority.get("authority_hash") or "")
    if not recorded_hash:
        return "pending EMPTY no_order_authority hash missing"
    if recorded_hash != authority_hash(authority):
        return "pending EMPTY no_order_authority hash mismatch"
    if str(payload.get("planning_authority_version") or "") != SCHEMA_VERSION:
        return "pending EMPTY planning_authority_version mismatch"
    if str(payload.get("planning_authority_source") or "") != str(authority.get("authority_id") or ""):
        return "pending EMPTY planning_authority_source mismatch"
    if str(payload.get("planning_authority_hash") or "") != recorded_hash:
        return "pending EMPTY planning_authority_hash mismatch"
    artifacts = authority.get("source_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return "pending EMPTY no_order_authority source_artifacts missing"
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            return "pending EMPTY no_order_authority source_artifact invalid"
        if bool(artifact.get("required", True)):
            path = _resolve_path(runtime_root, str(artifact.get("path") or ""))
            if not path.is_file():
                return "pending EMPTY no_order_authority source_artifact missing"
            expected_hash = str(artifact.get("sha256") or "")
            if expected_hash and expected_hash != _file_hash(path):
                return "pending EMPTY no_order_authority source_artifact hash mismatch"
            artifact_business_date = _artifact_business_date(path)
            if artifact_business_date and artifact_business_date != business_date:
                return "pending EMPTY no_order_authority source_artifact business_date mismatch"
    return ""


def authority_hash(authority: Mapping[str, Any]) -> str:
    material = dict(authority)
    material.pop("authority_hash", None)
    return "sha256:" + hashlib.sha256(_json_dumps(material).encode("utf-8")).hexdigest()


def _source_artifacts(
    *,
    runtime_root: Path,
    business_date: str,
    sell_order_plan_path: Path,
    sell_approval_path: Path,
) -> list[dict[str, Any]]:
    artifacts = [
        _artifact("sell_order_plan", sell_order_plan_path, required=True),
        _artifact("sell_approval_artifact", sell_approval_path, required=True),
    ]
    strategy_order_plan = runtime_root / "runtime_state" / "strategy_planning" / business_date / "order_plan.json"
    strategy_approval = runtime_root / "runtime_state" / "strategy_planning" / business_date / "approval_artifact.json"
    if strategy_order_plan.is_file():
        artifacts.append(_artifact("strategy_no_order_plan", strategy_order_plan, required=True))
    if strategy_approval.is_file():
        artifacts.append(_artifact("strategy_no_order_approval", strategy_approval, required=True))
    return artifacts


def _artifact(role: str, path: Path, *, required: bool) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(path),
        "required": required,
        "exists": path.is_file(),
        "sha256": _file_hash(path),
    }


def _reason_codes(
    *,
    sell_reason: str,
    add_evidence: Mapping[str, Any] | None,
    source_artifacts: list[dict[str, Any]],
) -> list[str]:
    reasons = {"no_executable_order_items"}
    if str(sell_reason).startswith("NO_SIGNAL"):
        reasons.add("sell_no_signal")
    for artifact in source_artifacts:
        if artifact["role"] == "strategy_no_order_plan":
            reasons.add("strategy_no_order_authorized")
            if _strategy_capacity_satisfied(Path(str(artifact["path"]))):
                reasons.add("existing_position_capacity_satisfied")
    add = dict(add_evidence or {})
    if int(add.get("rejected_count") or 0) > 0:
        reasons.add("pm_add_rejected")
    for rejected in add.get("rejected") or []:
        if isinstance(rejected, Mapping) and str(rejected.get("rejected_reason") or rejected.get("capital_allocation_reason") or "") == "LOT_SIZE_NOT_VIABLE":
            reasons.add("pm_add_rejected_lot_size_not_viable")
    return sorted(reasons)


def _strategy_capacity_satisfied(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    lineage = payload.get("strategy_item_lineage")
    if not isinstance(lineage, list):
        return False
    return any(isinstance(item, Mapping) and str(item.get("planning_intent") or "") == "NO_ACTION" for item in lineage)


def _artifact_business_date(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, Mapping):
        return ""
    return str(payload.get("business_date") or "")


def _resolve_path(runtime_root: Path, raw_path: str) -> Path:
    if not raw_path:
        return Path("")
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    candidate = runtime_root / path
    if candidate.exists():
        return candidate
    return path


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
