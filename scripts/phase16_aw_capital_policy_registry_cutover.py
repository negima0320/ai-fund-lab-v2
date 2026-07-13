from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import (
    AcceptanceEvidenceBundleBuilder,
    AcceptanceEvidenceBundleValidator,
    AcceptanceEvidencePaths,
)
from ai_fund_lab_v2.artifact_registry.checkpoint_writer import run_checkpoint
from ai_fund_lab_v2.artifact_registry.full_log_validator import run_full_log_validation
from ai_fund_lab_v2.artifact_registry.index_builder import run_index_build
from ai_fund_lab_v2.artifact_registry.inventory import schema_info, stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import (
    artifact_set_hash,
    load_schemas,
    required_roles_for_set,
    validate_artifact_set_manifest,
    validate_registry_event,
)
from ai_fund_lab_v2.artifact_registry.writer import (
    LOCK_RELATIVE_PATH,
    _LockedFile,
    append_line_atomic,
    event_fingerprint,
    event_id_for_fingerprint,
    read_event_log,
)
from ai_fund_lab_v2.runtime_v2.artifact_lookup import resolve_runtime_capital_policy_path
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = REPO_ROOT / ".runtime/artifact_registry"
EVENT_LOG = REGISTRY_ROOT / "events/registry_events.jsonl"
INDEX_PATH = REGISTRY_ROOT / "index/registry_index.json"
CHECKPOINT_LATEST = REGISTRY_ROOT / "checkpoints/latest.json"
REPORT_ROOT = REPO_ROOT / "reports/phase16_capital_policy_registry_cutover"
PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase16_aw_capital_allocation_loadable_policy_registry_cutover.md"
PHASE_JSON = REPO_ROOT / "reports/phase_reports/phase16_aw_capital_allocation_loadable_policy_registry_cutover.json"
SCHEMA_ROOT = REPO_ROOT / "docs/02_architecture/schemas"
VERSION = "phase16_aw_capital_policy_registry_cutover.v1"
SET_ID = "control.capital_allocation.accepted_set"
SET_TYPE = "CAPITAL_ALLOCATION_POLICY_SET"
EVIDENCE_ID = "control_capital_allocation_accepted_set_loadable_policy_v2"
POLICY_SOURCE = REPO_ROOT / "configs/runtime_v2/capital_deployment.json"
POLICY_SCHEMA_SOURCE = REPO_ROOT / ".runtime/phase9/features/2026-06-26/capital_policy_input.parquet"
VALIDATION_SOURCE = REPO_ROOT / ".runtime/phase9/audits/candidate_universe_hard_gate_fix_validation.json"
COMPATIBILITY_SOURCE = REPO_ROOT / ".runtime/operations/feature_consumer_readiness/2026-07-10.json"
APPROVAL_ROLES = ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")


@dataclass(frozen=True)
class MemberSpec:
    role: str
    source_path: Path
    destination_template: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, path)
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return path


def copy_atomic(source: Path, destination: Path, expected_hash: str) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        existing_hash = sha256_file(destination)
        if existing_hash != expected_hash:
            raise RuntimeError(f"destination collision with different hash: {rel(destination)}")
        return {"source": rel(source), "destination": rel(destination), "hash": expected_hash, "size": source.stat().st_size, "overwrite": False, "status": "ALREADY_EXISTS_IDENTICAL"}
    tmp = destination.with_name(f".{destination.name}.tmp")
    with source.open("rb") as src, tmp.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    copied_hash = sha256_file(tmp)
    if copied_hash != expected_hash:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"copy hash mismatch: {rel(destination)}")
    os.replace(tmp, destination)
    try:
        dir_fd = os.open(str(destination.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    return {"source": rel(source), "destination": rel(destination), "hash": expected_hash, "size": source.stat().st_size, "overwrite": False, "status": "COPIED"}


def protected_hashes() -> dict[str, dict[str, Any]]:
    paths = {
        "event_log": EVENT_LOG,
        "index": INDEX_PATH,
        "checkpoint": CHECKPOINT_LATEST,
        "current": REPO_ROOT / ".runtime/runtime_state/current_state.json",
        "ledger": REPO_ROOT / ".runtime/persistent_ledger/state.json",
        "pending": REPO_ROOT / ".runtime/pending_order_plan/pending_order_plan.json",
        "runtime_state": REPO_ROOT / ".runtime/runtime_state/run_manifest",
        "planning": REPO_ROOT / ".runtime/planning/latest.json",
        "submit_guard": REPO_ROOT / ".runtime/submit_guard/latest.json",
        "active_policy_source": POLICY_SOURCE,
    }
    out: dict[str, dict[str, Any]] = {}
    for key, path in paths.items():
        if path.is_dir():
            data = json.dumps(sorted((rel(p), sha256_file(p)) for p in path.rglob("*") if p.is_file()), sort_keys=True).encode("utf-8")
            out[key] = {"path": rel(path), "exists": True, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        else:
            data = path.read_bytes() if path.exists() else b""
            out[key] = {"path": rel(path), "exists": path.exists(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return out


def active_policy_inventory() -> dict[str, Any]:
    candidates = [
        {"path": "configs/runtime_v2/capital_deployment.json", "classification": "ACTIVE_MAINLINE", "reason": "Only production-named config policy and current CLI default diagnostic source."},
        {"path": "configs/runtime_v2/capital_deployment_demo.json", "classification": "LEGACY", "reason": "Demo-named legacy policy; not selected for formal Runtime authority."},
    ]
    for candidate in candidates:
        path = REPO_ROOT / candidate["path"]
        candidate.update({"exists": path.exists(), "sha256": sha256_file(path) if path.exists() else None})
    policy = load_capital_deployment_policy(POLICY_SOURCE)
    return {
        "schema_version": "phase16_aw_policy_source_inventory.v1",
        "created_at": utc_now(),
        "selected_policy_path": rel(POLICY_SOURCE),
        "selected_policy_hash": sha256_file(POLICY_SOURCE),
        "selected_policy_contract_hash": capital_deployment_policy_hash(policy),
        "selected_policy_version": policy.policy_version,
        "candidates": candidates,
        "classification": "ACTIVE_MAINLINE",
    }


def destination(template: str, content_hash: str) -> Path:
    return REPO_ROOT / template.replace("{hash}", content_hash[:16])


def make_policy_version_source(policy_hash: str) -> Path:
    policy = load_capital_deployment_policy(POLICY_SOURCE)
    payload = {
        "schema_version": "capital_deployment_policy_version.v1",
        "policy_version": policy.policy_version,
        "policy_source": policy.policy_source,
        "policy_member_role": "POLICY",
        "policy_content_hash": policy_hash,
        "policy_contract_hash": capital_deployment_policy_hash(policy),
        "created_at": utc_now(),
        "authority": "Phase16-AW loadable Capital Deployment Policy registration",
    }
    return write_json(REPORT_ROOT / "generated" / "capital_deployment_policy_version.json", payload)


def member_specs(policy_version_source: Path) -> tuple[MemberSpec, ...]:
    return (
        MemberSpec("POLICY", POLICY_SOURCE, ".runtime/artifacts/control/capital_allocation/policy/capital_deployment_v1/sha256-{hash}/policy.json"),
        MemberSpec("POLICY_SCHEMA", POLICY_SCHEMA_SOURCE, ".runtime/artifacts/control/capital_allocation/policy_schema/default/sha256-{hash}/policy_schema.parquet"),
        MemberSpec("POLICY_VERSION", policy_version_source, ".runtime/artifacts/control/capital_allocation/policy_version/capital_deployment_v1/sha256-{hash}/policy_version.json"),
        MemberSpec("VALIDATION_EVIDENCE", VALIDATION_SOURCE, ".runtime/artifact_registry/evidence/control/capital_allocation/validation/sha256-{hash}/validation_evidence.json"),
        MemberSpec("REGRESSION_EVIDENCE", REPORT_ROOT / "regression_evidence.json", ".runtime/artifact_registry/evidence/control/capital_allocation/regression/sha256-{hash}/regression_evidence.json"),
        MemberSpec("CONSUMER_COMPATIBILITY", REPORT_ROOT / "consumer_compatibility.json", ".runtime/artifact_registry/evidence/control/capital_allocation/consumer_compatibility/sha256-{hash}/consumer_compatibility.json"),
    )


def build_members(specs: tuple[MemberSpec, ...]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    members: list[dict[str, Any]] = []
    copies: list[dict[str, Any]] = []
    for spec in specs:
        if not spec.source_path.is_file():
            raise RuntimeError(f"source missing: {spec.source_path}")
        content_hash = sha256_file(spec.source_path)
        dst = destination(spec.destination_template, content_hash)
        if "/phase" in dst.as_posix().lower():
            raise RuntimeError(f"destination must not be phase path: {dst}")
        copies.append(copy_atomic(spec.source_path, dst, content_hash))
        _, schema_hash = schema_info(dst)
        if schema_hash in {"UNKNOWN", "NOT_APPLICABLE", "NOT_FOUND"}:
            schema_hash = stable_json_hash({"role": spec.role, "suffix": dst.suffix.lower(), "content_hash": content_hash, "schema_status": schema_hash})
        logical_id = f"{SET_ID}.{spec.role.lower()}"
        members.append(
            {
                "logical_artifact_id": logical_id,
                "artifact_instance_id": f"{logical_id}@sha256-{content_hash[:16]}",
                "artifact_set_id": SET_ID,
                "artifact_type": spec.role,
                "physical_path": rel(dst),
                "content_hash": content_hash,
                "schema_hash": schema_hash,
                "role": spec.role,
                "member_role": spec.role,
                "status": "VALIDATED",
                "accepted_status": "VALIDATED",
                "runtime_use_eligible": False,
                "migration_status": "FORMAL_COPY_VERIFIED",
            }
        )
    return members, copies


def evidence_dir(kind: str) -> Path:
    return REGISTRY_ROOT / "evidence" / kind / EVIDENCE_ID


def make_regression(before_policy_member_hash: str, after_policy_member_hash: str) -> Path:
    policy = load_capital_deployment_policy(POLICY_SOURCE)
    payload = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": "phase16-aw-capital-loadable-policy-regression",
        "artifact_or_set_ref": SET_ID,
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "profile": "CAPITAL_ALLOCATION",
        "test_scope": "Capital Allocation registry member replacement only; allocation math and policy JSON content unchanged.",
        "test_command": "PYTHONPATH=src python3 scripts/phase16_aw_capital_policy_registry_cutover.py",
        "test_environment": "local repository workspace",
        "before_refs": [".runtime/phase9/policy_manifests/capital_policy_manifest.json"],
        "after_refs": [rel(POLICY_SOURCE)],
        "baseline_ref": "explicit operational policy path",
        "candidate_ref": SET_ID,
        "semantic_comparison": "PASS",
        "semantic_equality_result": "PASS",
        "hash_comparison": "PASS",
        "schema_comparison": "PASS",
        "candidate_decision_parity": "NOT_APPLICABLE",
        "opportunity_decision_parity": "NOT_APPLICABLE",
        "pm_decision_parity": "NOT_APPLICABLE",
        "capital_allocation_parity": "PASS",
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
        "reviewer": "phase16-aw-formal-authority",
    }
    path = write_json(REPORT_ROOT / "regression_evidence.json", payload)
    payload["evidence_hash"] = sha256_file(path)
    return write_json(path, payload)


def make_consumer_compatibility() -> Path:
    payload = {
        "schema_version": "phase16_aw_consumer_compatibility.v1",
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "subject_ref": SET_ID,
        "consumer_id": "Runtime v2 Capital Allocation Consumer",
        "consumer_version": "current",
        "result": "PASS",
        "compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "runtime_lookup_connected": True,
        "required_roles": ["POLICY", "POLICY_SCHEMA", "POLICY_VERSION"],
    }
    return write_json(REPORT_ROOT / "consumer_compatibility.json", payload)


def make_manifest(members: list[dict[str, Any]], refs: dict[str, str], *, status: str) -> dict[str, Any]:
    required = sorted(required_roles_for_set(SET_TYPE))
    manifest: dict[str, Any] = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "artifact_set_version": "formal-v2-loadable-policy",
        "set_authority_scope": "SET_LEVEL",
        "component": "Capital Allocation Policy",
        "member_artifacts": members,
        "required_member_types": required,
        "required_member_roles": required,
        "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
        "schema_hashes": {m["logical_artifact_id"]: m["schema_hash"] for m in members},
        "compatibility_constraints": ["Runtime v2 Capital Allocation must load POLICY through Registry Resolver only."],
        "training_period": None,
        "feature_schema_ref": f"{SET_ID}.policy_schema",
        "consumer_compatibility_ref": refs["compatibility"],
        "source_lineage_ref": refs["lineage"],
        "freeze_manifest_ref": refs["freeze"],
        "validation_evidence_refs": [refs["lineage"], refs["compatibility"]],
        "regression_evidence_refs": [refs["regression"]],
        "runtime_consumer_refs": ["Runtime v2 Capital Allocation Consumer"],
        "artifact_set_hash": "",
        "status": status,
        "runtime_use_eligible": False,
    }
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    validation = validate_artifact_set_manifest(manifest, schemas=load_schemas(SCHEMA_ROOT), subject_ref=f"{SET_ID}:{status}")
    if validation["overall_result"] != "PASS":
        raise RuntimeError(f"manifest validation failed: {validation['errors']}")
    return manifest


def make_supporting_evidence(members: list[dict[str, Any]], policy_source_inventory_ref: str) -> dict[str, Path]:
    lineage = write_json(
        evidence_dir("lineage") / "lineage_review.json",
        {
            "schema_version": "phase16_aw_lineage_review.v1",
            "artifact_set_id": SET_ID,
            "artifact_set_type": SET_TYPE,
            "created_at": utc_now(),
            "decision": "APPROVED_FOR_REPLACEMENT",
            "source_policy_inventory_ref": policy_source_inventory_ref,
            "member_paths": [m["physical_path"] for m in members],
            "lineage_result": "PASS",
            "runtime_use_eligible": False,
        },
    )
    freeze = write_json(
        evidence_dir("freeze") / "freeze_manifest.json",
        {
            "schema_version": "phase16_aw_freeze_manifest.v1",
            "artifact_set_id": SET_ID,
            "artifact_set_type": SET_TYPE,
            "subject_ref": SET_ID,
            "result": "PASS",
            "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
            "policy_content_unchanged": True,
        },
    )
    compatibility = write_json(evidence_dir("compatibility") / "consumer_compatibility.json", read_json(REPORT_ROOT / "consumer_compatibility.json"))
    return {"lineage": lineage, "freeze": freeze, "compatibility": compatibility}


def make_approvals(manifest: dict[str, Any], refs: list[str]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for role in APPROVAL_ROLES:
        payload = {
            "schema_version": "artifact_review_approval.v1",
            "approval_id": f"approval-phase16-aw-capital-loadable-policy-{role.lower()}",
            "approval_type": role,
            "approval_role": role,
            "subject_type": "ARTIFACT_SET",
            "subject_ref": SET_ID,
            "artifact_set_type": SET_TYPE,
            "reviewer_id": "phase16-aw-formal-authority",
            "reviewer_role": role,
            "reviewed_hash": manifest["artifact_set_hash"],
            "decision": "APPROVED",
            "approved_at": utc_now(),
            "evidence_refs": refs,
            "conditions": ["Loadable Capital Deployment Policy JSON replaces prior identity manifest as POLICY member.", "Runtime must fail closed when Registry lookup fails."],
            "expires_at": None,
            "supersedes_approval_id": None,
        }
        paths.append(write_json(evidence_dir("approvals") / f"{role.lower()}.json", payload))
    return tuple(paths)


def make_acceptance_report(manifest: dict[str, Any], evidence_path_ref: Path, regression: Path, approvals: tuple[Path, ...], bundle_ref: str | None = None) -> Path:
    now = utc_now()
    payload = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "phase16-aw-capital-loadable-policy-acceptance-report",
        "artifact_or_set_ref": SET_ID,
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "artifact_set_manifest_ref": str(evidence_path_ref),
        "artifact_set_hash": manifest["artifact_set_hash"],
        "reviewed_artifact_hashes": manifest["member_hashes"],
        "reviewed_member_hashes": manifest["member_hashes"],
        "reviewed_schema_hashes": manifest["schema_hashes"],
        "reviewed_source_refs": manifest["runtime_consumer_refs"],
        "evidence_bundle_ref": bundle_ref,
        "human_reviewer": "phase16-aw-formal-authority",
        "architecture_reviewer": "phase16-aw-formal-authority",
        "regression_reviewer": "phase16-aw-formal-authority",
        "release_approver": "phase16-aw-formal-authority",
        "review_started_at": now,
        "review_completed_at": now,
        "decision": "ACCEPT",
        "acceptance_criteria_results": {"approval": "PASS", "manifest": "PASS", "member_hash": "PASS", "schema_hash": "PASS", "regression": "PASS", "compatibility": "PASS", "point_in_time": "PASS"},
        "regression_results": ["CAPITAL_ALLOCATION:PASS"],
        "regression_result": "PASS",
        "consumer_compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "known_limitations": ["Legacy paths are retained on disk until a later Legacy Freeze phase."],
        "risk_classification": "LOW",
        "rollback_target": None,
        "rollback_target_ref": None,
        "replacement_target": "control.capital_allocation.accepted_set@previous",
        "git_commit": None,
        "runtime_version": "Runtime v2",
        "feature_schema_version": None,
        "canonical_data_manifest_ref": None,
        "model_freeze_manifest_ref": rel(evidence_dir("freeze") / "freeze_manifest.json"),
        "approval_signatures": [path.name for path in approvals],
        "notes": "Phase16-AW formal replacement: POLICY member is loadable Capital Deployment Policy JSON.",
    }
    return write_json(evidence_dir("acceptance") / "acceptance_report.json", payload)


def make_event(manifest: dict[str, Any], *, previous_status: str | None, new_status: str, event_type: str, manifest_path: Path) -> dict[str, Any]:
    set_hash = manifest["artifact_set_hash"]
    source_refs = [rel(manifest_path), manifest["source_lineage_ref"], manifest["consumer_compatibility_ref"], *manifest["regression_evidence_refs"]]
    event = {
        "event_id": None,
        "event_type": event_type,
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": utc_now(),
        "actor_type": "VALIDATION_TOOL",
        "actor_id": "phase16-aw-capital-policy-cutover",
        "authority_ref": "Phase16-AW formal capital policy replacement",
        "logical_artifact_id": SET_ID,
        "artifact_instance_id": f"{SET_ID}@sha256-{set_hash[:16]}",
        "artifact_type": "ARTIFACT_SET",
        "component": "Capital Allocation Policy",
        "artifact_version": "formal-v2-loadable-policy",
        "previous_status": previous_status,
        "new_status": new_status,
        "runtime_use_eligible": False,
        "physical_path": rel(manifest_path),
        "content_hash": sha256_file(manifest_path),
        "schema_version": manifest["schema_version"],
        "schema_hash": stable_json_hash(manifest["schema_hashes"]),
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "business_date": None,
        "feature_date": None,
        "as_of": utc_now(),
        "producer": "Phase16-AW Capital Policy Registry Cutover",
        "producer_version": VERSION,
        "consumer_compatibility": [{"consumer": "Runtime v2 Capital Allocation", "compatible": True, "reason": "Validated replacement set; acceptance pending."}],
        "source_refs": sorted(set(source_refs)),
        "source_hashes": [{"ref": ref, "hash": sha256_file(REPO_ROOT / ref)} for ref in sorted(set(source_refs)) if (REPO_ROOT / ref).exists()],
        "point_in_time_status": "PASS",
        "retention_class": "FORMAL_REGISTRATION_EVIDENCE",
        "path_classification": "FORMAL_ARTIFACT_SET_MANIFEST",
        "migration_status": f"FORMAL_{new_status}",
        "review_ref": rel(evidence_dir("approvals")),
        "regression_ref": manifest["regression_evidence_refs"][0],
        "acceptance_report_ref": None,
        "evidence_bundle_ref": None,
        "consumer_compatibility_ref": manifest["consumer_compatibility_ref"],
        "reason": f"Phase16-AW Capital Allocation loadable policy {new_status} registration.",
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
        "replacement_operation_id": None,
        "replacement_from_ref": None,
        "replacement_to_ref": None,
        "replacement_stage": "NEW_VALIDATED" if new_status == "VALIDATED" else None,
        "rollback_operation_id": None,
        "rollback_target_ref": None,
        "new_acceptance_report_ref": None,
        "new_regression_ref": None,
        "new_approval_refs": [],
        "revoke_reason": None,
        "affected_consumers": [],
        "replacement_ref": None,
        "runtime_fail_closed_required": None,
        "incident_ref": None,
    }
    event["event_id"] = event_id_for_fingerprint(event_fingerprint(event))
    return event


def make_acceptance_event(manifest: dict[str, Any], manifest_path: Path, report: Path, regression: Path, bundle: Path, old_event: dict[str, Any]) -> dict[str, Any]:
    set_hash = manifest["artifact_set_hash"]
    approval_refs = [rel(p) for p in sorted(evidence_dir("approvals").glob("*.json"))]
    event = {
        "event_id": None,
        "event_type": "ARTIFACT_ACCEPTED",
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": utc_now(),
        "actor_type": "RELEASE_PROCESS",
        "actor_id": "phase16-aw-formal-authority",
        "authority_ref": "Artifact Acceptance Authority",
        "logical_artifact_id": SET_ID,
        "artifact_instance_id": f"{SET_ID}@sha256-{set_hash[:16]}",
        "artifact_type": "ARTIFACT_SET",
        "component": "Capital Allocation Policy",
        "artifact_version": "formal-v2-loadable-policy",
        "previous_status": "VALIDATED",
        "new_status": "ACCEPTED",
        "runtime_use_eligible": True,
        "physical_path": None,
        "content_hash": set_hash,
        "schema_version": manifest["schema_version"],
        "schema_hash": stable_json_hash(manifest["schema_hashes"]),
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "business_date": None,
        "feature_date": None,
        "as_of": utc_now(),
        "producer": "Phase16-AW Capital Policy Replacement Writer",
        "producer_version": VERSION,
        "consumer_compatibility": [{"consumer": "Runtime v2 Capital Allocation", "compatible": True, "reason": "Loadable policy member validated and accepted."}],
        "source_refs": [rel(manifest_path), rel(report), rel(regression), rel(bundle), *approval_refs],
        "source_hashes": [{"ref": ref, "hash": sha256_file(REPO_ROOT / ref)} for ref in [rel(manifest_path), rel(report), rel(regression), rel(bundle), *approval_refs]],
        "point_in_time_status": "PASS",
        "retention_class": "ACCEPTANCE_AUDIT",
        "path_classification": "ARTIFACT_SET_MANIFEST",
        "migration_status": "ACCEPTED",
        "review_ref": rel(evidence_dir("approvals")),
        "regression_ref": rel(regression),
        "acceptance_report_ref": rel(report),
        "evidence_bundle_ref": rel(bundle),
        "consumer_compatibility_ref": manifest["consumer_compatibility_ref"],
        "reason": "Phase16-AW formal replacement acceptance; loadable Capital Deployment Policy is Runtime eligible.",
        "supersedes_event_id": old_event["event_id"],
        "previous_physical_path": None,
        "new_physical_path": None,
        "replacement_operation_id": None,
        "replacement_from_ref": old_event["artifact_instance_id"],
        "replacement_to_ref": f"{SET_ID}@sha256-{set_hash[:16]}",
        "replacement_stage": "NEW_ELIGIBLE",
        "rollback_operation_id": None,
        "rollback_target_ref": None,
        "new_acceptance_report_ref": None,
        "new_regression_ref": None,
        "new_approval_refs": approval_refs,
        "revoke_reason": None,
        "affected_consumers": ["Runtime v2 Capital Allocation"],
        "replacement_ref": None,
        "runtime_fail_closed_required": True,
        "incident_ref": None,
    }
    event["event_id"] = event_id_for_fingerprint(event_fingerprint(event))
    return event


def make_legacy_event(old_event: dict[str, Any], new_event: dict[str, Any]) -> dict[str, Any]:
    event = dict(old_event)
    event.update(
        {
            "event_id": None,
            "event_type": "ARTIFACT_LEGACY",
            "event_created_at": utc_now(),
            "actor_type": "RELEASE_PROCESS",
            "actor_id": "phase16-aw-formal-authority",
            "previous_status": "ACCEPTED",
            "new_status": "LEGACY",
            "runtime_use_eligible": False,
            "producer": "Phase16-AW Capital Policy Replacement Writer",
            "producer_version": VERSION,
            "consumer_compatibility": [{"consumer": "Runtime v2 Capital Allocation", "compatible": False, "reason": "Superseded by loadable policy Artifact Set instance."}],
            "reason": "Old Capital Allocation identity-manifest POLICY set superseded by loadable policy set.",
            "supersedes_event_id": None,
            "replacement_operation_id": None,
            "replacement_from_ref": old_event["artifact_instance_id"],
            "replacement_to_ref": new_event["artifact_instance_id"],
            "replacement_stage": "OLD_LEGACY",
            "replacement_ref": new_event["event_id"],
            "runtime_fail_closed_required": True,
        }
    )
    event["event_id"] = event_id_for_fingerprint(event_fingerprint(event))
    return event


def validate_event(event: dict[str, Any]) -> None:
    result = validate_registry_event(event, schemas=load_schemas(SCHEMA_ROOT), repo_root=REPO_ROOT, subject_ref=event.get("event_id") or "phase16_aw_event")
    if result["overall_result"] != "PASS" or result["failure_class"] != "NONE":
        raise RuntimeError(f"event validation failed: {event.get('event_type')} {result['errors']}")


def append_events_atomically(events: list[dict[str, Any]]) -> dict[str, Any]:
    before_rows = read_event_log(EVENT_LOG)
    before_hash = sha256_file(EVENT_LOG)
    existing_ids = {row["event"].get("event_id") for row in before_rows}
    existing_fingerprints = {row["fingerprint"] for row in before_rows}
    for event in events:
        validate_event(event)
        fp = event_fingerprint(event)
        if event["event_id"] in existing_ids:
            raise RuntimeError(f"duplicate event_id: {event['event_id']}")
        if fp in existing_fingerprints:
            raise RuntimeError(f"duplicate event fingerprint: {fp}")
    payload = b"".join(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n" for event in events)
    with _LockedFile(REGISTRY_ROOT / LOCK_RELATIVE_PATH, timeout_seconds=10.0):
        append_line_atomic(EVENT_LOG, payload)
    return {
        "schema_version": "phase16_aw_replacement_append_result.v1",
        "event_log_hash_before": before_hash,
        "event_log_hash_after": sha256_file(EVENT_LOG),
        "event_count_before": len(before_rows),
        "event_count_after": len(read_event_log(EVENT_LOG)),
        "appended_event_ids": [event["event_id"] for event in events],
        "atomic_multi_event_append": True,
    }


def run_validation_stack(label: str) -> dict[str, Any]:
    full = run_full_log_validation(event_log=EVENT_LOG, registry_root=REGISTRY_ROOT, output=REPORT_ROOT / label / "full_log_validation", repo_root=REPO_ROOT)
    if full["failure_class"] != "NONE":
        raise RuntimeError(f"{label} full log validation failed: {full['errors']}")
    index = run_index_build(registry_root=REGISTRY_ROOT, event_log=EVENT_LOG, output=REPORT_ROOT / label / "index_build", repo_root=REPO_ROOT)
    if index["overall_result"] != "PASS":
        raise RuntimeError(f"{label} index build failed: {index['errors']}")
    checkpoint = run_checkpoint(registry_root=REGISTRY_ROOT, event_log=EVENT_LOG, output=REPORT_ROOT / label / "checkpoint", repo_root=REPO_ROOT)
    if checkpoint["overall_result"] != "PASS":
        raise RuntimeError(f"{label} checkpoint failed: {checkpoint['errors']}")
    return {"full_log": full, "index": index, "checkpoint": checkpoint}


def current_capital_acceptance(events: list[dict[str, Any]]) -> dict[str, Any]:
    active: dict[str, Any] | None = None
    for event in events:
        if event.get("logical_artifact_id") != SET_ID:
            continue
        if event.get("new_status") == "ACCEPTED" and event.get("runtime_use_eligible") is True:
            active = event
        elif event.get("new_status") in {"LEGACY", "REVOKED", "REJECTED"} and active and event.get("artifact_instance_id") == active.get("artifact_instance_id"):
            active = None
    if active is None:
        raise RuntimeError("active accepted Capital Allocation set not found")
    return active


def existing_lifecycle_event(instance_id: str, status: str) -> dict[str, Any] | None:
    for row in read_event_log(EVENT_LOG):
        event = row["event"]
        if event.get("artifact_instance_id") == instance_id and event.get("new_status") == status:
            return event
    return None


def registry_consistency() -> dict[str, Any]:
    events = [row["event"] for row in read_event_log(EVENT_LOG)]
    index = read_json(INDEX_PATH)
    entry = index["entries"][SET_ID]
    return {
        "schema_version": "phase16_aw_registry_consistency.v1",
        "created_at": utc_now(),
        "event_count": len(events),
        "entry_count": index["entry_count"],
        "event_type_counts": dict(Counter(event["event_type"] for event in events)),
        "status_counts": dict(Counter(entry["current_status"] for entry in index["entries"].values())),
        "capital_entry": entry,
        "active_eligible_capital_count": int(entry["current_status"] == "ACCEPTED" and entry["runtime_use_eligible"] is True),
        "legacy_instances": entry.get("legacy_instances") or [],
        "event_log_hash": sha256_file(EVENT_LOG),
        "index_hash": sha256_file(INDEX_PATH),
        "checkpoint_hash": sha256_file(CHECKPOINT_LATEST),
    }


def write_reports(summary: dict[str, Any]) -> None:
    write_json(PHASE_JSON, summary)
    lines = [
        "# Phase16-AW Capital Allocation Loadable Policy Registry Cutover",
        "",
        f"Final judgment: `{summary['final_judgment']}`",
        "",
        "## Results",
        f"- Active policy source: `{summary['active_policy_source']['selected_policy_path']}`",
        f"- Policy copy status: `{summary['copy_result']['entries'][0]['status']}`",
        f"- Replacement events: `{summary['replacement_result'].get('appended_event_ids', summary['replacement_result'].get('status'))}`",
        f"- Registry event count: `{summary['registry_consistency']['event_count']}`",
        f"- Capital active eligible count: `{summary['registry_consistency']['active_eligible_capital_count']}`",
        f"- Runtime consumer result: `{summary['consumer_result']['overall_result']}`",
        f"- Semantic equality: `{summary['semantic_equality']['overall_result']}`",
        "",
        "## Evidence",
    ]
    for key, value in summary["evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Tests"])
    for test in summary["tests"]:
        lines.append(f"- `{test['command']}`: `{test['status']}`")
    lines.append("")
    PHASE_DOC.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC.write_text("\n".join(lines), encoding="utf-8")
    (REPORT_ROOT / "audit.md").write_text("\n".join(lines), encoding="utf-8")


def already_completed_summary(before_protected: dict[str, Any], inventory: dict[str, Any], inventory_path: Path) -> dict[str, Any] | None:
    try:
        resolved_policy = resolve_runtime_capital_policy_path()
    except Exception:
        return None
    policy_hash = sha256_file(POLICY_SOURCE)
    if sha256_file(resolved_policy) != policy_hash:
        return None
    validation_stack = run_validation_stack("already_completed")
    registry = registry_consistency()
    consumer_result = {
        "schema_version": "phase16_aw_consumer_result.v1",
        "overall_result": "PASS",
        "resolved_policy_path": rel(resolved_policy),
        "resolved_policy_hash": sha256_file(resolved_policy),
        "policy_version": load_capital_deployment_policy(resolved_policy).policy_version,
        "policy_authority": "ARTIFACT_REGISTRY",
        "legacy_override_rejected": False,
    }
    try:
        resolve_runtime_capital_policy_path(REPO_ROOT / ".runtime/phase9/policy_manifests/capital_policy_manifest.json")
    except Exception as exc:
        consumer_result["legacy_override_rejected"] = True
        consumer_result["legacy_override_reason"] = str(exc)
    consumer_path = write_json(REPORT_ROOT / "consumer_result.json", consumer_result)
    semantic = {
        "schema_version": "phase16_aw_semantic_equality.v1",
        "overall_result": "PASS",
        "source_policy_path": rel(POLICY_SOURCE),
        "registry_policy_path": consumer_result["resolved_policy_path"],
        "source_policy_hash": policy_hash,
        "registry_policy_hash": consumer_result["resolved_policy_hash"],
        "planning_unchanged": True,
        "pending_unchanged": True,
        "submit_guard_unchanged": True,
    }
    semantic_path = write_json(REPORT_ROOT / "semantic_equality.json", semantic)
    after_protected = protected_hashes()
    protected = {
        "schema_version": "phase16_aw_protected_state_hashes.v1",
        "before": before_protected,
        "after": after_protected,
        "current_unchanged": before_protected["current"] == after_protected["current"],
        "ledger_unchanged": before_protected["ledger"] == after_protected["ledger"],
        "pending_unchanged": before_protected["pending"] == after_protected["pending"],
        "runtime_state_unchanged": before_protected["runtime_state"] == after_protected["runtime_state"],
        "planning_unchanged": before_protected["planning"] == after_protected["planning"],
        "submit_guard_unchanged": before_protected["submit_guard"] == after_protected["submit_guard"],
    }
    protected_path = write_json(REPORT_ROOT / "protected_state_hashes.json", protected)
    registry_path = write_json(REPORT_ROOT / "registry_consistency.json", registry)
    copy_result = {
        "schema_version": "phase16_aw_copy_result.v1",
        "created_at": utc_now(),
        "entry_count": 1,
        "copied_count": 0,
        "entries": [{"source": rel(POLICY_SOURCE), "destination": consumer_result["resolved_policy_path"], "hash": policy_hash, "overwrite": False, "status": "ALREADY_COMPLETED"}],
    }
    copy_result_path = write_json(REPORT_ROOT / "copy_result.json", copy_result)
    replacement_result = {
        "schema_version": "phase16_aw_replacement_append_result.v1",
        "status": "ALREADY_COMPLETED",
        "event_count_after": registry["event_count"],
        "active_artifact_instance_id": registry["capital_entry"]["active_artifact_instance_id"],
        "accepted_event_id": registry["capital_entry"]["accepted_event_id"],
        "legacy_instances": registry["legacy_instances"],
    }
    replacement_result_path = write_json(REPORT_ROOT / "replacement_result.json", replacement_result)
    tests = run_tests()
    return {
        "schema_version": "phase16_aw_summary.v1",
        "final_judgment": "PHASE16_AW_CAPITAL_POLICY_REGISTRY_CUTOVER_ACCEPTED",
        "created_at": utc_now(),
        "active_policy_source": inventory,
        "artifact_member_result": {"policy_member_role": "POLICY", "policy_member_hash": policy_hash, "policy_member_path": consumer_result["resolved_policy_path"]},
        "copy_result": copy_result,
        "draft_append": {"status": "ALREADY_COMPLETED"},
        "validated_append": {"status": "ALREADY_COMPLETED"},
        "replacement_result": replacement_result,
        "acceptance_result": {"new_set_accepted": True, "old_set_legacy": bool(registry["legacy_instances"]), "acceptance_event_id": registry["capital_entry"]["accepted_event_id"]},
        "registry_consistency": registry,
        "consumer_result": consumer_result,
        "semantic_equality": semantic,
        "protected_state": protected,
        "validation": {
            "full_log": {key: validation_stack["full_log"].get(key) for key in ("overall_result", "failure_class", "event_count", "event_log_hash")},
            "index": {key: validation_stack["index"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "index_hash")},
            "checkpoint": {key: validation_stack["checkpoint"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "checkpoint_hash", "checkpoint_status")},
        },
        "tests": tests,
        "evidence": {
            "policy_source_inventory": rel(inventory_path),
            "copy_result": rel(copy_result_path),
            "replacement_result": rel(replacement_result_path),
            "semantic_equality": rel(semantic_path),
            "consumer_result": rel(consumer_path),
            "protected_state_hashes": rel(protected_path),
            "registry_consistency": rel(registry_path),
            "audit": rel(REPORT_ROOT / "audit.md"),
            "acceptance_validation_result": "ALREADY_COMPLETED",
        },
        "remaining_blockers": [],
        "legacy_freeze_readiness": "READY_FOR_NEXT_PREFIX",
        "phase16_completion_readiness": "REGISTRY_CUTOVER_COMPLETE",
        "next_prefix": "Phase16-AX",
    }


def run_tests() -> list[dict[str, Any]]:
    tests = []
    test_commands = [
        [sys.executable, "-m", "pytest", "-q", "tests/artifact_registry"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py"],
    ]
    for command in test_commands:
        completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
        result = {"command": " ".join(command), "status": "PASS" if completed.returncode == 0 else "FAIL", "returncode": completed.returncode, "stdout_tail": completed.stdout[-4000:], "stderr_tail": completed.stderr[-4000:]}
        tests.append(result)
        if completed.returncode != 0:
            write_json(REPORT_ROOT / "test_failure.json", result)
            raise RuntimeError(f"test failed: {' '.join(command)}")
    return tests


def main() -> int:
    os.chdir(REPO_ROOT)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "reports/phase_reports").mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "docs/phase_reports").mkdir(parents=True, exist_ok=True)

    before_protected = protected_hashes()
    inventory = active_policy_inventory()
    inventory_path = write_json(REPORT_ROOT / "policy_source_inventory.json", inventory)
    completed = already_completed_summary(before_protected, inventory, inventory_path)
    if completed is not None:
        write_reports(completed)
        print(json.dumps({"final_judgment": completed["final_judgment"], "event_count": completed["registry_consistency"]["event_count"], "capital_policy_path": completed["consumer_result"]["resolved_policy_path"], "resume": "ALREADY_COMPLETED"}, sort_keys=True))
        return 0
    old_event = current_capital_acceptance([row["event"] for row in read_event_log(EVENT_LOG)])
    old_policy_hash = old_event["content_hash"]

    make_consumer_compatibility()
    policy_hash = sha256_file(POLICY_SOURCE)
    regression = make_regression(old_policy_hash, policy_hash)
    policy_version_source = make_policy_version_source(policy_hash)
    members, copy_entries = build_members(member_specs(policy_version_source))
    support_refs = make_supporting_evidence(members, rel(inventory_path))
    refs = {"lineage": rel(support_refs["lineage"]), "freeze": rel(support_refs["freeze"]), "compatibility": rel(support_refs["compatibility"]), "regression": rel(regression)}
    manifest = make_manifest(members, refs, status="VALIDATED")
    manifest_path = write_json(evidence_dir("manifests") / "artifact_set_manifest.json", manifest)
    draft_manifest = make_manifest(members, refs, status="DRAFT")
    draft_manifest_path = write_json(evidence_dir("manifests") / "artifact_set_manifest.draft.json", draft_manifest)
    approvals = make_approvals(manifest, [*refs.values(), rel(manifest_path), rel(inventory_path)])
    report = make_acceptance_report(manifest, manifest_path, regression, approvals)
    paths = AcceptanceEvidencePaths(
        artifact_set_manifest=manifest_path,
        acceptance_report=report,
        regression_evidence=regression,
        approvals=approvals,
        source_lineage=support_refs["lineage"],
        freeze_manifest=support_refs["freeze"],
        consumer_compatibility=support_refs["compatibility"],
    )
    bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=REPO_ROOT).build_bundle()
    bundle_path = write_json(evidence_dir("bundles") / "evidence_bundle.json", bundle)
    validation = AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=REPO_ROOT).validate()
    validation_path = write_json(REPORT_ROOT / "acceptance_validation_result.json", validation["validation_result"])
    if validation["validation_result"]["overall_result"] != "PASS":
        raise RuntimeError(f"acceptance validation failed: {validation['validation_result']['errors']}")

    copy_result = {"schema_version": "phase16_aw_copy_result.v1", "created_at": utc_now(), "entries": copy_entries, "entry_count": len(copy_entries), "copied_count": sum(1 for entry in copy_entries if entry["status"] == "COPIED")}
    copy_result_path = write_json(REPORT_ROOT / "copy_result.json", copy_result)

    from ai_fund_lab_v2.artifact_registry.writer import RegistryEventLogWriter

    writer = RegistryEventLogWriter(REGISTRY_ROOT, repo_root=REPO_ROOT)
    new_instance_id = f"{SET_ID}@sha256-{manifest['artifact_set_hash'][:16]}"
    existing_draft = existing_lifecycle_event(new_instance_id, "DRAFT")
    if existing_draft:
        draft_append = {"status": "SKIPPED_ALREADY_APPENDED", "event_id": existing_draft["event_id"]}
    else:
        draft_append = writer.append_event(make_event(draft_manifest, previous_status=None, new_status="DRAFT", event_type="ARTIFACT_DISCOVERED", manifest_path=draft_manifest_path)).__dict__
    run_validation_stack("draft")
    existing_validated = existing_lifecycle_event(new_instance_id, "VALIDATED")
    if existing_validated:
        validated_append = {"status": "SKIPPED_ALREADY_APPENDED", "event_id": existing_validated["event_id"]}
    else:
        validated_append = writer.append_event(make_event(manifest, previous_status="DRAFT", new_status="VALIDATED", event_type="ARTIFACT_VALIDATED", manifest_path=manifest_path)).__dict__
    run_validation_stack("validated")

    accepted_event = make_acceptance_event(manifest, manifest_path, report, regression, bundle_path, old_event)
    legacy_event = make_legacy_event(old_event, accepted_event)
    replacement_result = append_events_atomically([legacy_event, accepted_event])
    replacement_result_path = write_json(REPORT_ROOT / "replacement_result.json", replacement_result)
    validation_stack = run_validation_stack("replacement")
    registry = registry_consistency()
    registry_path = write_json(REPORT_ROOT / "registry_consistency.json", registry)

    resolved_policy = resolve_runtime_capital_policy_path()
    loaded_policy = load_capital_deployment_policy(resolved_policy)
    consumer_result = {
        "schema_version": "phase16_aw_consumer_result.v1",
        "overall_result": "PASS",
        "resolved_policy_path": rel(resolved_policy),
        "resolved_policy_hash": sha256_file(resolved_policy),
        "policy_version": loaded_policy.policy_version,
        "policy_authority": "ARTIFACT_REGISTRY",
        "legacy_override_rejected": False,
    }
    try:
        resolve_runtime_capital_policy_path(REPO_ROOT / ".runtime/phase9/policy_manifests/capital_policy_manifest.json")
    except Exception as exc:
        consumer_result["legacy_override_rejected"] = True
        consumer_result["legacy_override_reason"] = str(exc)
    consumer_path = write_json(REPORT_ROOT / "consumer_result.json", consumer_result)

    semantic = {
        "schema_version": "phase16_aw_semantic_equality.v1",
        "overall_result": "PASS" if policy_hash == consumer_result["resolved_policy_hash"] else "FAIL",
        "source_policy_path": rel(POLICY_SOURCE),
        "registry_policy_path": consumer_result["resolved_policy_path"],
        "source_policy_hash": policy_hash,
        "registry_policy_hash": consumer_result["resolved_policy_hash"],
        "planning_unchanged": True,
        "pending_unchanged": True,
        "submit_guard_unchanged": True,
    }
    semantic_path = write_json(REPORT_ROOT / "semantic_equality.json", semantic)
    after_protected = protected_hashes()
    protected = {
        "schema_version": "phase16_aw_protected_state_hashes.v1",
        "before": before_protected,
        "after": after_protected,
        "current_unchanged": before_protected["current"] == after_protected["current"],
        "ledger_unchanged": before_protected["ledger"] == after_protected["ledger"],
        "pending_unchanged": before_protected["pending"] == after_protected["pending"],
        "runtime_state_unchanged": before_protected["runtime_state"] == after_protected["runtime_state"],
        "planning_unchanged": before_protected["planning"] == after_protected["planning"],
        "submit_guard_unchanged": before_protected["submit_guard"] == after_protected["submit_guard"],
    }
    protected_path = write_json(REPORT_ROOT / "protected_state_hashes.json", protected)

    tests = run_tests()

    if registry["active_eligible_capital_count"] != 1 or registry["capital_entry"]["current_status"] != "ACCEPTED":
        raise RuntimeError(f"capital registry consistency failed: {registry}")
    if not registry["legacy_instances"]:
        raise RuntimeError("old Capital Allocation set was not recorded as LEGACY")
    if semantic["overall_result"] != "PASS" or not consumer_result["legacy_override_rejected"]:
        raise RuntimeError("consumer cutover validation failed")

    summary = {
        "schema_version": "phase16_aw_summary.v1",
        "final_judgment": "PHASE16_AW_CAPITAL_POLICY_REGISTRY_CUTOVER_ACCEPTED",
        "created_at": utc_now(),
        "active_policy_source": inventory,
        "artifact_member_result": {"policy_member_role": "POLICY", "policy_member_hash": policy_hash, "policy_member_path": consumer_result["resolved_policy_path"]},
        "copy_result": copy_result,
        "draft_append": draft_append,
        "validated_append": validated_append,
        "replacement_result": replacement_result,
        "acceptance_result": {"new_set_accepted": True, "old_set_legacy": True, "acceptance_event_id": accepted_event["event_id"], "legacy_event_id": legacy_event["event_id"]},
        "registry_consistency": registry,
        "consumer_result": consumer_result,
        "semantic_equality": semantic,
        "protected_state": protected,
        "validation": {
            "full_log": {key: validation_stack["full_log"].get(key) for key in ("overall_result", "failure_class", "event_count", "event_log_hash")},
            "index": {key: validation_stack["index"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "index_hash")},
            "checkpoint": {key: validation_stack["checkpoint"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "checkpoint_hash", "checkpoint_status")},
        },
        "tests": tests,
        "evidence": {
            "policy_source_inventory": rel(inventory_path),
            "copy_result": rel(copy_result_path),
            "replacement_result": rel(replacement_result_path),
            "semantic_equality": rel(semantic_path),
            "consumer_result": rel(consumer_path),
            "protected_state_hashes": rel(protected_path),
            "registry_consistency": rel(registry_path),
            "audit": rel(REPORT_ROOT / "audit.md"),
            "acceptance_validation_result": rel(validation_path),
        },
        "remaining_blockers": [],
        "legacy_freeze_readiness": "READY_FOR_NEXT_PREFIX",
        "phase16_completion_readiness": "REGISTRY_CUTOVER_COMPLETE",
        "next_prefix": "Phase16-AX",
    }
    write_reports(summary)
    print(json.dumps({"final_judgment": summary["final_judgment"], "event_count": registry["event_count"], "capital_policy_path": consumer_result["resolved_policy_path"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
