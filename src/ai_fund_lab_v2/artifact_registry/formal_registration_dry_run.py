from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import (
    AcceptanceEvidenceBundleBuilder,
    AcceptanceEvidenceBundleValidator,
    AcceptanceEvidencePaths,
    atomic_write_text,
    sha256_file_bytes,
)
from ai_fund_lab_v2.artifact_registry.acceptance_writer import AcceptanceWriterInputs, ArtifactAcceptanceWriter
from ai_fund_lab_v2.artifact_registry.checkpoint_writer import RegistryCheckpointWriter
from ai_fund_lab_v2.artifact_registry.index_builder import MaterializedRegistryIndexBuilder
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import artifact_set_hash
from ai_fund_lab_v2.artifact_registry.writer import RegistryEventLogWriter


DRY_RUN_VERSION = "phase16am_formal_registration_dry_run_v1"
DEFAULT_OUTPUT_ROOT = Path("reports/phase16_formal_registration_dry_run")
APPROVAL_ROLES = ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")


@dataclass(frozen=True)
class DryRunArtifactSetSpec:
    set_id: str
    set_type: str
    component: str
    roles: tuple[str, ...]
    sources: dict[str, Path]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def default_specs(repo_root: Path) -> tuple[DryRunArtifactSetSpec, ...]:
    def p(value: str) -> Path:
        return repo_root / value

    return (
        DryRunArtifactSetSpec(
            set_id="formal.candidate.ai.set",
            set_type="CANDIDATE_AI_SET",
            component="Candidate AI",
            roles=("MODEL", "MODEL_MANIFEST", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "METRICS_EVIDENCE", "CONSUMER_COMPATIBILITY"),
            sources={
                "MODEL": p(".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl"),
                "MODEL_MANIFEST": p(".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json"),
                "FEATURE_SCHEMA": p(".runtime/candidate_ai/manifests/phase4bc_long_history_features_manifest_2021-06-14_2026-06-12.json"),
                "TRAINING_METADATA": p(".runtime/candidate_ai/manifests/phase4be_long_history_dataset_manifest_2021-06-14_2026-05-15.json"),
                "TRAINING_DATA_LINEAGE": p(".runtime/candidate_ai/audit/phase4be_long_history_dataset_audit_2021-06-14_2026-05-15.json"),
                "VALIDATION_EVIDENCE": p(".runtime/candidate_ai/audit/phase4bc_long_history_features_audit_2021-06-14_2026-06-12.json"),
                "METRICS_EVIDENCE": p(".runtime/candidate_ai/inference/phase4bg_formal_candidate_scores_2026-06-12.json"),
                "CONSUMER_COMPATIBILITY": p(".runtime/operations/feature_consumer_readiness/2026-07-10.json"),
            },
        ),
        DryRunArtifactSetSpec(
            set_id="formal.opportunity.ai.set",
            set_type="OPPORTUNITY_AI_SET",
            component="Opportunity AI",
            roles=("MODEL", "METRICS", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "CONSUMER_COMPATIBILITY"),
            sources={
                "MODEL": p(".runtime/phase9/inference/2026-06-26/opportunity_artifact.json"),
                "METRICS": p(".runtime/phase9/inference/2026-06-26/daily_inference_manifest.json"),
                "FEATURE_SCHEMA": p(".runtime/phase9/feature_refresh/2026-06-26/feature_refresh_manifest.json"),
                "TRAINING_METADATA": p(".runtime/phase9/training_dataset_candidates/2026-05-18/training_dataset_manifest.json"),
                "TRAINING_DATA_LINEAGE": p(".runtime/phase9/training_dataset_candidates/2026-05-18/opportunity_ai_dataset.parquet"),
                "VALIDATION_EVIDENCE": p(".runtime/phase9/audits/candidate_universe_hard_gate_fix_validation.json"),
                "CONSUMER_COMPATIBILITY": p(".runtime/operations/feature_consumer_readiness/2026-07-10.json"),
            },
        ),
        DryRunArtifactSetSpec(
            set_id="formal.position.management.policy.set",
            set_type="POSITION_MANAGEMENT_POLICY_SET",
            component="Position Management Policy",
            roles=("CODE_POLICY", "RUNTIME_ADAPTER", "POLICY_VERSION", "FEATURE_VERSION", "BEHAVIOR_CONTRACT", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"),
            sources={
                "CODE_POLICY": p(".runtime/phase9/policy_manifests/position_policy_manifest.json"),
                "RUNTIME_ADAPTER": p(".runtime/phase9/features/2026-06-26/position_feature_input.parquet"),
                "POLICY_VERSION": p(".runtime/phase9/policy_manifests/position_policy_manifest.json"),
                "FEATURE_VERSION": p(".runtime/phase9/feature_refresh/2026-06-26/feature_refresh_manifest.json"),
                "BEHAVIOR_CONTRACT": p("docs/02_architecture/artifact_acceptance_contract.md"),
                "REGRESSION_EVIDENCE": p("reports/phase_reports/phase16_al_authority_gated_acceptance_writer_implementation.json"),
                "CONSUMER_COMPATIBILITY": p(".runtime/operations/feature_consumer_readiness/2026-07-10.json"),
            },
        ),
        DryRunArtifactSetSpec(
            set_id="formal.capital.allocation.policy.set",
            set_type="CAPITAL_ALLOCATION_POLICY_SET",
            component="Capital Allocation Policy",
            roles=("POLICY", "POLICY_SCHEMA", "POLICY_VERSION", "VALIDATION_EVIDENCE", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"),
            sources={
                "POLICY": p(".runtime/phase9/policy_manifests/capital_policy_manifest.json"),
                "POLICY_SCHEMA": p(".runtime/phase9/features/2026-06-26/capital_policy_input.parquet"),
                "POLICY_VERSION": p(".runtime/phase9/policy_manifests/capital_policy_manifest.json"),
                "VALIDATION_EVIDENCE": p(".runtime/phase9/audits/candidate_universe_hard_gate_fix_validation.json"),
                "REGRESSION_EVIDENCE": p("reports/phase_reports/phase16_al_authority_gated_acceptance_writer_implementation.json"),
                "CONSUMER_COMPATIBILITY": p(".runtime/operations/feature_consumer_readiness/2026-07-10.json"),
            },
        ),
    )


class FormalRegistrationDryRun:
    def __init__(self, *, output_root: Path = DEFAULT_OUTPUT_ROOT, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path.cwd()
        self.output_root = output_root if output_root.is_absolute() else self.repo_root / output_root
        self.registry_root = self.output_root / "isolated_registry"
        self.event_log_path = self.registry_root / "events" / "registry_events.jsonl"

    def run(self, specs: tuple[DryRunArtifactSetSpec, ...] | None = None) -> dict[str, Any]:
        specs = specs or default_specs(self.repo_root)
        self._init_output()
        before = protected_hashes(self.repo_root)
        set_results = [self._run_set(spec) for spec in specs]
        index_result = MaterializedRegistryIndexBuilder(registry_root=self.registry_root, event_log_path=self.event_log_path, repo_root=self.repo_root).build()
        checkpoint_result = RegistryCheckpointWriter(registry_root=self.registry_root, event_log_path=self.event_log_path, repo_root=self.repo_root).write_checkpoint()
        after = protected_hashes(self.repo_root)
        summary = {
            "schema_version": "phase16am_formal_registration_dry_run_result.v1",
            "dry_run_version": DRY_RUN_VERSION,
            "created_at": utc_now(),
            "isolated_registry_root": str(self.registry_root),
            "set_results": set_results,
            "index_result": {
                "overall_result": index_result["overall_result"],
                "failure_class": index_result["failure_class"],
                "event_count": index_result["event_count"],
                "entry_count": index_result["entry_count"],
                "index_hash": index_result["index_hash"],
                "index_path": index_result["index_path"],
            },
            "checkpoint_result": {
                "overall_result": checkpoint_result["overall_result"],
                "failure_class": checkpoint_result["failure_class"],
                "checkpoint_status": checkpoint_result["checkpoint_status"],
                "event_log_hash": checkpoint_result["event_log_hash"],
                "materialized_index_hash": checkpoint_result["materialized_index_hash"],
                "checkpoint_hash": checkpoint_result["checkpoint_hash"],
                "event_count": checkpoint_result["event_count"],
                "entry_count": checkpoint_result["entry_count"],
            },
            "protected_hashes_before": before,
            "protected_hashes_after": after,
            "protected_hashes_unchanged": before == after,
            "formal_registry_changed": before["formal_event_log"]["sha256"] != after["formal_event_log"]["sha256"]
            or before["formal_index"]["sha256"] != after["formal_index"]["sha256"]
            or before["formal_checkpoint"]["sha256"] != after["formal_checkpoint"]["sha256"],
        }
        summary["overall_result"] = "PASS" if all(item["overall_result"] == "PASS" for item in set_results) and index_result["overall_result"] == "PASS" and checkpoint_result["overall_result"] == "PASS" and summary["protected_hashes_unchanged"] else "FAIL"
        write_json(self.output_root / "summary.json", summary)
        write_json(self.output_root / "copy_plan.json", {"schema_version": "phase16am_copy_plan.v1", "sets": [item["copy_plan"] for item in set_results]})
        return summary

    def _init_output(self) -> None:
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        (self.registry_root / "locks").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "index").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "checkpoints").mkdir(parents=True, exist_ok=True)
        self.event_log_path.write_text("", encoding="utf-8")

    def _run_set(self, spec: DryRunArtifactSetSpec) -> dict[str, Any]:
        set_root = self.output_root / "sets" / spec.set_id
        set_root.mkdir(parents=True, exist_ok=True)
        copy_plan = self._copy_plan(spec)
        manifest = self._manifest(spec, copy_plan)
        manifest_path = write_json(set_root / "artifact_set_manifest.json", manifest)
        writer = RegistryEventLogWriter(self.registry_root, repo_root=self.repo_root)
        draft = writer.append_event(self._registry_event(spec, manifest, previous_status=None, new_status="DRAFT", event_type="ARTIFACT_DISCOVERED", manifest_path=manifest_path))
        validated = writer.append_event(self._registry_event(spec, manifest, previous_status="DRAFT", new_status="VALIDATED", event_type="ARTIFACT_VALIDATED", manifest_path=manifest_path))
        evidence = self._acceptance_evidence(spec, manifest, manifest_path, set_root)
        acceptance_inputs = AcceptanceWriterInputs(
            registry_root=self.registry_root,
            evidence_bundle=evidence["bundle_path"],
            validation_result=evidence["validation_result_path"],
            artifact_set_manifest=manifest_path,
            acceptance_report=evidence["acceptance_report_path"],
            regression_evidence=evidence["regression_evidence_path"],
            approvals=tuple(evidence["approval_paths"]),
            output_root=set_root / "acceptance_writer",
        )
        acceptance = ArtifactAcceptanceWriter(inputs=acceptance_inputs, repo_root=self.repo_root).append_acceptance()
        return {
            "artifact_set_id": spec.set_id,
            "artifact_set_type": spec.set_type,
            "overall_result": "PASS" if acceptance["overall_result"] == "PASS" else "FAIL",
            "copy_plan": copy_plan,
            "manifest_path": str(manifest_path),
            "draft_event_id": draft.event_id,
            "validated_event_id": validated.event_id,
            "acceptance_event_id": acceptance["event_id"],
            "acceptance_event_fingerprint": acceptance["event_fingerprint"],
            "acceptance_result": acceptance["overall_result"],
        }

    def _copy_plan(self, spec: DryRunArtifactSetSpec) -> dict[str, Any]:
        items = []
        for role in spec.roles:
            source = spec.sources[role]
            if not source.is_file():
                raise FileNotFoundError(f"Dry Run source missing: {source}")
            items.append(
                {
                    "role": role,
                    "source": str(source),
                    "destination": f"registry/artifacts/{spec.set_id}/{role.lower()}/{source.name}",
                    "hash": sha256_file_bytes(source),
                    "size": source.stat().st_size,
                    "overwrite": False,
                }
            )
        return {"artifact_set_id": spec.set_id, "artifact_set_type": spec.set_type, "items": items}

    def _manifest(self, spec: DryRunArtifactSetSpec, copy_plan: dict[str, Any]) -> dict[str, Any]:
        members = []
        set_source_refs = [item["source"] for item in copy_plan["items"]]
        for item in copy_plan["items"]:
            role = item["role"]
            logical_id = f"{spec.set_id}.{role.lower()}"
            members.append(
                {
                    "logical_artifact_id": logical_id,
                    "artifact_instance_id": f"{logical_id}@sha256-{item['hash'][:16]}",
                    "artifact_set_id": spec.set_id,
                    "artifact_type": role,
                    "physical_path": item["source"],
                    "content_hash": item["hash"],
                    "schema_hash": stable_json_hash({"role": role, "source": item["source"]}),
                    "role": role,
                    "member_role": role,
                    "status": "VALIDATED",
                    "runtime_use_eligible": False,
                    "source_refs": set_source_refs,
                }
            )
        manifest = {
            "schema_version": "artifact_set_manifest.v1",
            "artifact_set_id": spec.set_id,
            "artifact_set_type": spec.set_type,
            "artifact_set_version": "dry-run-v1",
            "set_authority_scope": "SET_LEVEL",
            "component": spec.component,
            "member_artifacts": members,
            "required_member_types": list(spec.roles),
            "required_member_roles": list(spec.roles),
            "member_hashes": {item["logical_artifact_id"]: item["content_hash"] for item in members},
            "schema_hashes": {item["logical_artifact_id"]: item["schema_hash"] for item in members},
            "compatibility_constraints": ["Runtime"],
            "training_period": None,
            "feature_schema_ref": next((m["logical_artifact_id"] for m in members if "FEATURE" in m["member_role"] or "SCHEMA" in m["member_role"]), None),
            "consumer_compatibility_ref": "consumer_compatibility.json",
            "source_lineage_ref": "source_lineage.json",
            "freeze_manifest_ref": "freeze_manifest.json",
            "validation_evidence_refs": ["regression_evidence.json"],
            "regression_evidence_refs": ["regression_evidence.json"],
            "runtime_consumer_refs": ["Runtime"],
            "artifact_set_hash": "",
            "status": "VALIDATED",
            "runtime_use_eligible": False,
        }
        manifest["artifact_set_hash"] = artifact_set_hash(manifest)
        return manifest

    def _registry_event(self, spec: DryRunArtifactSetSpec, manifest: dict[str, Any], *, previous_status: str | None, new_status: str, event_type: str, manifest_path: Path) -> dict[str, Any]:
        set_hash = manifest["artifact_set_hash"]
        return {
            "event_id": None,
            "event_type": event_type,
            "event_schema_version": "artifact_registry_event.v1",
            "event_created_at": utc_now(),
            "actor_type": "VALIDATION_TOOL",
            "actor_id": "phase16am-dry-run",
            "authority_ref": "Phase16-AM isolated dry run",
            "logical_artifact_id": spec.set_id,
            "artifact_instance_id": f"{spec.set_id}@sha256-{set_hash[:16]}",
            "artifact_type": "ARTIFACT_SET",
            "component": spec.component,
            "artifact_version": "dry-run-v1",
            "previous_status": previous_status,
            "new_status": new_status,
            "runtime_use_eligible": False,
            "physical_path": None,
            "content_hash": set_hash,
            "schema_version": manifest["schema_version"],
            "schema_hash": stable_json_hash(manifest["schema_hashes"]),
            "artifact_set_id": spec.set_id,
            "artifact_set_type": spec.set_type,
            "business_date": None,
            "feature_date": None,
            "as_of": None,
            "producer": "FormalRegistrationDryRun",
            "producer_version": DRY_RUN_VERSION,
            "consumer_compatibility": [],
            "source_refs": [str(manifest_path)],
            "source_hashes": [{"ref": str(manifest_path), "hash": sha256_file_bytes(manifest_path)}],
            "point_in_time_status": "NOT_APPLICABLE",
            "retention_class": "DRY_RUN",
            "path_classification": "ARTIFACT_SET_MANIFEST",
            "migration_status": new_status,
            "review_ref": None,
            "regression_ref": None,
            "acceptance_report_ref": None,
            "reason": "Phase16-AM isolated formal registration dry run",
            "supersedes_event_id": None,
            "previous_physical_path": None,
            "new_physical_path": None,
        }

    def _acceptance_evidence(self, spec: DryRunArtifactSetSpec, manifest: dict[str, Any], manifest_path: Path, set_root: Path) -> dict[str, Any]:
        report_path = write_json(set_root / "acceptance_report.json", self._acceptance_report(manifest, manifest_path))
        regression_path = write_json(set_root / "regression_evidence.json", self._regression_evidence(manifest, spec.set_type))
        approval_paths = [write_json(set_root / "approvals" / f"{role}.json", self._approval(role, manifest, report_path)) for role in APPROVAL_ROLES]
        generic = self._generic_evidence(manifest)
        source_path = write_json(set_root / "source_lineage.json", generic)
        freeze_path = write_json(set_root / "freeze_manifest.json", generic)
        consumer_path = write_json(set_root / "consumer_compatibility.json", generic)
        paths = AcceptanceEvidencePaths(
            artifact_set_manifest=manifest_path,
            acceptance_report=report_path,
            regression_evidence=regression_path,
            approvals=tuple(approval_paths),
            source_lineage=source_path,
            freeze_manifest=freeze_path,
            consumer_compatibility=consumer_path,
        )
        bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=self.repo_root).build_bundle()
        validation = AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=self.repo_root).validate()
        if validation["validation_result"]["overall_result"] != "PASS":
            raise RuntimeError(f"Acceptance Evidence validation failed for {spec.set_id}: {validation['validation_result']['errors']}")
        bundle_path = write_json(set_root / "acceptance_evidence_bundle.json", bundle)
        validation_path = write_json(set_root / "acceptance_validation_result.json", validation["validation_result"])
        return {
            "bundle_path": bundle_path,
            "validation_result_path": validation_path,
            "acceptance_report_path": report_path,
            "regression_evidence_path": regression_path,
            "approval_paths": approval_paths,
        }

    def _acceptance_report(self, manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
        return {
            "schema_version": "artifact_acceptance_report.v1",
            "acceptance_report_id": f"acceptance-report-{uuid.uuid4()}",
            "artifact_or_set_ref": manifest["artifact_set_id"],
            "artifact_set_id": manifest["artifact_set_id"],
            "artifact_set_type": manifest["artifact_set_type"],
            "artifact_set_manifest_ref": str(manifest_path),
            "artifact_set_hash": manifest["artifact_set_hash"],
            "reviewed_artifact_hashes": manifest["member_hashes"],
            "reviewed_member_hashes": manifest["member_hashes"],
            "reviewed_schema_hashes": manifest["schema_hashes"],
            "reviewed_source_refs": manifest["runtime_consumer_refs"],
            "evidence_bundle_ref": None,
            "human_reviewer": "phase16am-dry-run",
            "architecture_reviewer": "phase16am-dry-run",
            "regression_reviewer": "phase16am-dry-run",
            "release_approver": "phase16am-dry-run",
            "review_started_at": utc_now(),
            "review_completed_at": utc_now(),
            "decision": "ACCEPT",
            "acceptance_criteria_results": {},
            "regression_results": [],
            "regression_result": "PASS",
            "consumer_compatibility_result": "PASS",
            "point_in_time_result": "PASS",
            "known_limitations": ["Dry Run only; no production copy or formal Registry mutation."],
            "risk_classification": "LOW",
            "rollback_target": None,
            "rollback_target_ref": None,
            "replacement_target": None,
            "git_commit": None,
            "runtime_version": None,
            "feature_schema_version": None,
            "canonical_data_manifest_ref": None,
            "model_freeze_manifest_ref": None,
            "approval_signatures": [],
            "notes": "Phase16-AM isolated dry run acceptance evidence.",
        }

    def _regression_evidence(self, manifest: dict[str, Any], set_type: str) -> dict[str, Any]:
        payload = {
            "schema_version": "artifact_regression_evidence.v1",
            "regression_evidence_id": f"regression-{uuid.uuid4()}",
            "artifact_or_set_ref": manifest["artifact_set_id"],
            "artifact_set_id": manifest["artifact_set_id"],
            "artifact_set_type": set_type,
            "profile": {
                "CANDIDATE_AI_SET": "CANDIDATE",
                "OPPORTUNITY_AI_SET": "OPPORTUNITY",
                "POSITION_MANAGEMENT_POLICY_SET": "PM",
                "CAPITAL_ALLOCATION_POLICY_SET": "CAPITAL_ALLOCATION",
            }.get(set_type, "REGISTRY_PATH_ONLY"),
            "test_scope": "registration_workflow",
            "test_command": None,
            "test_environment": "isolated_registry",
            "before_refs": [],
            "after_refs": [],
            "baseline_ref": "pre-registration",
            "candidate_ref": manifest["artifact_set_id"],
            "semantic_comparison": "PASS",
            "semantic_equality_result": "PASS",
            "hash_comparison": "PASS",
            "schema_comparison": "PASS",
            "candidate_decision_parity": "PASS",
            "opportunity_decision_parity": "PASS" if set_type == "OPPORTUNITY_AI_SET" else "NOT_APPLICABLE",
            "pm_decision_parity": "PASS" if set_type == "POSITION_MANAGEMENT_POLICY_SET" else "NOT_APPLICABLE",
            "capital_allocation_parity": "PASS" if set_type == "CAPITAL_ALLOCATION_POLICY_SET" else "NOT_APPLICABLE",
            "planning_parity": "PASS",
            "pending_parity": "PASS",
            "submit_guard_parity": "PASS",
            "consumer_compatibility_result": "PASS",
            "point_in_time_result": "PASS",
            "planning_unchanged": True,
            "submit_unchanged": True,
            "current_unchanged": True,
            "ledger_unchanged": True,
            "pending_unchanged": True,
            "runtime_state_unchanged": True,
            "result": "PASS",
            "evidence_hash": None,
            "failures": [],
            "timestamp_only_differences": [],
            "reviewer": "phase16am-dry-run",
        }
        return payload

    def _approval(self, role: str, manifest: dict[str, Any], report_path: Path) -> dict[str, Any]:
        return {
            "schema_version": "artifact_review_approval.v1",
            "approval_id": f"approval-{uuid.uuid4()}",
            "approval_type": role,
            "approval_role": role,
            "subject_type": "ARTIFACT_SET",
            "subject_ref": manifest["artifact_set_id"],
            "artifact_set_type": manifest["artifact_set_type"],
            "reviewer_id": "phase16am-dry-run",
            "reviewer_role": "dry-run",
            "reviewed_hash": manifest["artifact_set_hash"],
            "decision": "APPROVED",
            "approved_at": utc_now(),
            "evidence_refs": [str(report_path)],
            "conditions": [],
            "expires_at": None,
            "supersedes_approval_id": None,
        }

    def _generic_evidence(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            "subject_ref": manifest["artifact_set_id"],
            "artifact_set_id": manifest["artifact_set_id"],
            "artifact_set_type": manifest["artifact_set_type"],
            "member_hashes": manifest["member_hashes"],
            "hashes": manifest["member_hashes"],
            "consumer_id": "Runtime",
            "consumer_version": "dry-run",
            "expected_member_roles": manifest["required_member_roles"],
            "result": "PASS",
            "compatibility_result": "PASS",
            "automatic_retraining": False,
            "scheduler_retraining": False,
        }


def protected_hashes(repo_root: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "formal_event_log": ".runtime/artifact_registry/events/registry_events.jsonl",
        "formal_index": ".runtime/artifact_registry/index/registry_index.json",
        "formal_checkpoint": ".runtime/artifact_registry/checkpoints/latest.json",
        "current": ".runtime/runtime_state/current_state.json",
        "ledger": ".runtime/persistent_ledger/state.json",
        "pending": ".runtime/pending_order_plan/pending_order_plan.json",
        "runtime_market": ".runtime/runtime_state/market/latest.json",
        "candidate_model": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
        "opportunity_artifact": ".runtime/phase9/inference/2026-06-26/opportunity_artifact.json",
        "pm_policy": ".runtime/phase9/policy_manifests/position_policy_manifest.json",
        "capital_policy": ".runtime/phase9/policy_manifests/capital_policy_manifest.json",
        "feature": ".runtime/phase9/features/2026-06-26/candidate_features.parquet",
    }
    result: dict[str, dict[str, Any]] = {}
    for key, rel in paths.items():
        path = repo_root / rel
        data = path.read_bytes() if path.exists() else b""
        result[key] = {"path": rel, "exists": path.exists(), "size": len(data), "sha256": stable_json_hash({"missing": rel}) if not path.exists() else __import__("hashlib").sha256(data).hexdigest()}
    return result


def run_formal_registration_dry_run(*, output_root: Path = DEFAULT_OUTPUT_ROOT, repo_root: Path | None = None) -> dict[str, Any]:
    return FormalRegistrationDryRun(output_root=output_root, repo_root=repo_root or Path.cwd()).run()
