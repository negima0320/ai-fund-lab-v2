"""Apply Current projection metadata into Runtime State."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ai_fund_lab_v2.runtime_v2.current_state.authority import current_authority_metadata


@dataclass(frozen=True)
class CurrentApplyResult:
    status: str
    reason: str
    runtime_state_path: str
    current_path: str
    current_hash: str
    current_version: str
    execution_references: tuple[str, ...]
    runtime_state_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def apply_current_projection_to_runtime_state(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    current_path: Path | str | None = None,
    execution_references: Iterable[str] = (),
) -> CurrentApplyResult:
    """Record that the normal Current projection became the active Runtime State."""

    root = Path(runtime_root)
    current = Path(current_path) if current_path is not None else root / "persistent_ledger" / "state.json"
    state_path = root / "runtime_state" / "current_state.json"
    current_payload = _load_json(current)
    authority = current_authority_metadata(current_payload)
    current_hash = authority["current_hash"]
    current_version = authority["current_version"]
    current_updates = {
        "current_hash": current_hash,
        "current_version": current_version,
        "current_pointer": str(current),
    }
    if any(current_payload.get(key) != value for key, value in current_updates.items()):
        current_payload = {**current_payload, **current_updates}
        current.write_text(json.dumps(current_payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    execution_refs = tuple(str(ref) for ref in execution_references if ref)
    existing = _load_json(state_path) if state_path.exists() else {}
    if (
        str(existing.get("current_hash") or "") == current_hash
        and tuple(existing.get("execution_references") or ()) == execution_refs
        and str(existing.get("state") or "") == "CURRENT_APPLIED"
    ):
        return CurrentApplyResult(
            status="NOOP_ALREADY_APPLIED",
            reason="current projection already applied to runtime state",
            runtime_state_path=str(state_path),
            current_path=str(current),
            current_hash=current_hash,
            current_version=current_version,
            execution_references=execution_refs,
            runtime_state_version=str(existing.get("runtime_state_version") or ""),
        )

    payload = {
        **existing,
        "schema_version": "runtime_v2_current_apply_state_v1",
        "runtime_state_version": _runtime_state_version(
            business_date=business_date,
            mode=mode,
            current_hash=current_hash,
            execution_refs=execution_refs,
        ),
        "business_date": business_date,
        "runtime_mode": mode,
        "environment": mode,
        "job": "current_apply",
        "state": "CURRENT_APPLIED",
        "exit_code": 0,
        "current_pointer": str(current),
        "current_path": str(current),
        "current_version": current_version,
        "current_hash": current_hash,
        "current_timestamp": str(current_payload.get("updated_at") or current_payload.get("created_at") or business_date),
        "execution_references": list(execution_refs),
        "execution_reference": execution_refs[0] if execution_refs else "",
        "pending_consumed": True,
        "stage_statuses": [
            {"stage": "execution_normalization", "status": "PASS"},
            {"stage": "ledger_append", "status": "PASS"},
            {"stage": "current_projection", "status": "PASS"},
            {"stage": "current_apply", "status": "PASS"},
        ],
        "production_equivalent": bool(current_payload.get("production_equivalent", False)),
        "notification_sent": False,
        "updated_at": business_date,
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return CurrentApplyResult(
        status="APPLIED",
        reason="current projection applied to runtime state",
        runtime_state_path=str(state_path),
        current_path=str(current),
        current_hash=current_hash,
        current_version=current_version,
        execution_references=execution_refs,
        runtime_state_version=str(payload["runtime_state_version"]),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _runtime_state_version(
    *,
    business_date: str,
    mode: str,
    current_hash: str,
    execution_refs: tuple[str, ...],
) -> str:
    raw = json.dumps(
        {
            "business_date": business_date,
            "mode": mode,
            "current_hash": current_hash,
            "execution_refs": execution_refs,
        },
        sort_keys=True,
    )
    return "runtime-state-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
