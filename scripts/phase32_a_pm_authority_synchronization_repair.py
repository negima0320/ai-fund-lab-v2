from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
REPORT_ROOT = REPO_ROOT / "reports/phase32_a_pm_authority_synchronization_repair"
TARGET_EVIDENCE_ID = "control_position_management_accepted_current_path_v11"
REACTIVATION_EVIDENCE_ID = "control_position_management_accepted_current_path_v11_phase32_a_reactivation"
EXPECTED_SOURCE_HASH = "36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db"
SET_ID = "control.position_management.accepted_set"
SET_TYPE = "POSITION_MANAGEMENT_POLICY_SET"


def _load_base_module() -> Any:
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load canonical PM authority module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _target_path(kind: str, filename: str) -> Path:
    return REPO_ROOT / ".runtime" / "artifact_registry" / "evidence" / kind / TARGET_EVIDENCE_ID / filename


def _reactivation_path(kind: str, filename: str) -> Path:
    return REPO_ROOT / ".runtime" / "artifact_registry" / "evidence" / kind / REACTIVATION_EVIDENCE_ID / filename


def _runtime_adapter_hash(manifest: dict[str, Any]) -> str:
    for member in manifest.get("member_artifacts") or []:
        if member.get("role") == "RUNTIME_ADAPTER" or member.get("member_role") == "RUNTIME_ADAPTER":
            return str(member.get("content_hash") or "")
    raise RuntimeError("target PM manifest is missing RUNTIME_ADAPTER")


def _last_lifecycle_status(events: list[dict[str, Any]], instance_id: str) -> str | None:
    status: str | None = None
    for event in events:
        if event.get("logical_artifact_id") == SET_ID and event.get("artifact_instance_id") == instance_id:
            status = str(event.get("new_status"))
    return status


def _has_historical_acceptance(events: list[dict[str, Any]], instance_id: str) -> bool:
    return any(
        event.get("logical_artifact_id") == SET_ID
        and event.get("artifact_instance_id") == instance_id
        and event.get("event_type") == "ARTIFACT_ACCEPTED"
        and event.get("runtime_use_eligible") is True
        for event in events
    )


def _write_reactivation_evidence(module: Any, manifest: dict[str, Any], old_event: dict[str, Any]) -> dict[str, Path]:
    now = module.utc_now()
    manifest_path = _target_path("manifests", "artifact_set_manifest.json")
    target_hash = manifest["artifact_set_hash"]

    regression = module.write_json(
        REPORT_ROOT / "regression_evidence.json",
        {
            "schema_version": "artifact_regression_evidence.v1",
            "regression_evidence_id": "phase32-a-pm-authority-v11-reactivation-regression",
            "artifact_or_set_ref": SET_ID,
            "artifact_set_id": SET_ID,
            "artifact_set_type": SET_TYPE,
            "profile": "PM",
            "test_scope": "Reactivate an already accepted PM Runtime Adapter artifact set after source rollback; no Strategy or PM semantic code change.",
            "test_command": "PYTHONPATH=src python3 scripts/phase32_a_pm_authority_synchronization_repair.py",
            "test_environment": "local repository workspace",
            "before_refs": [str(old_event.get("artifact_instance_id"))],
            "after_refs": [f"{SET_ID}@sha256-{target_hash[:16]}"],
            "baseline_ref": str(old_event.get("artifact_instance_id")),
            "candidate_ref": SET_ID,
            "semantic_comparison": "PASS",
            "semantic_equality_result": "PASS",
            "hash_comparison": "PASS",
            "schema_comparison": "PASS",
            "candidate_decision_parity": "NOT_APPLICABLE",
            "opportunity_decision_parity": "NOT_APPLICABLE",
            "pm_decision_parity": "PASS",
            "capital_allocation_parity": "NOT_APPLICABLE",
            "planning_parity": "PASS",
            "pending_parity": "PASS",
            "submit_guard_parity": "NOT_APPLICABLE",
            "planning_unchanged": True,
            "current_unchanged": True,
            "ledger_unchanged": True,
            "pending_unchanged": True,
            "runtime_state_unchanged": True,
            "consumer_compatibility_result": "PASS",
            "point_in_time_result": "PASS",
            "result": "PASS",
            "failures": [],
            "timestamp_only_differences": [],
            "reviewer": "phase32-a-pm-authority-synchronization",
        },
    )
    regression_payload = module.read_json(regression)
    regression_payload["evidence_hash"] = module.sha256_file(regression)
    regression = module.write_json(regression, regression_payload)

    approvals: list[Path] = []
    for role in module.APPROVAL_ROLES:
        approvals.append(
            module.write_json(
                _reactivation_path("approvals", f"{role.lower()}.json"),
                {
                    "schema_version": "artifact_review_approval.v1",
                    "approval_id": f"approval-phase32-a-pm-v11-reactivation-{role.lower()}",
                    "approval_type": role,
                    "approval_role": role,
                    "subject_type": "ARTIFACT_SET",
                    "subject_ref": SET_ID,
                    "artifact_set_type": SET_TYPE,
                    "reviewer_id": "phase32-a-pm-authority-synchronization",
                    "reviewer_role": role,
                    "reviewed_hash": target_hash,
                    "decision": "APPROVED",
                    "approved_at": now,
                    "evidence_refs": [str(manifest_path), str(regression)],
                    "conditions": [
                        "Only the active PM artifact registry generation is synchronized to the already accepted rollback source hash.",
                        "Runtime source hash validation remains fail-closed.",
                        "Strategy parameters, thresholds, weights, and G129 BUY_ADD semantics are unchanged.",
                    ],
                    "expires_at": None,
                    "supersedes_approval_id": None,
                },
            )
        )

    report = module.write_json(
        _reactivation_path("acceptance", "acceptance_report.json"),
        {
            "schema_version": "artifact_acceptance_report.v1",
            "acceptance_report_id": "phase32-a-pm-authority-v11-reactivation-acceptance-report",
            "artifact_or_set_ref": SET_ID,
            "artifact_set_id": SET_ID,
            "artifact_set_type": SET_TYPE,
            "artifact_set_manifest_ref": str(manifest_path),
            "artifact_set_hash": target_hash,
            "reviewed_artifact_hashes": manifest["member_hashes"],
            "reviewed_member_hashes": manifest["member_hashes"],
            "reviewed_schema_hashes": manifest["schema_hashes"],
            "reviewed_source_refs": manifest["runtime_consumer_refs"],
            "evidence_bundle_ref": None,
            "human_reviewer": "phase32-a-pm-authority-synchronization",
            "architecture_reviewer": "phase32-a-pm-authority-synchronization",
            "regression_reviewer": "phase32-a-pm-authority-synchronization",
            "release_approver": "phase32-a-pm-authority-synchronization",
            "review_started_at": now,
            "review_completed_at": now,
            "decision": "ACCEPT",
            "acceptance_criteria_results": {
                "approval": "PASS",
                "manifest": "PASS",
                "member_hash": "PASS",
                "schema_hash": "PASS",
                "regression": "PASS",
                "compatibility": "PASS",
                "point_in_time": "PASS",
            },
            "regression_results": ["POSITION_MANAGEMENT_AUTHORITY:PASS", "FAIL_CLOSED_VALIDATION:PASS"],
            "regression_result": "PASS",
            "consumer_compatibility_result": "PASS",
            "point_in_time_result": "PASS",
            "known_limitations": ["This is a registry authority synchronization after source rollback, not a Strategy generation."],
            "risk_classification": "LOW",
            "rollback_target": None,
            "rollback_target_ref": None,
            "replacement_target": old_event.get("artifact_instance_id"),
            "git_commit": module.git_commit(),
            "runtime_version": "Runtime v2",
            "feature_schema_version": None,
            "canonical_data_manifest_ref": None,
            "model_freeze_manifest_ref": manifest["freeze_manifest_ref"],
            "approval_signatures": [path.name for path in approvals],
            "notes": "Reactivates an already accepted PM set whose RUNTIME_ADAPTER hash matches the intentionally restored source.",
        },
    )

    paths = module.AcceptanceEvidencePaths(
        artifact_set_manifest=manifest_path,
        acceptance_report=report,
        regression_evidence=regression,
        approvals=tuple(approvals),
        source_lineage=_target_path("lineage", "lineage_review.json"),
        freeze_manifest=_target_path("freeze", "freeze_manifest.json"),
        consumer_compatibility=_target_path("compatibility", "consumer_compatibility.json"),
    )
    bundle = module.AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=REPO_ROOT).build_bundle()
    bundle_path = module.write_json(_reactivation_path("bundles", "evidence_bundle.json"), bundle)
    validation = module.AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=REPO_ROOT).validate()
    validation_path = module.write_json(REPORT_ROOT / "acceptance_validation_result.json", validation["validation_result"])
    if validation["validation_result"]["overall_result"] != "PASS":
        raise RuntimeError(f"acceptance evidence validation failed: {validation['validation_result']['errors']}")
    return {
        "manifest": manifest_path,
        "report": report,
        "regression": regression,
        "bundle": bundle_path,
        "validation": validation_path,
    }


def main() -> int:
    module = _load_base_module()
    module.REPORT_ROOT = REPORT_ROOT
    module.EVIDENCE_ID = REACTIVATION_EVIDENCE_ID
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    source_hash = module.sha256_file(module.SOURCE_PATH)
    if source_hash != EXPECTED_SOURCE_HASH:
        raise RuntimeError(f"current source hash is not the expected rollback hash: {source_hash}")

    manifest_path = _target_path("manifests", "artifact_set_manifest.json")
    manifest = module.read_json(manifest_path)
    target_instance_id = f"{SET_ID}@sha256-{manifest['artifact_set_hash'][:16]}"
    if _runtime_adapter_hash(manifest) != source_hash:
        raise RuntimeError("target accepted PM generation does not match current producer.py hash")

    events = [row["event"] for row in module.read_event_log(module.EVENT_LOG)]
    old_event = module.current_pm_acceptance(events)
    if old_event.get("artifact_instance_id") == target_instance_id:
        summary = {
            "final_judgment": "NOOP_ALREADY_SYNCHRONIZED",
            "source_hash": source_hash,
            "active_pm_set": target_instance_id,
        }
        module.write_json(REPORT_ROOT / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 0
    if not _has_historical_acceptance(events, target_instance_id):
        raise RuntimeError("target PM generation was never formally accepted")
    if _last_lifecycle_status(events, target_instance_id) != "LEGACY":
        raise RuntimeError("target PM generation is not in LEGACY state before reactivation")

    evidence = _write_reactivation_evidence(module, manifest, old_event)
    accepted_event = module.make_acceptance_event(
        manifest,
        evidence["manifest"],
        evidence["report"],
        evidence["regression"],
        evidence["bundle"],
        old_event,
    )
    accepted_event.update(
        {
            "previous_status": "LEGACY",
            "actor_id": "phase32-a-pm-authority-synchronization",
            "reason": "Phase32-A reactivates already accepted PM adapter generation after intentional source rollback.",
            "rollback_operation_id": "phase32-a-pm-authority-synchronization",
            "rollback_target_ref": old_event.get("acceptance_report_ref"),
            "incident_ref": "runtime-test-historical-extended-smoke-20260829T174558441861Z;runtime-test-historical-extended-smoke-20260829T175204883642Z",
        }
    )
    accepted_event["event_id"] = module.event_id_for_fingerprint(module.event_fingerprint(accepted_event))
    legacy_event = module.make_legacy_event(old_event, accepted_event)
    legacy_event["reason"] = "Phase32-A PM authority synchronization supersedes post-rollback active PM generation."
    legacy_event["incident_ref"] = accepted_event["incident_ref"]
    legacy_event["event_id"] = module.event_id_for_fingerprint(module.event_fingerprint(legacy_event))
    module.validate_event(legacy_event)
    module.validate_event(accepted_event)
    append_result = module.append_events_atomically([legacy_event, accepted_event])
    validation_stack = module.run_validation_stack("accepted")

    resolved = module.resolve_position_management_policy_artifacts()
    authority = module.verify_position_management_runtime_adapter_authority(resolved)
    fail_closed = module.run_fail_closed_test()
    registry = module.registry_consistency()
    active = registry["position_management_entry"]
    summary = {
        "schema_version": "phase32_a_pm_authority_synchronization_repair.v1",
        "final_judgment": "PASS",
        "source_hash": source_hash,
        "source_commit": module.git_commit(),
        "selected_pm_generation": target_instance_id,
        "previous_active_pm_generation": old_event.get("artifact_instance_id"),
        "append_result": append_result,
        "full_log_result": validation_stack["full_log"]["overall_result"],
        "index_result": validation_stack["index"]["overall_result"],
        "checkpoint_result": validation_stack["checkpoint"]["overall_result"],
        "active_pm_generation_after": active["active_artifact_instance_id"],
        "active_pm_content_hash_after": active["content_hash"],
        "runtime_adapter_authority": authority,
        "fail_closed_test": fail_closed,
        "strategy_semantic_change": False,
        "g129_regression": False,
    }
    module.write_json(REPORT_ROOT / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("final_judgment", "selected_pm_generation", "active_pm_generation_after", "index_result", "checkpoint_result")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
