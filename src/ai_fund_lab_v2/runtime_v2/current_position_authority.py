"""Current position authority resolution shared by Runtime feature consumers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


READY_STATUSES = {"READY", "VALID_CARRYOVER"}


def resolve_current_position_authority(
    *,
    runtime_root: Path | str | None,
    target_data_until: str,
    no_runtime_root_status: str = "READY_EMPTY",
) -> dict[str, Any]:
    if runtime_root is None:
        return _authority_payload(
            status=no_runtime_root_status,
            path="",
            payload={"positions": [], "current_state_confirmed_empty": True, "no_position": True},
            target_data_until=target_data_until,
            reason="position_feature_ready_no_runtime_root",
        )
    root = Path(runtime_root)
    runtime_state_path = root / "runtime_state" / "current_state.json"
    runtime_state = _read_json_or_empty(runtime_state_path) if runtime_state_path.is_file() else {}
    source = str(runtime_state.get("asset_state_source") or "persistent_ledger/state.json").strip() or "persistent_ledger/state.json"
    source_path = Path(source)
    current_path = source_path if source_path.is_absolute() else root / source_path
    if not current_path.is_file():
        return _authority_payload(
            status="MISSING",
            path=str(current_path),
            payload={},
            target_data_until=target_data_until,
            reason="current_authority_missing_asset_sot",
        )
    payload = _read_json_or_empty(current_path)
    if not payload:
        return _authority_payload(
            status="UNKNOWN",
            path=str(current_path),
            payload={},
            target_data_until=target_data_until,
            reason="current_authority_unreadable_asset_sot",
        )
    positions = payload.get("positions")
    if payload.get("current_positions_unknown") is True:
        return _authority_payload(
            status="UNKNOWN",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_positions_unknown",
        )
    if not isinstance(positions, list):
        return _authority_payload(
            status="UNKNOWN",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_positions_invalid_or_missing",
        )
    review_required = bool(payload.get("review_required"))
    if review_required:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_authority_review_required",
        )
    current_position_status = str(payload.get("current_position_status") or "")
    if current_position_status and current_position_status not in READY_STATUSES:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_position_status_not_ready",
        )
    temporal_status = str(payload.get("temporal_status") or "")
    if temporal_status and temporal_status not in READY_STATUSES:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_temporal_status_not_ready",
        )
    position_state_as_of = _position_state_as_of(payload)
    if position_state_as_of and position_state_as_of[:10] > target_data_until:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_position_state_as_of_after_feature_target_date",
        )
    if positions and payload.get("no_position") is True:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_position_metadata_conflict_non_empty_marked_no_position",
        )
    if positions and not position_state_as_of:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_position_state_as_of_missing",
        )
    if positions:
        return _authority_payload(
            status="READY",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="position_feature_ready",
        )
    if payload.get("no_position") is False and payload.get("current_state_confirmed_empty") is not True:
        return _authority_payload(
            status="REVIEW_REQUIRED",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_position_metadata_conflict_empty_not_marked_no_position",
        )
    if payload.get("no_position") is True or payload.get("current_state_confirmed_empty") is True:
        if not position_state_as_of:
            return _authority_payload(
                status="REVIEW_REQUIRED",
                path=str(current_path),
                payload=payload,
                target_data_until=target_data_until,
                reason="current_position_state_as_of_missing",
            )
        return _authority_payload(
            status="READY_EMPTY",
            path=str(current_path),
            payload=payload,
            target_data_until=target_data_until,
            reason="current_positions_confirmed_empty",
        )
    return _authority_payload(
        status="UNKNOWN",
        path=str(current_path),
        payload=payload,
        target_data_until=target_data_until,
        reason="current_positions_unknown",
    )


def _authority_payload(
    *,
    status: str,
    path: str,
    payload: dict[str, Any],
    target_data_until: str,
    reason: str,
) -> dict[str, Any]:
    positions = payload.get("positions") if isinstance(payload.get("positions"), list) else []
    position_state_as_of = _position_state_as_of(payload)
    no_fill_carry_used = bool(position_state_as_of and position_state_as_of[:10] < target_data_until)
    return {
        "status": status,
        "path": path,
        "payload": payload,
        "position_count": len(positions),
        "position_state_as_of": position_state_as_of[:10],
        "feature_target_date": target_data_until,
        "no_fill_carry_used": no_fill_carry_used,
        "reason": reason,
        "current_authority_status": status,
        "current_authority_path": path,
        "current_position_status": str(payload.get("current_position_status") or ""),
        "current_positions_unknown": bool(payload.get("current_positions_unknown")),
        "current_state_confirmed_empty": bool(payload.get("current_state_confirmed_empty")),
        "no_position": bool(payload.get("no_position")),
        "no_position_reason": str(payload.get("no_position_reason") or ""),
        "position_state_source": str(payload.get("position_state_source") or ""),
        "temporal_status": str(payload.get("temporal_status") or ""),
        "review_required": bool(payload.get("review_required")),
        "current_position_count": len(positions),
        "current_position_state_as_of": position_state_as_of[:10],
    }


def _position_state_as_of(payload: dict[str, Any]) -> str:
    return str(payload.get("position_state_as_of") or payload.get("business_date") or payload.get("as_of") or "")


def _read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
