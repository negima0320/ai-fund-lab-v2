"""Isolated Historical Runtime root materialization for Runtime tests."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


ISOLATED_ROOT_SCHEMA_VERSION = "phase19_bb_isolated_historical_runtime_root.v1"
DEFAULT_ACCEPTED_GENERATION_ID = "phase19_aq_accepted_generation_641e6e313543f013"


def materialize_isolated_historical_runtime_root(
    *,
    repo_root: Path,
    shared_runtime_root: Path,
    run_id: str,
    profile: dict[str, Any],
    target_business_date: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a clean Historical Runtime root without mutating shared state."""

    repo = Path(repo_root)
    shared = Path(shared_runtime_root)
    created = created_at or _utc_now()
    isolated_parent = shared / "runtime_tests" / run_id
    isolated_root = isolated_parent / ".runtime"
    isolated_root.mkdir(parents=True, exist_ok=True)

    for rel in (
        "persistent_ledger",
        "runtime_state",
        "pending_order_plan",
        "operations",
        "ai_lifecycle",
        "runtime_test",
    ):
        (isolated_root / rel).mkdir(parents=True, exist_ok=True)

    shared_pre_hashes = protected_shared_runtime_hashes(shared)
    cash = float((profile.get("initial_state") or {}).get("cash"))
    buying_power = float((profile.get("initial_state") or {}).get("buying_power", cash))
    pointer_result = _materialize_accepted_generation_pointer(
        repo_root=repo,
        shared_runtime_root=shared,
        isolated_runtime_root=isolated_root,
    )
    market_ref = _materialize_market_data_reference(shared_runtime_root=shared, isolated_runtime_root=isolated_root)
    model_ref = _materialize_training_output_reference(shared_runtime_root=shared, isolated_runtime_root=isolated_root)
    ledger = _ledger_payload(
        run_id=run_id,
        profile=profile,
        target_business_date=target_business_date,
        cash=cash,
        buying_power=buying_power,
        created_at=created,
    )
    _write_json(isolated_root / "persistent_ledger" / "state.json", ledger)
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (isolated_root / "persistent_ledger" / name).write_text("", encoding="utf-8")
    pending = {
        "schema_version": "runtime_v2_pending_slot_v1",
        "status": "EMPTY",
        "state": "EMPTY",
        "active_pending": False,
        "last_pending_plan_id": "",
        "last_terminal_state": "",
        "last_transition_at": target_business_date + "T00:00:00+09:00",
        "run_id": run_id,
        "profile_id": profile.get("profile_id", ""),
        "runtime_mode": profile.get("mode", ""),
    }
    _write_json(isolated_root / "pending_order_plan" / "pending_order_plan.json", pending)
    pm = {
        "schema_version": "runtime_v2_operation_state_v1",
        "runtime_mode": profile.get("mode", ""),
        "environment": profile.get("mode", ""),
        "profile_id": profile.get("profile_id", ""),
        "run_id": run_id,
        "state": "READY",
        "reason": "phase19_bb_clean_day1_initial_authority",
        "business_date": target_business_date,
        "generated_at": target_business_date + "T00:00:00+09:00",
        "updated_at": target_business_date + "T00:00:00+09:00",
        "asset_state_source": "persistent_ledger/state.json",
        "pending_state_source": "pending_order_plan/pending_order_plan.json",
        "production_equivalent": False,
        "asset_state_is_authoritative_here": False,
        "pending_state_is_authoritative_here": False,
    }
    _write_json(isolated_root / "runtime_state" / "current_state.json", pm)
    metadata = {
        "schema_version": ISOLATED_ROOT_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile.get("profile_id", ""),
        "target_business_date": target_business_date,
        "target_business_dates": sorted(str(day) for day in (profile.get("accepted_feature_dates") or {}).keys()),
        "isolated_runtime_root": str(isolated_root),
        "shared_runtime_root": str(shared),
        "created_at": created,
        "initial_state_authority": "A. isolated empty Historical state",
        "cash_authority": "config/runtime_tests/historical_smoke_5bd.json.initial_state.cash",
        "accepted_generation": pointer_result,
        "market_data_reference": market_ref,
        "training_output_reference": model_ref,
        "forbidden_copied_artifacts": [
            "shared Ledger Current",
            "shared Pending Plan",
            "shared PM State",
            "shared Safety latest",
            "shared Inference outputs",
            "shared Runtime Features",
            "shared Lifecycle Gate decision",
            "shared Execution state",
            "shared Approval state",
        ],
    }
    _write_json(isolated_root / "runtime_test" / "metadata.json", metadata)
    shared_post_hashes = protected_shared_runtime_hashes(shared)
    resolution = resolve_accepted_generation(isolated_root).to_dict()
    return {
        "schema_version": ISOLATED_ROOT_SCHEMA_VERSION,
        "status": "PASS" if shared_pre_hashes == shared_post_hashes and resolution.get("resolution_status") == "RESOLVED_COMMITTED" else "BLOCK",
        "run_id": run_id,
        "profile_id": profile.get("profile_id", ""),
        "target_business_date": target_business_date,
        "isolated_runtime_root": str(isolated_root),
        "shared_runtime_root": str(shared),
        "shared_runtime_pre_hashes": shared_pre_hashes,
        "shared_runtime_post_hashes": shared_post_hashes,
        "shared_runtime_non_mutation": shared_pre_hashes == shared_post_hashes,
        "historical_initial_state": ledger,
        "pending_initial_state": pending,
        "pm_initial_state": pm,
        "metadata": metadata,
        "accepted_generation_resolution": resolution,
        "day1_pre_run_absent_artifacts": day1_pre_run_absent_artifacts(isolated_root, target_business_date),
    }


def protected_shared_runtime_hashes(shared_runtime_root: Path) -> dict[str, Any]:
    root = Path(shared_runtime_root)
    targets = {
        "persistent_ledger_state": root / "persistent_ledger" / "state.json",
        "pending_order_plan": root / "pending_order_plan" / "pending_order_plan.json",
        "runtime_current_state": root / "runtime_state" / "current_state.json",
        "accepted_generation_pointer": root / "runtime_state" / "accepted_buy_ai_bundle.json",
    }
    return {name: _file_ref(path) for name, path in targets.items()}


def day1_pre_run_absent_artifacts(runtime_root: Path, target_business_date: str) -> dict[str, Any]:
    root = Path(runtime_root)
    targets = {
        "candidate_inference": root / "runtime_state" / "buy_ai" / target_business_date / "candidate_decisions.json",
        "opportunity_inference": root / "runtime_state" / "buy_ai" / target_business_date / "opportunity_rankings.json",
        "runtime_features": root / "operations" / "feature_artifacts" / target_business_date,
        "safety_decision": root / "runtime_state" / "safety" / "latest_safety_decision.json",
        "lifecycle_gate": root / "runtime_state" / "buy_ai" / target_business_date / "ai_lifecycle_gate_decision.json",
        "planning_result": root / "pending_order_plan" / "history" / target_business_date,
    }
    items = {name: {"path": str(path), "exists": path.exists()} for name, path in targets.items()}
    return {
        "status": "PASS" if not any(item["exists"] for item in items.values()) else "BLOCK",
        "target_business_date": target_business_date,
        "items": items,
    }


def _materialize_accepted_generation_pointer(
    *,
    repo_root: Path,
    shared_runtime_root: Path,
    isolated_runtime_root: Path,
) -> dict[str, Any]:
    source_pointer_path = shared_runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json"
    pointer = _read_json(source_pointer_path)
    generation_id = str(pointer.get("accepted_generation_id") or DEFAULT_ACCEPTED_GENERATION_ID)
    source_manifest_path = repo_root / ".runtime" / "ai_lifecycle" / "generations" / generation_id / "accepted_generation_manifest.json"
    manifest = _read_json(source_manifest_path)
    target_manifest_path = isolated_runtime_root / "ai_lifecycle" / "generations" / generation_id / "accepted_generation_manifest.json"
    target_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_manifest_path, target_manifest_path)
    target_pointer = dict(pointer)
    target_pointer["bundle_manifest_path"] = str(Path("ai_lifecycle") / "generations" / generation_id / "accepted_generation_manifest.json")
    target_pointer["accepted_generation_id"] = generation_id
    target_pointer["transaction_state"] = "COMMITTED"
    _write_json(isolated_runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json", target_pointer)
    return {
        "status": "PASS",
        "accepted_generation_id": generation_id,
        "source_pointer_path": str(source_pointer_path),
        "isolated_pointer_path": str(isolated_runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json"),
        "source_manifest_path": str(source_manifest_path),
        "isolated_manifest_path": str(target_manifest_path),
        "aggregate_hash": manifest.get("aggregate_hash", ""),
        "pointer_sha256": _sha256_file(isolated_runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json"),
        "manifest_sha256": _sha256_file(target_manifest_path),
    }


def _materialize_market_data_reference(*, shared_runtime_root: Path, isolated_runtime_root: Path) -> dict[str, Any]:
    source = shared_runtime_root / "operations" / "jquants"
    target = isolated_runtime_root / "operations" / "jquants"
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(os.path.relpath(source.resolve(strict=False), start=target.parent.resolve(strict=False)), target)
    return {
        "status": "PASS" if target.is_symlink() else "BLOCK",
        "reference_type": "symlink_read_only_reference",
        "source_path": str(source),
        "isolated_path": str(target),
        "copy_performed": False,
    }


def _materialize_training_output_reference(*, shared_runtime_root: Path, isolated_runtime_root: Path) -> dict[str, Any]:
    source = shared_runtime_root / "ai_lifecycle" / "training_outputs"
    target = isolated_runtime_root / "ai_lifecycle" / "training_outputs"
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(os.path.relpath(source.resolve(strict=False), start=target.parent.resolve(strict=False)), target)
    return {
        "status": "PASS" if target.is_symlink() else "BLOCK",
        "reference_type": "symlink_read_only_reference",
        "source_path": str(source),
        "isolated_path": str(target),
        "copy_performed": False,
    }


def _ledger_payload(
    *,
    run_id: str,
    profile: dict[str, Any],
    target_business_date: str,
    cash: float,
    buying_power: float,
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": "runtime_v2_current_temporal_v1",
        "asset_state_id": f"{run_id}-day1-initial-current",
        "environment": profile.get("mode", ""),
        "runtime_mode": profile.get("mode", ""),
        "profile_id": profile.get("profile_id", ""),
        "run_id": run_id,
        "source": "phase19_bb_isolated_empty_historical_state",
        "as_of": target_business_date + "T00:00:00+09:00",
        "business_date": target_business_date,
        "position_state_as_of": target_business_date,
        "positions": [],
        "cash": cash,
        "buying_power": buying_power,
        "market_value": 0.0,
        "total_equity": cash,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": True,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "cash_confirmed": True,
        "buying_power_confirmed": True,
        "generated_from": [],
        "created_at": created_at,
        "updated_at": created_at,
        "temporal_schema_version": "runtime_v2_current_temporal_v1",
        "temporal_status": "READY",
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
    }


def _file_ref(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": _sha256_file(path),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
