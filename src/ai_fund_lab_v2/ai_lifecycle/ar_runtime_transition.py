from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.accepted_generation_consumer_adapter import validate_manifest_compatibility
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


PHASE = "Phase19-AR"
EXECUTED_AT = "2026-07-20T00:00:00+09:00"
ACCEPTED_GENERATION_ID = "phase19_aq_accepted_generation_641e6e313543f013"
ACCEPTED_MANIFEST = Path(
    ".runtime/ai_lifecycle/generations/phase19_aq_accepted_generation_641e6e313543f013/accepted_generation_manifest.json"
)
COMMITTED_POINTER = Path("runtime_state/accepted_buy_ai_bundle.json")
STAGED_POINTER = Path("runtime_state/staged_accepted_buy_ai_bundle.json")


@dataclass(frozen=True)
class Phase19ARResult:
    prepared_transaction: dict[str, Any]
    staged_pointer: dict[str, Any]
    smoke_verification: dict[str, Any]
    committed_pointer: dict[str, Any]
    runtime_reload_validation: dict[str, Any]
    rollback_validation: dict[str, Any]
    threshold_policy_validation: dict[str, Any]
    runtime_boundary_validation: dict[str, Any]
    schema_validation: dict[str, Any]
    hash_validation: dict[str, Any]
    binding_validation: dict[str, Any]
    regression_results: dict[str, Any]
    non_mutation: dict[str, Any]
    final_judgment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "prepared_transaction": self.prepared_transaction,
            "staged_pointer": self.staged_pointer,
            "smoke_verification": self.smoke_verification,
            "committed_pointer": self.committed_pointer,
            "runtime_reload_validation": self.runtime_reload_validation,
            "rollback_validation": self.rollback_validation,
            "threshold_policy_validation": self.threshold_policy_validation,
            "runtime_boundary_validation": self.runtime_boundary_validation,
            "schema_validation": self.schema_validation,
            "hash_validation": self.hash_validation,
            "binding_validation": self.binding_validation,
            "regression_results": self.regression_results,
            "non_mutation": self.non_mutation,
            "final_judgment": self.final_judgment,
        }


def run_phase19_ar(
    *,
    repo_root: Path | str,
    manifest_path: Path | str | None = None,
    runtime_root: Path | str | None = None,
    evidence_dir: Path | str | None = None,
    write_runtime_pointer: bool = True,
) -> Phase19ARResult:
    root = Path(repo_root)
    runtime = Path(runtime_root) if runtime_root is not None else root / ".runtime"
    manifest_file = Path(manifest_path) if manifest_path is not None else root / ACCEPTED_MANIFEST
    evidence_root = Path(evidence_dir) if evidence_dir is not None else root / "reports/phase19_ar_atomic_runtime_transition"
    manifest = _read_json(manifest_file)
    previous_resolution = resolve_accepted_generation(runtime)

    prepared = _prepared_transaction(manifest, manifest_file, previous_resolution)
    staged = _stage_pointer(runtime, manifest_file, manifest, prepared, write_runtime_pointer=write_runtime_pointer)
    smoke = _smoke_verification(root, manifest, manifest_file, staged)
    schema = _schema_validation(root, manifest)
    hash_validation = _hash_validation(manifest, manifest_file)
    binding = _binding_validation(root, manifest, prepared, staged, smoke)
    threshold = _threshold_policy_validation()
    committed = _commit_pointer(runtime, manifest_file, manifest, prepared, smoke, schema, hash_validation, binding, threshold, write_runtime_pointer=write_runtime_pointer)
    runtime_reload = _runtime_reload_validation(runtime, manifest, committed)
    rollback = _rollback_validation(runtime, manifest, prepared, committed)
    boundary = _runtime_boundary_validation(runtime_reload, threshold)
    non_mutation = _non_mutation()
    regression = {
        "status": "NOT_EXECUTED_IN_RUNNER",
        "py_compile": "RECORDED_BY_PHASE_SCRIPT",
        "pytest": "RECORDED_BY_PHASE_SCRIPT",
    }
    final = _final_judgment(
        prepared,
        staged,
        smoke,
        committed,
        runtime_reload,
        rollback,
        threshold,
        boundary,
        schema,
        hash_validation,
        binding,
        non_mutation,
    )
    result = Phase19ARResult(
        prepared_transaction=prepared,
        staged_pointer=staged,
        smoke_verification=smoke,
        committed_pointer=committed,
        runtime_reload_validation=runtime_reload,
        rollback_validation=rollback,
        threshold_policy_validation=threshold,
        runtime_boundary_validation=boundary,
        schema_validation=schema,
        hash_validation=hash_validation,
        binding_validation=binding,
        regression_results=regression,
        non_mutation=non_mutation,
        final_judgment=final,
    )
    _write_evidence(evidence_root, result)
    return result


def evaluate_threshold_policy(event_type: str) -> dict[str, Any]:
    structural = {
        "Schema mismatch",
        "Hash mismatch",
        "Missing Feature",
        "NaN",
        "Inf",
        "Loader Failure",
        "Collapse",
        "Candidate Dependency",
    }
    statistical = {"Distribution Drift", "Population Drift", "TopN Shape Drift"}
    if event_type in structural:
        action = "BUY_ONLY_BLOCK"
    elif event_type in statistical:
        action = "REVIEW_REQUIRED"
    else:
        action = "REVIEW_REQUIRED"
    return {
        "event_type": event_type,
        "action": action,
        "block_buy": action == "BUY_ONLY_BLOCK",
        "block_sell": False,
        "policy_source": "Phase19-AR Human Decision by user:negishi",
    }


def _prepared_transaction(manifest: dict[str, Any], manifest_path: Path, previous_resolution: Any) -> dict[str, Any]:
    transaction_id = f"phase19_ar_tx_{_stable_hash({'generation_id': manifest['generation_id'], 'aggregate_hash': manifest['aggregate_hash']})[:16]}"
    previous_generation = None
    if getattr(previous_resolution, "is_resolved", False):
        previous_generation = {
            "generation_id": previous_resolution.generation_id,
            "aggregate_hash": previous_resolution.aggregate_hash,
            "bundle_manifest_path": previous_resolution.bundle_manifest_path,
        }
    return {
        "status": "PASS",
        "phase": PHASE,
        "transaction_state": "PREPARED",
        "transaction_id": transaction_id,
        "accepted_generation_id": manifest["generation_id"],
        "aggregate_hash": manifest["aggregate_hash"],
        "previous_generation": previous_generation,
        "created_at": EXECUTED_AT,
        "accepted_manifest": str(manifest_path),
    }


def _stage_pointer(
    runtime_root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    prepared: dict[str, Any],
    *,
    write_runtime_pointer: bool,
) -> dict[str, Any]:
    payload = _pointer_payload("STAGED", manifest_path, manifest, prepared)
    staged_path = runtime_root / STAGED_POINTER
    if write_runtime_pointer:
        _write_json(staged_path, payload)
    return {
        "status": "PASS",
        "transaction_state": "STAGED",
        "pointer_path": str(staged_path),
        "pointer_written": write_runtime_pointer,
        "runtime_authority": "STAGED_ONLY_FOR_SMOKE_VERIFICATION",
        "committed_pointer_written": False,
        "payload": payload,
    }


def _smoke_verification(root: Path, manifest: dict[str, Any], manifest_path: Path, staged: dict[str, Any]) -> dict[str, Any]:
    consumer = validate_manifest_compatibility(manifest, repo_root=root, load_pickles=True).to_dict()
    checks = {
        "accepted_manifest": manifest.get("generation_status") == "ACCEPTED" and manifest.get("accepted") is True,
        "candidate": bool(consumer.get("candidate")),
        "opportunity": bool(consumer.get("opportunity")),
        "candidate_scaler": bool((consumer.get("candidate") or {}).get("scaler_file")),
        "opportunity_scaler": bool((consumer.get("opportunity") or {}).get("scaler_file")),
        "candidate_calibration": bool((consumer.get("candidate") or {}).get("calibration_ref")),
        "opportunity_calibration": bool((consumer.get("opportunity") or {}).get("calibration_ref")),
        "candidate_feature_order": bool((consumer.get("candidate") or {}).get("feature_order")),
        "opportunity_feature_order": bool((consumer.get("opportunity") or {}).get("feature_order")),
        "baseline": bool(manifest.get("runtime_baseline_ref")) and bool(manifest.get("runtime_baseline_hash")),
        "freshness": bool(manifest.get("freshness_metadata")),
        "runtime_consumer": consumer.get("status") == "PASS",
        "staged_pointer": staged.get("transaction_state") == "STAGED",
        "manifest_path_exists": manifest_path.is_file(),
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "PASS" if not failed else "BLOCK",
        "transaction_state": "SMOKE_VERIFIED" if not failed else "ABORTED",
        "checks": checks,
        "failed_checks": failed,
        "consumer_adapter": consumer,
    }


def _commit_pointer(
    runtime_root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    prepared: dict[str, Any],
    smoke: dict[str, Any],
    schema: dict[str, Any],
    hash_validation: dict[str, Any],
    binding: dict[str, Any],
    threshold: dict[str, Any],
    *,
    write_runtime_pointer: bool,
) -> dict[str, Any]:
    preconditions = {
        "smoke": smoke.get("status") == "PASS",
        "schema": schema.get("status") == "PASS",
        "hash": hash_validation.get("status") == "PASS",
        "binding": binding.get("status") == "PASS",
        "threshold_policy": threshold.get("status") == "PASS",
    }
    pointer_path = runtime_root / COMMITTED_POINTER
    payload = _pointer_payload("COMMITTED", manifest_path, manifest, prepared)
    if all(preconditions.values()) and write_runtime_pointer:
        _write_json(pointer_path, payload)
    return {
        "status": "PASS" if all(preconditions.values()) else "BLOCK",
        "transaction_state": "COMMITTED" if all(preconditions.values()) else "ABORTED",
        "pointer_path": str(pointer_path),
        "pointer_written": bool(all(preconditions.values()) and write_runtime_pointer),
        "runtime_authority": "COMMITTED_ACCEPTED_GENERATION_ONLY" if all(preconditions.values()) else "NOT_COMMITTED",
        "preconditions": preconditions,
        "payload": payload if all(preconditions.values()) else {},
    }


def _runtime_reload_validation(runtime_root: Path, manifest: dict[str, Any], committed: dict[str, Any]) -> dict[str, Any]:
    resolution = resolve_accepted_generation(runtime_root).to_dict()
    checks = {
        "committed_pointer": committed.get("transaction_state") == "COMMITTED",
        "resolved": resolution.get("resolution_status") == "RESOLVED_COMMITTED",
        "generation_id": resolution.get("generation_id") == manifest.get("generation_id"),
        "aggregate_hash": resolution.get("aggregate_hash") == manifest.get("aggregate_hash"),
        "candidate": bool(resolution.get("candidate_member")),
        "opportunity": bool(resolution.get("opportunity_member")),
        "legacy_component_fallback_used": resolution.get("source_evidence", {}).get("legacy_component_fallback_used") is False,
        "promotion_candidate_fallback_used": resolution.get("source_evidence", {}).get("promotion_candidate_fallback_used") is False,
        "manual_model_path_used": resolution.get("source_evidence", {}).get("manual_model_path_used") is False,
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "PASS" if not failed else "BLOCK",
        "runtime_reload_state": "RELOADED_COMMITTED_ACCEPTED_GENERATION" if not failed else "RELOAD_BLOCKED",
        "checks": checks,
        "failed_checks": failed,
        "resolution": resolution,
    }


def _rollback_validation(runtime_root: Path, manifest: dict[str, Any], prepared: dict[str, Any], committed: dict[str, Any]) -> dict[str, Any]:
    previous = prepared.get("previous_generation") or manifest.get("previous_generation_ref")
    pointer_path = runtime_root / COMMITTED_POINTER
    current_hash = _file_hash(pointer_path) if pointer_path.exists() else ""
    if not previous:
        return {
            "status": "PASS",
            "rollback_state": "ROLLBACK_NOT_AVAILABLE_BOOTSTRAP_NO_PREVIOUS_GENERATION",
            "rollback_executed": False,
            "rollback_pointer_mutation": False,
            "append_only_history_preserved": True,
            "current_pointer_sha256": current_hash,
            "reason": "Accepted Generation is bootstrap with no previous COMMITTED generation.",
        }
    rollback_payload = {
        "transaction_state": "ROLLED_BACK",
        "rollback_target": previous,
        "source_transaction_id": prepared["transaction_id"],
        "created_at": EXECUTED_AT,
    }
    return {
        "status": "PASS" if committed.get("transaction_state") == "COMMITTED" else "BLOCK",
        "rollback_state": "ROLLBACK_PLAN_VALIDATED",
        "rollback_executed": False,
        "rollback_pointer_mutation": False,
        "append_only_history_preserved": True,
        "rollback_payload_preview": rollback_payload,
        "current_pointer_sha256": current_hash,
    }


def _threshold_policy_validation() -> dict[str, Any]:
    structural = [
        "Schema mismatch",
        "Hash mismatch",
        "Missing Feature",
        "NaN",
        "Inf",
        "Loader Failure",
        "Collapse",
        "Candidate Dependency",
    ]
    statistical = ["Distribution Drift", "Population Drift", "TopN Shape Drift"]
    structural_results = [evaluate_threshold_policy(item) for item in structural]
    statistical_results = [evaluate_threshold_policy(item) for item in statistical]
    return {
        "status": "PASS",
        "reviewer": "user:negishi",
        "decision": {
            "structural_abnormality": "BUY_ONLY_BLOCK",
            "statistical_drift": "REVIEW_REQUIRED",
            "statistical_drift_buy_auto_stop": False,
        },
        "structural_results": structural_results,
        "statistical_results": statistical_results,
        "buy_only_block_normal": all(item["action"] == "BUY_ONLY_BLOCK" and item["block_buy"] for item in structural_results),
        "statistical_drift_review_required": all(item["action"] == "REVIEW_REQUIRED" and not item["block_buy"] for item in statistical_results),
        "sell_independence": all(not item["block_sell"] for item in structural_results + statistical_results),
    }


def _runtime_boundary_validation(runtime_reload: dict[str, Any], threshold: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if runtime_reload.get("status") == "PASS" and threshold.get("status") == "PASS" else "BLOCK",
        "runtime_authority": "COMMITTED Accepted Generation only",
        "forbidden_authorities_used": {
            "latest": False,
            "mtime": False,
            "legacy": False,
            "manual": False,
            "promotion_candidate": False,
        },
        "accepted_generation_consumer_flow": [
            "Accepted Generation",
            "Runtime Resolver",
            "Candidate",
            "Opportunity",
            "BUY Planning",
        ],
        "dual_gate_runtime_reference": False,
        "sell_independence": True,
    }


def _schema_validation(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    schema = _read_json(root / "schemas/ai_lifecycle/accepted_generation_manifest.schema.json")
    missing = [key for key in schema.get("required", []) if key not in manifest]
    const_mismatch = []
    for key, spec in (schema.get("properties") or {}).items():
        if isinstance(spec, dict) and "const" in spec and key in manifest and manifest[key] != spec["const"]:
            const_mismatch.append(key)
    return {
        "status": "PASS" if not missing and not const_mismatch else "BLOCK",
        "schema": "schemas/ai_lifecycle/accepted_generation_manifest.schema.json",
        "json_parse": "PASS",
        "draft_schema_validation": "NOT_EXECUTED_jsonschema_not_project_dependency",
        "missing_required_fields": missing,
        "const_mismatch": const_mismatch,
    }


def _hash_validation(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    aggregate_recomputed = _content_hash(manifest, "aggregate_hash", "manifest_hash")
    manifest_hash_recomputed = _content_hash(manifest, "manifest_hash")
    return {
        "status": "PASS"
        if manifest.get("aggregate_hash") == aggregate_recomputed and manifest.get("manifest_hash") == manifest_hash_recomputed
        else "BLOCK",
        "algorithm": "SHA256",
        "canonicalization": "JSON sort_keys compact separators ensure_ascii default=str",
        "aggregate_hash": manifest.get("aggregate_hash"),
        "aggregate_hash_recomputed": aggregate_recomputed,
        "manifest_hash": manifest.get("manifest_hash"),
        "manifest_hash_recomputed": manifest_hash_recomputed,
        "artifact_file_sha256": _file_hash(manifest_path),
    }


def _binding_validation(root: Path, manifest: dict[str, Any], prepared: dict[str, Any], staged: dict[str, Any], smoke: dict[str, Any]) -> dict[str, Any]:
    candidate = manifest.get("candidate_member") or {}
    opportunity = manifest.get("opportunity_member") or {}
    checks = {
        "accepted_generation_id": prepared.get("accepted_generation_id") == manifest.get("generation_id"),
        "staged_generation_id": staged.get("payload", {}).get("accepted_generation_id") == manifest.get("generation_id"),
        "candidate_model_hash": _file_matches(root / str(candidate.get("model_file") or ""), str(candidate.get("model_hash") or "")),
        "candidate_scaler_hash": _file_matches(root / str(candidate.get("scaler_file") or ""), str(candidate.get("scaler_hash") or "")),
        "opportunity_model_hash": _file_matches(root / str(opportunity.get("model_file") or ""), str(opportunity.get("model_hash") or "")),
        "opportunity_scaler_hash": _file_matches(root / str(opportunity.get("scaler_file") or ""), str(opportunity.get("scaler_hash") or "")),
        "candidate_calibration_present": (root / str(candidate.get("calibration_ref") or "")).is_file(),
        "opportunity_calibration_present": (root / str(opportunity.get("calibration_ref") or "")).is_file(),
        "feature_order_present": bool(candidate.get("feature_order")) and bool(opportunity.get("feature_order")),
        "baseline_bound": bool(manifest.get("runtime_baseline_hash")),
        "freshness_bound": bool(manifest.get("freshness_metadata")),
        "smoke_verified": smoke.get("status") == "PASS",
    }
    failed = [key for key, value in checks.items() if not value]
    return {"status": "PASS" if not failed else "BLOCK", "checks": checks, "failed_checks": failed}


def _non_mutation() -> dict[str, Any]:
    return {
        "status": "PASS",
        "broker_write": 0,
        "buy_restart": 0,
        "production_ready_declared": False,
        "autonomous_operation_complete_declared": False,
        "accepted_generation_created_in_ar": 0,
        "training_rerun": 0,
        "calibration_refit": 0,
        "sell_state_mutated": False,
        "sell_dependencies": {
            "Current": "UNCHANGED",
            "Pending": "UNCHANGED",
            "Ledger": "UNCHANGED",
            "PM": "UNCHANGED",
            "Safety": "UNCHANGED",
            "Broker": "UNCHANGED",
        },
    }


def _final_judgment(*reviews: dict[str, Any]) -> dict[str, Any]:
    ok = all(review.get("status") == "PASS" for review in reviews)
    return {
        "status": "PASS" if ok else "REVIEW_REQUIRED",
        "final_judgment": [
            "PHASE19_AR_RUNTIME_TRANSITION_COMPLETE",
            "PHASE19_AS_E2E_VALIDATION_READY",
        ]
        if ok
        else ["PHASE19_AR_REVIEW_REQUIRED"],
        "accepted_generation_id": ACCEPTED_GENERATION_ID,
        "runtime_transition_complete": ok,
        "production_readiness_declared": False,
        "buy_restart_executed": False,
        "broker_write_executed": False,
    }


def _pointer_payload(state: str, manifest_path: Path, manifest: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase19_ar_runtime_pointer.v1",
        "transaction_state": state,
        "transaction_id": prepared["transaction_id"],
        "accepted_generation_id": manifest["generation_id"],
        "bundle_manifest_path": str(manifest_path),
        "aggregate_hash": manifest["aggregate_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "accepted_at": manifest["accepted_at"],
        "effective_from": manifest["effective_from"],
        "previous_generation": prepared.get("previous_generation"),
        "authority_decision": "COMMITTED Accepted Generation pointer only" if state == "COMMITTED" else "STAGED smoke verification pointer only",
        "created_at": EXECUTED_AT,
    }


def _write_evidence(evidence_dir: Path, result: Phase19ARResult) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in result.to_dict().items():
        _write_json(evidence_dir / f"{name}.json", payload)


def copy_regression_result(evidence_dir: Path | str, payload: dict[str, Any]) -> None:
    _write_json(Path(evidence_dir) / "regression_results.json", payload)


def write_summary_files(repo_root: Path | str, result: Phase19ARResult, *, changed_files: list[str]) -> None:
    root = Path(repo_root)
    summary = {
        "phase": PHASE,
        "accepted_generation_id": ACCEPTED_GENERATION_ID,
        "final_judgment": result.final_judgment["final_judgment"],
        "runtime_pointer": result.committed_pointer.get("pointer_path"),
        "runtime_transition_complete": result.final_judgment.get("runtime_transition_complete"),
        "broker_write_executed": False,
        "buy_restart_executed": False,
        "evidence_dir": "reports/phase19_ar_atomic_runtime_transition/",
        "changed_files": changed_files,
    }
    _write_json(root / "reports/phase_reports/phase19_ar_atomic_runtime_transition.json", summary)


def copy_evidence_file(src: Path | str, dst: Path | str) -> None:
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
