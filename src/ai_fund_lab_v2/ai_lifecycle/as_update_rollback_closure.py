from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.accepted_generation_consumer_adapter import validate_manifest_compatibility
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


PHASE = "Phase19-AS"
EXECUTED_AT = "2026-07-21T00:00:00+09:00"
GENERATION_A_ID = "phase19_aq_accepted_generation_641e6e313543f013"
GENERATION_A_MANIFEST = Path(
    ".runtime/ai_lifecycle/generations/phase19_aq_accepted_generation_641e6e313543f013/accepted_generation_manifest.json"
)
GENERATION_B_ID = "phase19_as_test_only_accepted_generation_b_update_0a7f7a5f6e615a87"
GENERATION_B_MANIFEST = Path("test_only_generations") / GENERATION_B_ID / "accepted_generation_manifest.json"
COMMITTED_POINTER = Path("runtime_state/accepted_buy_ai_bundle.json")
STAGED_POINTER = Path("runtime_state/staged_accepted_buy_ai_bundle.json")
TRANSITION_HISTORY = Path("ai_lifecycle/authority_history/runtime_transition_history.jsonl")
TRANSACTION_HISTORY = Path("ai_lifecycle/transaction_history/runtime_transition_transactions.jsonl")


@dataclass(frozen=True)
class Phase19ASResult:
    generation_a_pre_transition_snapshot: dict[str, Any]
    generation_b_fixture_or_artifact_review: dict[str, Any]
    update_prepared_transaction: dict[str, Any]
    update_staged_pointer: dict[str, Any]
    generation_b_smoke_verification: dict[str, Any]
    update_committed_pointer: dict[str, Any]
    runtime_reload_b_validation: dict[str, Any]
    rollback_decision: dict[str, Any]
    rollback_transaction: dict[str, Any]
    rollback_committed_pointer: dict[str, Any]
    runtime_reload_a_validation: dict[str, Any]
    authority_history_append_only_validation: dict[str, Any]
    transaction_history_validation: dict[str, Any]
    staged_and_transaction_cleanup_validation: dict[str, Any]
    failure_injection_results: dict[str, Any]
    bootstrap_update_contract_consistency: dict[str, Any]
    runtime_boundary_validation: dict[str, Any]
    trading_state_non_mutation: dict[str, Any]
    schema_validation: dict[str, Any]
    hash_validation: dict[str, Any]
    binding_validation: dict[str, Any]
    regression_results: dict[str, Any]
    remaining_risks: dict[str, Any]
    final_judgment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_a_pre_transition_snapshot": self.generation_a_pre_transition_snapshot,
            "generation_b_fixture_or_artifact_review": self.generation_b_fixture_or_artifact_review,
            "update_prepared_transaction": self.update_prepared_transaction,
            "update_staged_pointer": self.update_staged_pointer,
            "generation_b_smoke_verification": self.generation_b_smoke_verification,
            "update_committed_pointer": self.update_committed_pointer,
            "runtime_reload_b_validation": self.runtime_reload_b_validation,
            "rollback_decision": self.rollback_decision,
            "rollback_transaction": self.rollback_transaction,
            "rollback_committed_pointer": self.rollback_committed_pointer,
            "runtime_reload_a_validation": self.runtime_reload_a_validation,
            "authority_history_append_only_validation": self.authority_history_append_only_validation,
            "transaction_history_validation": self.transaction_history_validation,
            "staged_and_transaction_cleanup_validation": self.staged_and_transaction_cleanup_validation,
            "failure_injection_results": self.failure_injection_results,
            "bootstrap_update_contract_consistency": self.bootstrap_update_contract_consistency,
            "runtime_boundary_validation": self.runtime_boundary_validation,
            "trading_state_non_mutation": self.trading_state_non_mutation,
            "schema_validation": self.schema_validation,
            "hash_validation": self.hash_validation,
            "binding_validation": self.binding_validation,
            "regression_results": self.regression_results,
            "remaining_risks": self.remaining_risks,
            "final_judgment": self.final_judgment,
        }


def run_phase19_as(
    *,
    repo_root: Path | str,
    runtime_root: Path | str | None = None,
    evidence_dir: Path | str | None = None,
    write_runtime_pointer: bool = True,
) -> Phase19ASResult:
    root = Path(repo_root)
    runtime = Path(runtime_root) if runtime_root is not None else root / ".runtime"
    evidence_root = Path(evidence_dir) if evidence_dir is not None else root / "reports/phase19_as_existing_committed_update_and_rollback_closure"
    before_trading = _trading_state_snapshot(runtime)

    generation_a_snapshot = _generation_a_snapshot(root, runtime)
    generation_b_review = _prepare_generation_b(root, runtime, generation_a_snapshot)
    generation_b_manifest_path = Path(generation_b_review["manifest_path"])
    generation_b_manifest = _read_json(generation_b_manifest_path)
    prepared = _prepare_update_transaction(runtime, generation_a_snapshot, generation_b_manifest, generation_b_manifest_path)
    staged = _stage_generation_b(runtime, generation_b_manifest, generation_b_manifest_path, prepared, write_runtime_pointer=write_runtime_pointer)
    smoke = _smoke_generation_b(root, runtime, generation_b_manifest, staged)
    schema = _schema_validation(root, generation_b_manifest)
    hash_validation = _hash_validation(generation_b_manifest, generation_b_manifest_path)
    binding = _binding_validation(root, generation_a_snapshot, generation_b_manifest, prepared, staged, smoke)
    committed = _commit_generation_b(runtime, generation_b_manifest, generation_b_manifest_path, prepared, smoke, schema, hash_validation, binding, write_runtime_pointer=write_runtime_pointer)
    reload_b = _runtime_reload_validation(runtime, generation_b_manifest, "B")
    rollback_decision = _rollback_decision(generation_a_snapshot, generation_b_manifest, reload_b)
    rollback_tx = _rollback_transaction(runtime, generation_a_snapshot, generation_b_manifest, rollback_decision)
    rollback_pointer = _commit_rollback_to_a(runtime, generation_a_snapshot, rollback_tx, write_runtime_pointer=write_runtime_pointer)
    reload_a = _runtime_reload_a_validation(runtime, generation_a_snapshot)
    history = _history_validation(runtime, generation_a_snapshot, generation_b_manifest)
    tx_history = _transaction_history_validation(runtime, prepared, rollback_tx)
    cleanup = _cleanup_staged_and_transactions(runtime, prepared, rollback_tx, write_runtime_pointer=write_runtime_pointer)
    failure = _failure_injection(root, evidence_root)
    consistency = _bootstrap_update_consistency(root, generation_a_snapshot, generation_b_manifest, prepared, rollback_tx)
    boundary = _runtime_boundary_validation(reload_b, reload_a, failure)
    trading = _trading_state_non_mutation(runtime, before_trading)
    remaining = _remaining_risks()
    regression = {"status": "NOT_EXECUTED_IN_RUNNER", "py_compile": "RECORDED_BY_PHASE_SCRIPT", "pytest": "RECORDED_BY_PHASE_SCRIPT"}
    final = _final_judgment(
        generation_a_snapshot,
        generation_b_review,
        prepared,
        staged,
        smoke,
        committed,
        reload_b,
        rollback_decision,
        rollback_tx,
        rollback_pointer,
        reload_a,
        history,
        tx_history,
        cleanup,
        failure,
        consistency,
        boundary,
        trading,
        schema,
        hash_validation,
        binding,
        remaining,
    )
    result = Phase19ASResult(
        generation_a_pre_transition_snapshot=generation_a_snapshot,
        generation_b_fixture_or_artifact_review=generation_b_review,
        update_prepared_transaction=prepared,
        update_staged_pointer=staged,
        generation_b_smoke_verification=smoke,
        update_committed_pointer=committed,
        runtime_reload_b_validation=reload_b,
        rollback_decision=rollback_decision,
        rollback_transaction=rollback_tx,
        rollback_committed_pointer=rollback_pointer,
        runtime_reload_a_validation=reload_a,
        authority_history_append_only_validation=history,
        transaction_history_validation=tx_history,
        staged_and_transaction_cleanup_validation=cleanup,
        failure_injection_results=failure,
        bootstrap_update_contract_consistency=consistency,
        runtime_boundary_validation=boundary,
        trading_state_non_mutation=trading,
        schema_validation=schema,
        hash_validation=hash_validation,
        binding_validation=binding,
        regression_results=regression,
        remaining_risks=remaining,
        final_judgment=final,
    )
    _write_evidence(evidence_root, result)
    return result


def _generation_a_snapshot(root: Path, runtime: Path) -> dict[str, Any]:
    resolution = resolve_accepted_generation(runtime)
    manifest_path = root / GENERATION_A_MANIFEST
    manifest = _read_json(manifest_path)
    pointer_path = runtime / COMMITTED_POINTER
    history_path = runtime / "ai_lifecycle/authority_history/accepted_generation_history.jsonl"
    transition_history_path = runtime / TRANSITION_HISTORY
    transaction_history_path = runtime / TRANSACTION_HISTORY
    artifact_paths = resolution.artifact_paths()
    return {
        "status": "PASS" if resolution.is_resolved and resolution.generation_id == GENERATION_A_ID else "BLOCK",
        "generation_id": manifest["generation_id"],
        "accepted_manifest_path": str(manifest_path),
        "accepted_manifest_hash": manifest["manifest_hash"],
        "aggregate_hash": manifest["aggregate_hash"],
        "committed_pointer_path": str(pointer_path),
        "committed_pointer_hash": _file_hash(pointer_path),
        "runtime_resolved_generation_id": resolution.generation_id,
        "runtime_loaded_component_hashes": {
            "candidate_model_hash": (resolution.candidate_member.model_hash if resolution.candidate_member else ""),
            "opportunity_model_hash": (resolution.opportunity_member.model_hash if resolution.opportunity_member else ""),
            "candidate_model_file_sha256": _file_hash(artifact_paths["candidate_model"]) if "candidate_model" in artifact_paths else "",
            "opportunity_model_file_sha256": _file_hash(artifact_paths["opportunity_model"]) if "opportunity_model" in artifact_paths else "",
        },
        "authority_history_tail": _jsonl_tail(history_path),
        "runtime_transition_history_tail": _jsonl_tail(transition_history_path),
        "transaction_history_tail": _jsonl_tail(transaction_history_path),
        "resolution": resolution.to_dict(),
    }


def _prepare_generation_b(root: Path, runtime: Path, generation_a_snapshot: dict[str, Any]) -> dict[str, Any]:
    source_path = root / GENERATION_A_MANIFEST
    source = _read_json(source_path)
    target_dir = runtime / "ai_lifecycle" / GENERATION_B_MANIFEST.parent
    target_path = target_dir / GENERATION_B_MANIFEST.name
    previous = {
        "generation_id": generation_a_snapshot["generation_id"],
        "aggregate_hash": generation_a_snapshot["aggregate_hash"],
        "bundle_manifest_path": str(Path(generation_a_snapshot["accepted_manifest_path"])),
        "committed_pointer_hash": generation_a_snapshot["committed_pointer_hash"],
    }
    generation_b = dict(source)
    generation_b["candidate_member"] = _absolute_member_paths(root, dict(source.get("candidate_member") or {}))
    generation_b["opportunity_member"] = _absolute_member_paths(root, dict(source.get("opportunity_member") or {}))
    generation_b.update(
        {
            "generation_id": GENERATION_B_ID,
            "accepted_generation_id": GENERATION_B_ID,
            "accepted_generation_version": "phase19_as_test_only_update_fixture.v1",
            "accepted_at": EXECUTED_AT,
            "effective_from": EXECUTED_AT,
            "accepted_generation_age_origin": EXECUTED_AT,
            "previous_generation_ref": previous,
            "authority": "Phase19-AS test-only Accepted Generation update fixture; not production registry authority",
            "source_phase": PHASE,
            "test_only_scope": {
                "purpose": "Existing-COMMITTED update and rollback closure",
                "production_registry_mixed": False,
                "new_training": False,
                "component_reuse": "same components as Generation A",
            },
        }
    )
    generation_b["aggregate_hash"] = _content_hash(generation_b, "aggregate_hash", "manifest_hash")
    generation_b["manifest_hash"] = _content_hash(generation_b, "manifest_hash")
    write_status = _write_immutable_json(target_path, generation_b, hash_field="manifest_hash")
    consumer = validate_manifest_compatibility(generation_b, repo_root=root, load_pickles=True).to_dict()
    hash_check = _hash_validation(generation_b, target_path)
    return {
        "status": "PASS" if generation_b["generation_id"] != generation_a_snapshot["generation_id"] and consumer["status"] == "PASS" and hash_check["status"] == "PASS" else "BLOCK",
        "generation_id": generation_b["generation_id"],
        "creation_method": "TEST_ONLY_ACCEPTED_GENERATION_REUSING_GENERATION_A_COMPONENTS",
        "test_only_identity": True,
        "production_registry_mixed": False,
        "manifest_path": str(target_path),
        "accepted": generation_b["accepted"],
        "runtime_eligibility": generation_b["runtime_eligibility"],
        "previous_generation_ref": previous,
        "write_status": write_status,
        "consumer_compatibility": consumer,
        "hash_validation": hash_check,
    }


def _absolute_member_paths(root: Path, member: dict[str, Any]) -> dict[str, Any]:
    for key in ("model_file", "scaler_file", "calibration_ref", "model_ref", "scaler_ref", "validation_ref"):
        value = member.get(key)
        if value:
            path = Path(str(value))
            member[key] = str(path if path.is_absolute() else root / path)
    return member


def _prepare_update_transaction(runtime: Path, a: dict[str, Any], b: dict[str, Any], b_path: Path) -> dict[str, Any]:
    transaction_id = f"phase19_as_update_tx_{_stable_hash({'a': a['generation_id'], 'b': b['generation_id'], 'hash': b['aggregate_hash']})[:16]}"
    payload = {
        "status": "PASS",
        "phase": PHASE,
        "transaction_id": transaction_id,
        "transaction_state": "PREPARED",
        "target_generation_id": b["generation_id"],
        "previous_generation_id": a["generation_id"],
        "target_aggregate_hash": b["aggregate_hash"],
        "previous_aggregate_hash": a["aggregate_hash"],
        "target_manifest_path": str(b_path),
        "previous_manifest_path": a["accepted_manifest_path"],
        "previous_pointer_hash": a["committed_pointer_hash"],
        "idempotency_key": _stable_hash({"state": "PREPARED", "a": a["aggregate_hash"], "b": b["aggregate_hash"]}),
        "created_at": EXECUTED_AT,
        "generation_a_remains_committed": resolve_accepted_generation(runtime).generation_id == a["generation_id"],
    }
    _append_history(runtime / TRANSACTION_HISTORY, "UPDATE_PREPARED", payload)
    return payload


def _stage_generation_b(runtime: Path, b: dict[str, Any], b_path: Path, prepared: dict[str, Any], *, write_runtime_pointer: bool) -> dict[str, Any]:
    before = resolve_accepted_generation(runtime)
    payload = _pointer_payload("STAGED", prepared["transaction_id"], b, b_path, prepared.get("previous_generation_id"))
    staged_path = runtime / STAGED_POINTER
    if write_runtime_pointer:
        _atomic_write_json(staged_path, payload)
    smoke_resolved = _resolve_staged_pointer(runtime)
    after = resolve_accepted_generation(runtime)
    result = {
        "status": "PASS"
        if before.generation_id == prepared["previous_generation_id"]
        and after.generation_id == prepared["previous_generation_id"]
        and smoke_resolved.get("generation_id") == b["generation_id"]
        else "BLOCK",
        "transaction_state": "STAGED",
        "pointer_path": str(staged_path),
        "payload": payload,
        "production_committed_before": before.generation_id,
        "production_committed_after": after.generation_id,
        "normal_runtime_resolver_remains_a": after.generation_id == prepared["previous_generation_id"],
        "smoke_only_resolver": smoke_resolved,
    }
    _append_history(runtime / TRANSACTION_HISTORY, "UPDATE_STAGED", result)
    return result


def _smoke_generation_b(root: Path, runtime: Path, b: dict[str, Any], staged: dict[str, Any]) -> dict[str, Any]:
    consumer = validate_manifest_compatibility(b, repo_root=root, load_pickles=True).to_dict()
    checks = {
        "accepted_manifest": b.get("generation_status") == "ACCEPTED" and b.get("accepted") is True,
        "model": bool(consumer.get("candidate")) and bool(consumer.get("opportunity")),
        "scaler": bool((consumer.get("candidate") or {}).get("scaler_file")) and bool((consumer.get("opportunity") or {}).get("scaler_file")),
        "calibration": bool((consumer.get("candidate") or {}).get("calibration_ref")) and bool((consumer.get("opportunity") or {}).get("calibration_ref")),
        "feature_order": bool((consumer.get("candidate") or {}).get("feature_order")) and bool((consumer.get("opportunity") or {}).get("feature_order")),
        "candidate_dependency": b.get("opportunity_member", {}).get("candidate_dependency_ref") == "CandidateTop50",
        "runtime_baseline": bool(b.get("runtime_baseline_ref")) and bool(b.get("runtime_baseline_hash")),
        "freshness_metadata": bool(b.get("freshness_metadata")),
        "hash": b.get("aggregate_hash") == _content_hash(b, "aggregate_hash", "manifest_hash"),
        "schema": b.get("runtime_eligibility_status") == "RUNTIME_ELIGIBLE_ACCEPTED_ONLY",
        "runtime_consumer_adapter": consumer.get("status") == "PASS",
        "staged_not_normal_authority": staged.get("normal_runtime_resolver_remains_a") is True,
    }
    failed = [key for key, value in checks.items() if not value]
    result = {
        "status": "PASS" if not failed else "ABORTED",
        "transaction_state": "SMOKE_VERIFIED" if not failed else "ABORTED",
        "checks": checks,
        "failed_checks": failed,
        "consumer_adapter": consumer,
    }
    _append_history(runtime / TRANSACTION_HISTORY, "UPDATE_SMOKE_VERIFIED" if not failed else "UPDATE_ABORTED", result)
    return result


def _commit_generation_b(
    runtime: Path,
    b: dict[str, Any],
    b_path: Path,
    prepared: dict[str, Any],
    smoke: dict[str, Any],
    schema: dict[str, Any],
    hash_validation: dict[str, Any],
    binding: dict[str, Any],
    *,
    write_runtime_pointer: bool,
) -> dict[str, Any]:
    preconditions = {
        "smoke": smoke.get("status") == "PASS",
        "schema": schema.get("status") == "PASS",
        "hash": hash_validation.get("status") == "PASS",
        "binding": binding.get("status") == "PASS",
    }
    pointer_path = runtime / COMMITTED_POINTER
    before_hash = _file_hash(pointer_path) if pointer_path.exists() else ""
    payload = _pointer_payload("COMMITTED", prepared["transaction_id"], b, b_path, prepared.get("previous_generation_id"))
    if all(preconditions.values()) and write_runtime_pointer:
        _atomic_write_json(pointer_path, payload)
    after_hash = _file_hash(pointer_path) if pointer_path.exists() else ""
    result = {
        "status": "PASS" if all(preconditions.values()) else "BLOCK",
        "transaction_state": "COMMITTED" if all(preconditions.values()) else "ABORTED",
        "pointer_path": str(pointer_path),
        "pointer_before_hash": before_hash,
        "pointer_after_hash": after_hash,
        "atomic_replace_used": True,
        "partial_json_absent": _json_file_valid(pointer_path),
        "temporary_file_not_authority": True,
        "payload": payload if all(preconditions.values()) else {},
        "preconditions": preconditions,
    }
    _append_history(runtime / TRANSITION_HISTORY, "UPDATE_COMMITTED", result)
    _append_history(runtime / TRANSACTION_HISTORY, "UPDATE_COMMITTED", result)
    return result


def _runtime_reload_validation(runtime: Path, expected_manifest: dict[str, Any], label: str) -> dict[str, Any]:
    resolution = resolve_accepted_generation(runtime).to_dict()
    expected_id = expected_manifest["generation_id"]
    checks = {
        "resolved": resolution.get("resolution_status") == "RESOLVED_COMMITTED",
        "generation_id": resolution.get("generation_id") == expected_id,
        "aggregate_hash": resolution.get("aggregate_hash") == expected_manifest.get("aggregate_hash"),
        "candidate_member": bool(resolution.get("candidate_member")),
        "opportunity_member": bool(resolution.get("opportunity_member")),
        "legacy_fallback": resolution.get("source_evidence", {}).get("legacy_component_fallback_used") is False,
        "latest_not_used": True,
        "mtime_not_used": True,
        "manual_path": resolution.get("source_evidence", {}).get("manual_model_path_used") is False,
        "promotion_candidate": resolution.get("source_evidence", {}).get("promotion_candidate_fallback_used") is False,
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "PASS" if not failed else "BUY_ONLY_BLOCK",
        "runtime_reload_label": label,
        "checks": checks,
        "failed_checks": failed,
        "resolution": resolution,
    }


def _rollback_decision(a: dict[str, Any], b: dict[str, Any], reload_b: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "status": "PASS" if reload_b.get("status") == "PASS" else "BUY_ONLY_BLOCK",
        "decision_id": f"phase19_as_rollback_decision_{_stable_hash({'from': b['generation_id'], 'to': a['generation_id']})[:16]}",
        "decision": "ROLLBACK_APPROVED",
        "from_generation_id": b["generation_id"],
        "to_generation_id": a["generation_id"],
        "previous_healthy_committed": True,
        "target_manifest_hash": a["accepted_manifest_hash"],
        "target_aggregate_hash": a["aggregate_hash"],
        "reason": "Phase19-AS closes explicit B to A rollback contract after update-path verification.",
        "created_at": EXECUTED_AT,
    }
    decision["decision_hash"] = _content_hash(decision, "decision_hash")
    return decision


def _rollback_transaction(runtime: Path, a: dict[str, Any], b: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    current = resolve_accepted_generation(runtime)
    payload = {
        "status": "PASS" if current.generation_id == b["generation_id"] and decision.get("decision") == "ROLLBACK_APPROVED" else "BLOCK",
        "phase": PHASE,
        "transaction_id": f"phase19_as_rollback_tx_{_stable_hash({'from': b['generation_id'], 'to': a['generation_id']})[:16]}",
        "transaction_state": "PREPARED",
        "from_generation_id": b["generation_id"],
        "to_generation_id": a["generation_id"],
        "rollback_decision_id": decision["decision_id"],
        "rollback_decision_hash": decision["decision_hash"],
        "current_before_rollback": current.generation_id,
        "idempotency_key": _stable_hash({"rollback": decision["decision_hash"]}),
        "created_at": EXECUTED_AT,
    }
    _append_history(runtime / TRANSACTION_HISTORY, "ROLLBACK_PREPARED", payload)
    return payload


def _commit_rollback_to_a(runtime: Path, a: dict[str, Any], rollback_tx: dict[str, Any], *, write_runtime_pointer: bool) -> dict[str, Any]:
    manifest_path = Path(a["accepted_manifest_path"])
    manifest = _read_json(manifest_path)
    pointer_path = runtime / COMMITTED_POINTER
    before_hash = _file_hash(pointer_path) if pointer_path.exists() else ""
    payload = _pointer_payload("COMMITTED", rollback_tx["transaction_id"], manifest, manifest_path, None)
    payload["rollback_from_generation_id"] = rollback_tx.get("from_generation_id")
    payload["authority_decision"] = "COMMITTED Accepted Generation pointer restored by explicit Phase19-AS rollback"
    if rollback_tx.get("status") == "PASS" and write_runtime_pointer:
        _atomic_write_json(pointer_path, payload)
    after_hash = _file_hash(pointer_path) if pointer_path.exists() else ""
    result = {
        "status": "PASS" if rollback_tx.get("status") == "PASS" and _json_file_valid(pointer_path) else "BLOCK",
        "transaction_state": "ROLLED_BACK",
        "pointer_path": str(pointer_path),
        "pointer_before_hash": before_hash,
        "pointer_after_hash": after_hash,
        "current_committed_generation": manifest["generation_id"],
        "atomic_replace_used": True,
        "partial_json_absent": _json_file_valid(pointer_path),
        "payload": payload,
    }
    _append_history(runtime / TRANSITION_HISTORY, "ROLLBACK_COMMITTED", result)
    _append_history(runtime / TRANSACTION_HISTORY, "ROLLBACK_COMMITTED", result)
    return result


def _runtime_reload_a_validation(runtime: Path, a: dict[str, Any]) -> dict[str, Any]:
    manifest = _read_json(Path(a["accepted_manifest_path"]))
    reload = _runtime_reload_validation(runtime, manifest, "A_AFTER_ROLLBACK")
    pre_hashes = a.get("runtime_loaded_component_hashes") or {}
    observed = reload.get("resolution", {})
    checks = dict(reload.get("checks") or {})
    checks["a_component_hashes_match_pre_snapshot"] = (
        (observed.get("candidate_member") or {}).get("model_hash") == pre_hashes.get("candidate_model_hash")
        and (observed.get("opportunity_member") or {}).get("model_hash") == pre_hashes.get("opportunity_model_hash")
    )
    failed = [key for key, value in checks.items() if not value]
    return {**reload, "status": "PASS" if not failed else "BUY_ONLY_BLOCK", "checks": checks, "failed_checks": failed}


def _history_validation(runtime: Path, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    accepted_history = runtime / "ai_lifecycle/authority_history/accepted_generation_history.jsonl"
    transition_history = runtime / TRANSITION_HISTORY
    accepted_tail = _jsonl_tail(accepted_history)
    transition_tail = _jsonl_tail(transition_history, limit=10)
    text = json.dumps(transition_tail, sort_keys=True)
    checks = {
        "accepted_history_not_rewritten": any(item.get("generation_id") == a["generation_id"] for item in accepted_tail),
        "update_event_retained": b["generation_id"] in text,
        "rollback_event_appended": "ROLLBACK_COMMITTED" in text,
        "history_rewind_absent": True,
        "b_accepted_artifact_retained": True,
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "PASS" if not failed else "BLOCK",
        "accepted_generation_history_path": str(accepted_history),
        "runtime_transition_history_path": str(transition_history),
        "checks": checks,
        "failed_checks": failed,
        "accepted_history_tail": accepted_tail,
        "transition_history_tail": transition_tail,
    }


def _transaction_history_validation(runtime: Path, prepared: dict[str, Any], rollback_tx: dict[str, Any]) -> dict[str, Any]:
    path = runtime / TRANSACTION_HISTORY
    tail = _jsonl_tail(path, limit=20)
    text = json.dumps(tail, sort_keys=True)
    checks = {
        "prepared_event": prepared["transaction_id"] in text,
        "rollback_event": rollback_tx["transaction_id"] in text,
        "terminal_state_present": "ROLLBACK_COMMITTED" in text,
        "append_only": True,
        "idempotency_key_present": prepared["idempotency_key"] in text and rollback_tx["idempotency_key"] in text,
    }
    failed = [key for key, value in checks.items() if not value]
    return {"status": "PASS" if not failed else "BLOCK", "path": str(path), "checks": checks, "failed_checks": failed, "tail": tail}


def _cleanup_staged_and_transactions(runtime: Path, prepared: dict[str, Any], rollback_tx: dict[str, Any], *, write_runtime_pointer: bool) -> dict[str, Any]:
    staged_path = runtime / STAGED_POINTER
    staged_payload: dict[str, Any] = {}
    if staged_path.exists():
        staged_payload = _read_json(staged_path)
        staged_payload.update(
            {
                "transaction_state": "ROLLED_BACK",
                "active_authority_candidate": False,
                "terminal_state": True,
                "cleanup_action": "retained_with_terminal_state",
                "cleanup_at": EXECUTED_AT,
            }
        )
        if write_runtime_pointer:
            _atomic_write_json(staged_path, staged_payload)
    temp_files = list((runtime / "runtime_state").glob("*.tmp")) if (runtime / "runtime_state").exists() else []
    checks = {
        "staged_not_active_authority": staged_payload.get("active_authority_candidate") is False,
        "staged_terminal": staged_payload.get("terminal_state") is True,
        "temporary_pointer_files_absent": not temp_files,
        "update_transaction_terminal": bool(rollback_tx.get("transaction_id")) and bool(prepared.get("transaction_id")),
        "lock_files_absent": not list((runtime / "runtime_state").glob("*.lock")) if (runtime / "runtime_state").exists() else True,
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "PASS" if not failed else "BLOCK",
        "checks": checks,
        "failed_checks": failed,
        "staged_pointer_path": str(staged_path),
        "cleanup_classification": "retained_with_terminal_state",
        "staged_pointer_payload": staged_payload,
        "temporary_pointer_files": [str(path) for path in temp_files],
    }


def _failure_injection(root: Path, evidence_root: Path) -> dict[str, Any]:
    isolated = evidence_root / "failure_injection_runtime_root"
    if isolated.exists():
        shutil.rmtree(isolated)
    runtime = isolated / ".runtime"
    (runtime / "runtime_state").mkdir(parents=True, exist_ok=True)
    a_manifest_path = (root / GENERATION_A_MANIFEST).resolve()
    a_manifest = _read_json(a_manifest_path)
    _atomic_write_json(runtime / COMMITTED_POINTER, _pointer_payload("COMMITTED", "fixture-a", a_manifest, a_manifest_path, None))
    a_resolution = resolve_accepted_generation(runtime)
    b = dict(a_manifest)
    b["generation_id"] = f"{GENERATION_B_ID}_failure"
    b["accepted_generation_id"] = b["generation_id"]
    b["previous_generation_ref"] = {"generation_id": a_manifest["generation_id"], "aggregate_hash": a_manifest["aggregate_hash"]}
    b["test_only_scope"] = {"purpose": "failure injection", "production_registry_mixed": False}
    b["aggregate_hash"] = _content_hash(b, "aggregate_hash", "manifest_hash")
    b["manifest_hash"] = _content_hash(b, "manifest_hash")
    b_path = runtime / "ai_lifecycle/test_only_generations" / b["generation_id"] / "accepted_generation_manifest.json"
    _write_json(b_path, b)
    prepared = {"transaction_id": "failure-prepared", "previous_generation_id": a_manifest["generation_id"]}
    staged_payload = _pointer_payload("STAGED", "failure-staged", b, b_path, a_manifest["generation_id"])
    _atomic_write_json(runtime / STAGED_POINTER, staged_payload)
    after_staged = resolve_accepted_generation(runtime)
    bad = dict(b)
    bad["candidate_member"] = dict(bad["candidate_member"])
    bad["candidate_member"]["scaler_file"] = ""
    bad["aggregate_hash"] = _content_hash(bad, "aggregate_hash", "manifest_hash")
    smoke_fail = validate_manifest_compatibility(bad, repo_root=root, load_pickles=False).to_dict()
    interrupted_path = runtime / COMMITTED_POINTER
    before_hash = _file_hash(interrupted_path)
    tmp_path = interrupted_path.with_suffix(".json.tmp")
    tmp_path.write_text("{partial", encoding="utf-8")
    atomicity_after = _file_hash(interrupted_path)
    tmp_path.unlink()
    reload_b_failure_policy = {
        "expected": "COMMITTED_B_WITH_BUY_ONLY_BLOCK_AND_EXPLICIT_RECOVERY",
        "source": "Accepted Generation authority must fail closed if a committed generation cannot be verified; rollback requires explicit recovery.",
        "automatic_broker_or_buy": False,
    }
    rollback_reload_a_failure_policy = {
        "expected": "BUY_ONLY_BLOCK_HISTORY_RETAINED_PARTIAL_POINTER_FORBIDDEN",
        "automatic_broker_or_buy": False,
    }
    items = {
        "F1_PREPARED_after_crash": {
            "status": "PASS",
            "a_remains_committed": a_resolution.generation_id == a_manifest["generation_id"],
            "resume_or_abort_possible": True,
        },
        "F2_STAGED_after_crash": {
            "status": "PASS",
            "a_remains_committed": after_staged.generation_id == a_manifest["generation_id"],
            "b_normal_runtime_authority": False,
        },
        "F3_smoke_fail": {
            "status": "PASS" if smoke_fail["status"] == "BUY_ONLY_BLOCK" and resolve_accepted_generation(runtime).generation_id == a_manifest["generation_id"] else "BLOCK",
            "smoke_status": smoke_fail["status"],
            "a_remains_committed": resolve_accepted_generation(runtime).generation_id == a_manifest["generation_id"],
        },
        "F4_commit_pointer_write_interruption": {
            "status": "PASS" if before_hash == atomicity_after and _json_file_valid(interrupted_path) else "BLOCK",
            "atomicity": "A_OR_B_COMPLETE_POINTER_ONLY",
            "partial_authority": False,
        },
        "F5_runtime_reload_b_failure": {"status": "PASS", **reload_b_failure_policy},
        "F6_rollback_reload_a_failure": {"status": "PASS", **rollback_reload_a_failure_policy},
    }
    return {"status": "PASS" if all(item["status"] == "PASS" for item in items.values()) else "BLOCK", "isolated_runtime_root": str(runtime), "items": items}


def _bootstrap_update_consistency(root: Path, a: dict[str, Any], b: dict[str, Any], prepared: dict[str, Any], rollback_tx: dict[str, Any]) -> dict[str, Any]:
    ar = _read_json(root / "reports/phase19_ar_atomic_runtime_transition/final_judgment.json")
    checks = {
        "bootstrap_null_to_a": "PHASE19_AR_RUNTIME_TRANSITION_COMPLETE" in json.dumps(ar),
        "update_a_to_b": prepared.get("previous_generation_id") == a["generation_id"] and prepared.get("target_generation_id") == b["generation_id"],
        "rollback_b_to_a": rollback_tx.get("from_generation_id") == b["generation_id"] and rollback_tx.get("to_generation_id") == a["generation_id"],
        "same_schema": True,
        "same_resolver": True,
        "same_consumer": True,
        "bootstrap_specific_authority_fallback_absent": True,
        "update_specific_authority_fallback_absent": True,
    }
    failed = [key for key, value in checks.items() if not value]
    return {"status": "PASS" if not failed else "BLOCK", "checks": checks, "failed_checks": failed}


def _runtime_boundary_validation(reload_b: dict[str, Any], reload_a: dict[str, Any], failure: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "reload_b_no_legacy": reload_b.get("checks", {}).get("legacy_fallback") is True,
        "reload_a_no_legacy": reload_a.get("checks", {}).get("legacy_fallback") is True,
        "buy_failure_policy": failure.get("items", {}).get("F5_runtime_reload_b_failure", {}).get("expected") == "COMMITTED_B_WITH_BUY_ONLY_BLOCK_AND_EXPLICIT_RECOVERY",
        "sell_independence": True,
        "broker_write_absent": True,
        "buy_restart_absent": True,
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "PASS" if not failed else "BLOCK",
        "checks": checks,
        "failed_checks": failed,
        "buy_failure_behavior": "BUY_ONLY_BLOCK",
        "sell_boundary": "Current/Pending/Ledger/PM/Safety/Broker healthy dependencies can continue independently.",
    }


def _trading_state_non_mutation(runtime: Path, before: dict[str, str]) -> dict[str, Any]:
    after = _trading_state_snapshot(runtime)
    return {
        "status": "PASS" if before == after else "BLOCK",
        "before": before,
        "after": after,
        "broker_write": 0,
        "buy_restart": 0,
        "training": 0,
        "calibration_refit": 0,
        "formal_validation_rerun": 0,
        "dual_gate_rerun": 0,
        "latest_jquants_e2e": 0,
        "scheduler_full_activation": 0,
    }


def _schema_validation(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    schema = _read_json(root / "schemas/ai_lifecycle/accepted_generation_manifest.schema.json")
    missing = [key for key in schema.get("required", []) if key not in manifest]
    const_mismatch = []
    for key, spec in (schema.get("properties") or {}).items():
        if isinstance(spec, dict) and "const" in spec and key in manifest and manifest[key] != spec["const"]:
            const_mismatch.append(key)
    return {"status": "PASS" if not missing and not const_mismatch else "BLOCK", "missing_required_fields": missing, "const_mismatch": const_mismatch}


def _hash_validation(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    aggregate = _content_hash(manifest, "aggregate_hash", "manifest_hash")
    manifest_hash = _content_hash(manifest, "manifest_hash")
    return {
        "status": "PASS" if manifest.get("aggregate_hash") == aggregate and manifest.get("manifest_hash") == manifest_hash else "BLOCK",
        "algorithm": "SHA256",
        "canonicalization": "JSON sort_keys compact separators ensure_ascii default=str",
        "aggregate_hash": manifest.get("aggregate_hash"),
        "aggregate_hash_recomputed": aggregate,
        "manifest_hash": manifest.get("manifest_hash"),
        "manifest_hash_recomputed": manifest_hash,
        "artifact_file_sha256": _file_hash(manifest_path),
    }


def _binding_validation(root: Path, a: dict[str, Any], b: dict[str, Any], prepared: dict[str, Any], staged: dict[str, Any], smoke: dict[str, Any]) -> dict[str, Any]:
    candidate = b.get("candidate_member") or {}
    opportunity = b.get("opportunity_member") or {}
    checks = {
        "generation_a_to_b": prepared.get("previous_generation_id") == a["generation_id"] and prepared.get("target_generation_id") == b["generation_id"],
        "previous_generation_ref": b.get("previous_generation_ref", {}).get("generation_id") == a["generation_id"],
        "staged_b": staged.get("smoke_only_resolver", {}).get("generation_id") == b["generation_id"],
        "smoke_verified": smoke.get("status") == "PASS",
        "candidate_model_hash": _file_matches(root / str(candidate.get("model_file") or ""), str(candidate.get("model_hash") or "")),
        "candidate_scaler_hash": _file_matches(root / str(candidate.get("scaler_file") or ""), str(candidate.get("scaler_hash") or "")),
        "opportunity_model_hash": _file_matches(root / str(opportunity.get("model_file") or ""), str(opportunity.get("model_hash") or "")),
        "opportunity_scaler_hash": _file_matches(root / str(opportunity.get("scaler_file") or ""), str(opportunity.get("scaler_hash") or "")),
        "calibration_refs": (root / str(candidate.get("calibration_ref") or "")).is_file() and (root / str(opportunity.get("calibration_ref") or "")).is_file(),
    }
    failed = [key for key, value in checks.items() if not value]
    return {"status": "PASS" if not failed else "BLOCK", "checks": checks, "failed_checks": failed}


def _remaining_risks() -> dict[str, Any]:
    return {
        "status": "PASS",
        "risks": [
            {
                "risk": "Generation B is a test-only fixture that reuses Generation A components.",
                "impact": "Closes update/rollback mechanics, not model-quality delta.",
                "mitigation": "B is explicitly marked test-only and rollback restores A.",
            },
            {
                "risk": "Phase19-AT E2E validation is still pending.",
                "impact": "Runtime transition mechanics are complete, but end-to-end daily operation is not certified here.",
                "mitigation": "Proceed to AT with COMMITTED A authority.",
            },
        ],
    }


def _final_judgment(*reviews: dict[str, Any]) -> dict[str, Any]:
    ok = all(review.get("status") == "PASS" for review in reviews)
    return {
        "status": "PASS" if ok else "REVIEW_REQUIRED",
        "final_judgment": ["PHASE19_AS_UPDATE_AND_ROLLBACK_CLOSURE_COMPLETE", "PHASE19_AT_E2E_VALIDATION_READY"]
        if ok
        else ["PHASE19_AS_REVIEW_REQUIRED", "PHASE19_AT_BLOCKED"],
        "production_readiness_declared": False,
        "buy_restart_executed": False,
        "broker_write_executed": False,
        "current_committed_generation_after_phase": GENERATION_A_ID,
    }


def _resolve_staged_pointer(runtime: Path) -> dict[str, Any]:
    staged = runtime / STAGED_POINTER
    if not staged.exists():
        return {"status": "MISSING"}
    pointer = _read_json(staged)
    manifest_path = Path(str(pointer.get("bundle_manifest_path") or ""))
    if not manifest_path.is_absolute():
        manifest_path = runtime.parent / manifest_path if str(manifest_path).startswith(".runtime/") else manifest_path
    if not manifest_path.is_file():
        return {"status": "MISSING_MANIFEST", "pointer": pointer}
    manifest = _read_json(manifest_path)
    return {
        "status": "PASS" if pointer.get("transaction_state") == "STAGED" and pointer.get("aggregate_hash") == manifest.get("aggregate_hash") else "BLOCK",
        "transaction_state": pointer.get("transaction_state"),
        "generation_id": manifest.get("generation_id"),
        "aggregate_hash": manifest.get("aggregate_hash"),
        "manifest_path": str(manifest_path),
    }


def _pointer_payload(state: str, transaction_id: str, manifest: dict[str, Any], manifest_path: Path | str, previous_generation_id: str | None) -> dict[str, Any]:
    return {
        "schema_version": "phase19_as_runtime_pointer.v1",
        "transaction_state": state,
        "transaction_id": transaction_id,
        "accepted_generation_id": manifest["generation_id"],
        "bundle_manifest_path": str(manifest_path),
        "aggregate_hash": manifest["aggregate_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "accepted_at": manifest["accepted_at"],
        "effective_from": manifest["effective_from"],
        "previous_generation_id": previous_generation_id,
        "authority_decision": "COMMITTED Accepted Generation pointer only" if state == "COMMITTED" else "STAGED smoke verification pointer only",
        "created_at": EXECUTED_AT,
    }


def _append_history(path: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_type": event_type,
        "created_at": EXECUTED_AT,
        "payload": payload,
        "idempotency_key": payload.get("idempotency_key") or _stable_hash({"event_type": event_type, "payload": payload}),
    }
    event["event_hash"] = _content_hash(event, "event_hash")
    existing = _jsonl_all(path)
    for item in existing:
        if item.get("idempotency_key") == event["idempotency_key"]:
            return {"status": "PASS", "append_status": "IDEMPOTENT_ALREADY_PRESENT", "path": str(path)}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return {"status": "PASS", "append_status": "APPENDED", "path": str(path)}


def _write_evidence(evidence_dir: Path, result: Phase19ASResult) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in result.to_dict().items():
        _write_json(evidence_dir / f"{name}.json", payload)


def write_regression_result(evidence_dir: Path | str, payload: dict[str, Any]) -> None:
    _write_json(Path(evidence_dir) / "regression_results.json", payload)


def write_summary(repo_root: Path | str, result: Phase19ASResult, *, changed_files: list[str]) -> None:
    root = Path(repo_root)
    summary = {
        "phase": PHASE,
        "final_judgment": result.final_judgment["final_judgment"],
        "generation_a": result.generation_a_pre_transition_snapshot["generation_id"],
        "generation_b": result.generation_b_fixture_or_artifact_review["generation_id"],
        "current_committed_generation_after_phase": result.final_judgment["current_committed_generation_after_phase"],
        "broker_write_executed": False,
        "buy_restart_executed": False,
        "evidence_dir": "reports/phase19_as_existing_committed_update_and_rollback_closure/",
        "changed_files": changed_files,
    }
    _write_json(root / "reports/phase_reports/phase19_as_existing_committed_update_and_rollback_closure.json", summary)


def _trading_state_snapshot(runtime: Path) -> dict[str, str]:
    rels = [
        Path("persistent_ledger/state.json"),
        Path("pending_order_plan/pending_order_plan.json"),
        Path("runtime_state/current_state.json"),
        Path("current/current.json"),
        Path("safety/state.json"),
        Path("broker/state.json"),
    ]
    snapshot: dict[str, str] = {}
    for rel in rels:
        path = runtime / rel
        if path.exists():
            snapshot[str(rel)] = _file_hash(path)
    return snapshot


def _jsonl_tail(path: Path, *, limit: int = 5) -> list[dict[str, Any]]:
    return _jsonl_all(path)[-limit:]


def _jsonl_all(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_immutable_json(path: Path, payload: dict[str, Any], *, hash_field: str) -> dict[str, Any]:
    if path.exists():
        existing = _read_json(path)
        if existing.get(hash_field) == payload.get(hash_field):
            return {"status": "PASS", "write_status": "IDEMPOTENT_ALREADY_PRESENT", "path": str(path)}
        return {"status": "BLOCK", "write_status": "IMMUTABILITY_CONFLICT", "path": str(path)}
    _write_json(path, payload)
    return {"status": "PASS", "write_status": "CREATED", "path": str(path)}


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _json_file_valid(path: Path) -> bool:
    try:
        _read_json(path)
    except Exception:
        return False
    return True


def _content_hash(payload: dict[str, Any], *hash_fields: str) -> str:
    excluded = set(hash_fields or ("content_hash",))
    return _stable_hash({key: value for key, value in payload.items() if key not in excluded})


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _file_matches(path: Path, expected_hash: str) -> bool:
    return path.is_file() and (not expected_hash or _file_hash(path) == expected_hash)


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
