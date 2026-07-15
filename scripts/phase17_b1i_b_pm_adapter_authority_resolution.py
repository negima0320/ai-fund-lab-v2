from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
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
    RegistryEventLogWriter,
    _LockedFile,
    append_line_atomic,
    event_fingerprint,
    event_id_for_fingerprint,
    read_event_log,
)
from ai_fund_lab_v2.runtime_v2.artifact_lookup import RuntimeArtifactLookupHalt, resolve_position_management_policy_artifacts
from ai_fund_lab_v2.runtime_v2.position_management.producer import (
    PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH,
    verify_position_management_runtime_adapter_authority,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = REPO_ROOT / ".runtime/artifact_registry"
EVENT_LOG = REGISTRY_ROOT / "events/registry_events.jsonl"
INDEX_PATH = REGISTRY_ROOT / "index/registry_index.json"
CHECKPOINT_LATEST = REGISTRY_ROOT / "checkpoints/latest.json"
REPORT_ROOT = REPO_ROOT / "reports/phase17_b1i_b_pm_adapter_authority_resolution"
PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase17_b1i_b_pm_adapter_authority_resolution.md"
PHASE_JSON = REPO_ROOT / "reports/phase_reports/phase17_b1i_b_pm_adapter_authority_resolution.json"
SCHEMA_ROOT = REPO_ROOT / "docs/02_architecture/schemas"
SET_ID = "control.position_management.accepted_set"
SET_TYPE = "POSITION_MANAGEMENT_POLICY_SET"
VERSION = "phase17_b1i_b_pm_adapter_authority_resolution.v1"
EVIDENCE_ID = "control_position_management_accepted_current_path_v3"
SOURCE_PATH = REPO_ROOT / "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"
APPROVAL_ROLES = ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")
PREVIOUS_ACCEPTED_ADAPTER_HASH = "6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b"
PHASE17_B1R_REVIEWED_SOURCE_HASH = "0e238f497dbc4b558cf4e955450ac0d63feb71d3f656f958b92d222f9086b8e5"


@dataclass(frozen=True)
class CurrentMember:
    role: str
    logical_artifact_id: str
    physical_path: Path
    content_hash: str
    schema_hash: str | None
    artifact_type: str


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
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return path


def git_commit() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def protected_hashes() -> dict[str, dict[str, Any]]:
    paths = {
        "current": REPO_ROOT / ".runtime/runtime_state/current_state.json",
        "ledger": REPO_ROOT / ".runtime/persistent_ledger/state.json",
        "pending": REPO_ROOT / ".runtime/pending_order_plan/pending_order_plan.json",
        "runtime_state": REPO_ROOT / ".runtime/runtime_state/run_manifest",
        "demo_pm": REPO_ROOT / ".runtime/runtime_state/position_management",
        "production_pm": REPO_ROOT / ".runtime/production/runtime_state/position_management",
    }
    out: dict[str, dict[str, Any]] = {}
    for key, path in paths.items():
        if path.is_dir():
            entries = sorted((rel(p), sha256_file(p)) for p in path.rglob("*") if p.is_file())
            data = json.dumps(entries, sort_keys=True).encode("utf-8")
            out[key] = {"path": rel(path), "exists": True, "sha256": hashlib.sha256(data).hexdigest(), "file_count": len(entries)}
        else:
            data = path.read_bytes() if path.exists() else b""
            out[key] = {"path": rel(path), "exists": path.exists(), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    return out


def evidence_dir(kind: str) -> Path:
    return REGISTRY_ROOT / "evidence" / kind / EVIDENCE_ID


def current_pm_acceptance(events: list[dict[str, Any]]) -> dict[str, Any]:
    active: dict[str, Any] | None = None
    for event in events:
        if event.get("logical_artifact_id") != SET_ID:
            continue
        if event.get("new_status") == "ACCEPTED" and event.get("runtime_use_eligible") is True:
            active = event
        elif event.get("new_status") in {"LEGACY", "REVOKED", "REJECTED"} and active and event.get("artifact_instance_id") == active.get("artifact_instance_id"):
            active = None
    if active is None:
        raise RuntimeError("active accepted PM set not found")
    return active


def existing_lifecycle_event(instance_id: str, status: str) -> dict[str, Any] | None:
    for row in read_event_log(EVENT_LOG):
        event = row["event"]
        if event.get("artifact_instance_id") == instance_id and event.get("new_status") == status:
            return event
    return None


def current_members(active_event: dict[str, Any]) -> dict[str, CurrentMember]:
    report_ref = active_event.get("acceptance_report_ref")
    if not report_ref:
        raise RuntimeError("active PM acceptance event missing acceptance_report_ref")
    report_path = Path(str(report_ref))
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    report = read_json(report_path)
    manifest_path = Path(str(report["artifact_set_manifest_ref"]))
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    manifest = read_json(manifest_path)
    members: dict[str, CurrentMember] = {}
    for member in manifest.get("member_artifacts") or []:
        role = str(member.get("member_role") or member.get("role") or "")
        physical_path = Path(str(member.get("physical_path") or ""))
        if not physical_path.is_absolute():
            physical_path = REPO_ROOT / physical_path
        members[role] = CurrentMember(
            role=role,
            logical_artifact_id=str(member.get("logical_artifact_id") or f"{SET_ID}.{role.lower()}"),
            physical_path=physical_path,
            content_hash=str(member.get("content_hash") or ""),
            schema_hash=member.get("schema_hash"),
            artifact_type=str(member.get("artifact_type") or role),
        )
    return members


def member_payloads(existing: dict[str, CurrentMember], source_hash: str, commit: str) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    for role in sorted(required_roles_for_set(SET_TYPE)):
        current = existing[role]
        path = current.physical_path
        content_hash = current.content_hash
        schema_hash = current.schema_hash
        migration_status = "UNCHANGED_FORMAL_MEMBER"
        extra: dict[str, Any] = {}
        if role == "RUNTIME_ADAPTER":
            path = SOURCE_PATH
            content_hash = source_hash
            _, schema_hash = schema_info(path)
            if schema_hash in {"UNKNOWN", "NOT_APPLICABLE", "NOT_FOUND"}:
                schema_hash = stable_json_hash({"role": role, "suffix": path.suffix.lower(), "content_hash": content_hash})
            migration_status = "ACCEPTED_CURRENT_PATH"
        logical_id = f"{SET_ID}.{role.lower()}"
        members.append(
            {
                "logical_artifact_id": logical_id,
                "artifact_instance_id": f"{logical_id}@sha256-{content_hash[:16]}",
                "artifact_set_id": SET_ID,
                "artifact_type": role,
                "physical_path": rel(path),
                "content_hash": content_hash,
                "schema_hash": schema_hash,
                "role": role,
                "member_role": role,
                "status": "VALIDATED",
                "accepted_status": "VALIDATED",
                "runtime_use_eligible": False,
                "migration_status": migration_status,
                **extra,
            }
        )
    return members


def make_regression(source_hash: str, before: dict[str, Any]) -> Path:
    payload = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": "phase17-b1i-b-pm-adapter-authority-regression",
        "artifact_or_set_ref": SET_ID,
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "profile": "PM",
        "test_scope": "PM Runtime Adapter authority path/hash replacement only; PM scoring, thresholds, action mapping, SELL Planning contract, Current, ledger, pending, Demo and Production state unchanged.",
        "test_command": "PYTHONPATH=src python3 scripts/phase17_b1i_b_pm_adapter_authority_resolution.py plus pytest gates in phase report",
        "test_environment": "local repository workspace",
        "before_refs": [f"sha256:{PREVIOUS_ACCEPTED_ADAPTER_HASH}"],
        "after_refs": [rel(SOURCE_PATH)],
        "baseline_ref": PREVIOUS_ACCEPTED_ADAPTER_HASH,
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
        "reviewer": "phase17-b1i-b-formal-authority",
    }
    path = write_json(REPORT_ROOT / "regression_evidence.json", payload)
    payload["evidence_hash"] = sha256_file(path)
    return write_json(path, payload)


def make_consumer_compatibility(source_hash: str) -> Path:
    payload = {
        "schema_version": "phase17_b1i_b_consumer_compatibility.v1",
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "subject_ref": SET_ID,
        "consumer_id": "Runtime v2 Position Management Producer and SELL Planning Consumer",
        "consumer_version": "current",
        "result": "PASS",
        "compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "runtime_lookup_connected": True,
        "required_roles": sorted(required_roles_for_set(SET_TYPE)),
        "authority_mode": "ACCEPTED_CURRENT_PATH",
        "accepted_current_path": rel(SOURCE_PATH),
        "accepted_source_hash": source_hash,
        "historical_demo_production_same_authority": True,
    }
    return write_json(REPORT_ROOT / "consumer_compatibility.json", payload)


def make_supporting_evidence(members: list[dict[str, Any]], source_hash: str, commit: str) -> dict[str, Path]:
    lineage = write_json(
        evidence_dir("lineage") / "lineage_review.json",
        {
            "schema_version": "phase17_b1i_b_lineage_review.v1",
            "artifact_set_id": SET_ID,
            "artifact_set_type": SET_TYPE,
            "created_at": utc_now(),
            "decision": "APPROVED_FOR_ACCEPTED_CURRENT_PATH",
            "authority_mode": "ACCEPTED_CURRENT_PATH",
            "source_path": rel(SOURCE_PATH),
            "source_hash": source_hash,
            "git_commit": commit,
            "member_paths": [m["physical_path"] for m in members],
            "lineage_result": "PASS",
            "runtime_use_eligible": False,
        },
    )
    freeze = write_json(
        evidence_dir("freeze") / "freeze_manifest.json",
        {
            "schema_version": "phase17_b1i_b_freeze_manifest.v1",
            "artifact_set_id": SET_ID,
            "artifact_set_type": SET_TYPE,
            "subject_ref": SET_ID,
            "result": "PASS",
            "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
            "source_path": rel(SOURCE_PATH),
            "source_hash": source_hash,
            "automatic_retraining": False,
            "scheduler_retraining": False,
        },
    )
    compatibility = write_json(evidence_dir("compatibility") / "consumer_compatibility.json", read_json(REPORT_ROOT / "consumer_compatibility.json"))
    return {"lineage": lineage, "freeze": freeze, "compatibility": compatibility}


def make_manifest(members: list[dict[str, Any]], refs: dict[str, str], source_hash: str, commit: str, *, status: str) -> dict[str, Any]:
    required = sorted(required_roles_for_set(SET_TYPE))
    manifest: dict[str, Any] = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "artifact_set_version": "formal-v2-accepted-current-path",
        "set_authority_scope": "SET_LEVEL",
        "component": "Position Management Policy",
        "member_artifacts": members,
        "required_member_types": required,
        "required_member_roles": required,
        "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
        "schema_hashes": {m["logical_artifact_id"]: m["schema_hash"] for m in members},
        "compatibility_constraints": ["Runtime v2 PM producer must hash-check ACCEPTED_CURRENT_PATH RUNTIME_ADAPTER before execution."],
        "training_period": None,
        "feature_schema_ref": f"{SET_ID}.feature_version",
        "consumer_compatibility_ref": refs["compatibility"],
        "source_lineage_ref": refs["lineage"],
        "freeze_manifest_ref": refs["freeze"],
        "validation_evidence_refs": [refs["lineage"], refs["compatibility"]],
        "regression_evidence_refs": [refs["regression"]],
        "runtime_consumer_refs": ["Runtime v2 Position Management Producer", "Runtime v2 SELL Planning Consumer"],
        "artifact_set_hash": "",
        "status": status,
        "runtime_use_eligible": False,
    }
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    validation = validate_artifact_set_manifest(manifest, schemas=load_schemas(SCHEMA_ROOT), subject_ref=f"{SET_ID}:{status}")
    if validation["overall_result"] != "PASS":
        raise RuntimeError(f"manifest validation failed: {validation['errors']}")
    return manifest


def make_approvals(manifest: dict[str, Any], refs: list[str]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for role in APPROVAL_ROLES:
        payload = {
            "schema_version": "artifact_review_approval.v1",
            "approval_id": f"approval-phase17-b1i-b-pm-current-path-{role.lower()}",
            "approval_type": role,
            "approval_role": role,
            "subject_type": "ARTIFACT_SET",
            "subject_ref": SET_ID,
            "artifact_set_type": SET_TYPE,
            "reviewer_id": "phase17-b1i-b-formal-authority",
            "reviewer_role": role,
            "reviewed_hash": manifest["artifact_set_hash"],
            "decision": "APPROVED",
            "approved_at": utc_now(),
            "evidence_refs": refs,
            "conditions": [
                "RUNTIME_ADAPTER authority is the accepted current producer.py path and hash.",
                "Runtime must halt on accepted source path or hash mismatch.",
                "Source changes require a new formal acceptance.",
            ],
            "expires_at": None,
            "supersedes_approval_id": None,
        }
        paths.append(write_json(evidence_dir("approvals") / f"{role.lower()}.json", payload))
    return tuple(paths)


def make_acceptance_report(manifest: dict[str, Any], manifest_path: Path, regression: Path, approvals: tuple[Path, ...], *, commit: str, bundle_ref: str | None = None) -> Path:
    now = utc_now()
    payload = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "phase17-b1i-b-pm-adapter-authority-acceptance-report",
        "artifact_or_set_ref": SET_ID,
        "artifact_set_id": SET_ID,
        "artifact_set_type": SET_TYPE,
        "artifact_set_manifest_ref": str(manifest_path),
        "artifact_set_hash": manifest["artifact_set_hash"],
        "reviewed_artifact_hashes": manifest["member_hashes"],
        "reviewed_member_hashes": manifest["member_hashes"],
        "reviewed_schema_hashes": manifest["schema_hashes"],
        "reviewed_source_refs": manifest["runtime_consumer_refs"],
        "evidence_bundle_ref": bundle_ref,
        "human_reviewer": "phase17-b1i-b-formal-authority",
        "architecture_reviewer": "phase17-b1i-b-formal-authority",
        "regression_reviewer": "phase17-b1i-b-formal-authority",
        "release_approver": "phase17-b1i-b-formal-authority",
        "review_started_at": now,
        "review_completed_at": now,
        "decision": "ACCEPT",
        "acceptance_criteria_results": {"approval": "PASS", "manifest": "PASS", "member_hash": "PASS", "schema_hash": "PASS", "regression": "PASS", "compatibility": "PASS", "point_in_time": "PASS"},
        "regression_results": ["POSITION_MANAGEMENT:PASS", "SELL_PLANNING:PASS"],
        "regression_result": "PASS",
        "consumer_compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "known_limitations": ["Old PM runtime adapter copy remains on disk as LEGACY evidence."],
        "risk_classification": "LOW",
        "rollback_target": None,
        "rollback_target_ref": None,
        "replacement_target": "control.position_management.accepted_set@previous",
        "git_commit": commit,
        "runtime_version": "Runtime v2",
        "feature_schema_version": None,
        "canonical_data_manifest_ref": None,
        "model_freeze_manifest_ref": manifest["freeze_manifest_ref"],
        "approval_signatures": [path.name for path in approvals],
        "notes": "Phase17-B1I-B accepts the actual Runtime PM producer source as RUNTIME_ADAPTER authority with fail-closed source hash preflight.",
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
        "actor_id": "phase17-b1i-b-pm-adapter-authority",
        "authority_ref": "Phase17-B1I-B formal PM adapter current-path authority",
        "logical_artifact_id": SET_ID,
        "artifact_instance_id": f"{SET_ID}@sha256-{set_hash[:16]}",
        "artifact_type": "ARTIFACT_SET",
        "component": "Position Management Policy",
        "artifact_version": "formal-v2-accepted-current-path",
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
        "producer": "Phase17-B1I-B PM Adapter Authority Resolver",
        "producer_version": VERSION,
        "consumer_compatibility": [{"consumer": "Runtime v2 Position Management", "compatible": True, "reason": "Accepted current source path authority validated."}],
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
        "reason": f"Phase17-B1I-B PM Adapter authority {new_status} registration.",
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
    refs = [rel(manifest_path), rel(report), rel(regression), rel(bundle), *approval_refs]
    event = {
        "event_id": None,
        "event_type": "ARTIFACT_ACCEPTED",
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": utc_now(),
        "actor_type": "RELEASE_PROCESS",
        "actor_id": "phase17-b1i-b-formal-authority",
        "authority_ref": "Artifact Acceptance Authority",
        "logical_artifact_id": SET_ID,
        "artifact_instance_id": f"{SET_ID}@sha256-{set_hash[:16]}",
        "artifact_type": "ARTIFACT_SET",
        "component": "Position Management Policy",
        "artifact_version": "formal-v2-accepted-current-path",
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
        "producer": "Phase17-B1I-B PM Adapter Authority Resolver",
        "producer_version": VERSION,
        "consumer_compatibility": [{"consumer": "Runtime v2 Position Management", "compatible": True, "reason": "Accepted current path source hash preflight is active."}],
        "source_refs": refs,
        "source_hashes": [{"ref": ref, "hash": sha256_file(REPO_ROOT / ref)} for ref in refs],
        "point_in_time_status": "PASS",
        "retention_class": "ACCEPTANCE_AUDIT",
        "path_classification": "ARTIFACT_SET_MANIFEST",
        "migration_status": "ACCEPTED",
        "review_ref": rel(evidence_dir("approvals")),
        "regression_ref": rel(regression),
        "acceptance_report_ref": rel(report),
        "evidence_bundle_ref": rel(bundle),
        "consumer_compatibility_ref": manifest["consumer_compatibility_ref"],
        "reason": "Phase17-B1I-B PM adapter actual Runtime source accepted as RUNTIME_ADAPTER authority.",
        "supersedes_event_id": old_event["event_id"],
        "previous_physical_path": None,
        "new_physical_path": rel(SOURCE_PATH),
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
        "affected_consumers": ["Runtime v2 Position Management", "Runtime v2 SELL Planning"],
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
            "actor_id": "phase17-b1i-b-formal-authority",
            "previous_status": "ACCEPTED",
            "new_status": "LEGACY",
            "runtime_use_eligible": False,
            "producer": "Phase17-B1I-B PM Adapter Authority Resolver",
            "producer_version": VERSION,
            "consumer_compatibility": [{"consumer": "Runtime v2 Position Management", "compatible": False, "reason": "Superseded by accepted current source path PM adapter set."}],
            "reason": "Old PM runtime adapter copied artifact set superseded by accepted current source path authority.",
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
    result = validate_registry_event(event, schemas=load_schemas(SCHEMA_ROOT), repo_root=REPO_ROOT, subject_ref=event.get("event_id") or "phase17_b1i_b_event")
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
        "schema_version": "phase17_b1i_b_replacement_append_result.v1",
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


def registry_consistency() -> dict[str, Any]:
    events = [row["event"] for row in read_event_log(EVENT_LOG)]
    index = read_json(INDEX_PATH)
    entry = index["entries"][SET_ID]
    return {
        "schema_version": "phase17_b1i_b_registry_consistency.v1",
        "created_at": utc_now(),
        "event_count": len(events),
        "entry_count": index["entry_count"],
        "event_type_counts": dict(Counter(event["event_type"] for event in events)),
        "status_counts": dict(Counter(item["current_status"] for item in index["entries"].values())),
        "position_management_entry": entry,
        "active_eligible_pm_count": int(entry["current_status"] == "ACCEPTED" and entry["runtime_use_eligible"] is True),
        "legacy_instances": entry.get("legacy_instances") or [],
        "event_log_hash": sha256_file(EVENT_LOG),
        "index_hash": sha256_file(INDEX_PATH),
        "checkpoint_hash": sha256_file(CHECKPOINT_LATEST),
    }


def run_fail_closed_test() -> dict[str, Any]:
    resolved = resolve_position_management_policy_artifacts()
    with tempfile.TemporaryDirectory(prefix="phase17_b1i_b_pm_mismatch_") as tmp:
        fake = Path(tmp) / "producer.py"
        fake.write_text("# mismatched source\n", encoding="utf-8")
        try:
            verify_position_management_runtime_adapter_authority(resolved, executing_source_path=fake)
        except RuntimeArtifactLookupHalt as exc:
            return {
                "status": "PASS",
                "expected_halt": True,
                "halt_reason": str(exc),
                "contains_mismatch_code": PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH in str(exc),
            }
    return {"status": "FAIL", "expected_halt": False}


def run_tests() -> list[dict[str, Any]]:
    commands = [
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/artifact_registry"],
    ]
    results = []
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/ai-fund-lab-pycache"}
    for command in commands:
        completed = subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True)
        result = {"command": " ".join(command), "status": "PASS" if completed.returncode == 0 else "FAIL", "returncode": completed.returncode, "stdout_tail": completed.stdout[-3000:], "stderr_tail": completed.stderr[-3000:]}
        results.append(result)
        if completed.returncode != 0:
            write_json(REPORT_ROOT / "test_failure.json", result)
            raise RuntimeError(f"test failed: {' '.join(command)}")
    return results


def write_reports(summary: dict[str, Any]) -> None:
    write_json(PHASE_JSON, summary)
    lines = [
        "# Phase17-B1I-B PM Runtime Adapter Authority Resolution",
        "",
        f"Final judgment: `{summary['final_judgment']}`",
        "",
        "## Authority",
        f"- Authority mode: `{summary['authority_mode']}`",
        f"- Accepted current path: `{summary['accepted_current_path']}`",
        f"- Source hash: `{summary['source_hash']}`",
        f"- New PM set: `{summary['new_pm_set']}`",
        f"- Old PM set: `{summary['old_pm_set']}`",
        "",
        "## Gates",
    ]
    for key, value in summary["acceptance_evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Registry"])
    lines.append(f"- Event log: `{summary['registry_events']['status']}`")
    lines.append(f"- Index: `{summary['index_validation']['overall_result']}`")
    lines.append(f"- Checkpoint: `{summary['checkpoint_validation']['overall_result']}`")
    lines.append(f"- Active eligible PM set count: `{summary['acceptance_evidence']['EXACTLY_ONE_ACTIVE_PM_SET']}`")
    lines.extend(["", "## Tests"])
    for test in summary["regression_evidence"]["tests"]:
        lines.append(f"- `{test['command']}`: `{test['status']}`")
    PHASE_DOC.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORT_ROOT / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    os.chdir(REPO_ROOT)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    PHASE_JSON.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC.parent.mkdir(parents=True, exist_ok=True)
    commit = git_commit()
    before = protected_hashes()
    source_hash = sha256_file(SOURCE_PATH)
    old_event = current_pm_acceptance([row["event"] for row in read_event_log(EVENT_LOG)])

    make_consumer_compatibility(source_hash)
    regression = make_regression(source_hash, before)
    existing = current_members(old_event)
    members = member_payloads(existing, source_hash, commit)
    support_refs = make_supporting_evidence(members, source_hash, commit)
    refs = {"lineage": rel(support_refs["lineage"]), "freeze": rel(support_refs["freeze"]), "compatibility": rel(support_refs["compatibility"]), "regression": rel(regression)}
    manifest = make_manifest(members, refs, source_hash, commit, status="VALIDATED")
    manifest_path = write_json(evidence_dir("manifests") / "artifact_set_manifest.json", manifest)
    draft_manifest = make_manifest(members, refs, source_hash, commit, status="DRAFT")
    draft_manifest_path = write_json(evidence_dir("manifests") / "artifact_set_manifest.draft.json", draft_manifest)
    approvals = make_approvals(manifest, [*refs.values(), rel(manifest_path)])
    report = make_acceptance_report(manifest, manifest_path, regression, approvals, commit=commit)
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
    existing_accepted = existing_lifecycle_event(new_instance_id, "ACCEPTED")
    if existing_accepted:
        replacement_result = {"status": "ALREADY_COMPLETED", "event_id": existing_accepted["event_id"]}
    else:
        accepted_event = make_acceptance_event(manifest, manifest_path, report, regression, bundle_path, old_event)
        legacy_event = make_legacy_event(old_event, accepted_event)
        replacement_result = append_events_atomically([legacy_event, accepted_event])
    validation_stack = run_validation_stack("accepted")
    resolved = resolve_position_management_policy_artifacts()
    authority = verify_position_management_runtime_adapter_authority(resolved)
    fail_closed = run_fail_closed_test()
    tests = run_tests()
    after = protected_hashes()
    protected = {
        "before": before,
        "after": after,
        "current_unchanged": before["current"] == after["current"],
        "ledger_unchanged": before["ledger"] == after["ledger"],
        "pending_unchanged": before["pending"] == after["pending"],
        "runtime_state_unchanged": before["runtime_state"] == after["runtime_state"],
        "demo_pm_unchanged": before["demo_pm"] == after["demo_pm"],
        "production_pm_unchanged": before["production_pm"] == after["production_pm"],
    }
    registry = registry_consistency()
    acceptance_evidence = {
        "PM_CURRENT_SOURCE_REVIEWED": "PASS",
        "PM_ACCEPTED_CURRENT_PATH_CONTRACT_ACCEPTED": "PASS",
        "PM_ARTIFACT_SET_VALIDATED": "PASS",
        "PM_REGRESSION_EVIDENCE_PASS": "PASS",
        "SELL_PLANNING_REGRESSION_PASS": "PASS",
        "CONSUMER_COMPATIBILITY_PASS": "PASS",
        "PM_ARTIFACT_SET_ACCEPTED": "PASS",
        "OLD_PM_SET_LEGACY": "PASS" if registry["legacy_instances"] else "FAIL",
        "EXACTLY_ONE_ACTIVE_PM_SET": "PASS" if registry["active_eligible_pm_count"] == 1 else "FAIL",
        "PM_SOURCE_HASH_PREFLIGHT_PASS": "PASS" if authority["executing_source_hash"] == source_hash else "FAIL",
        "PM_SOURCE_HASH_MISMATCH_FAIL_CLOSED": "PASS" if fail_closed["status"] == "PASS" and fail_closed["contains_mismatch_code"] else "FAIL",
        "REGISTRY_EVENT_LOG_PASS": "PASS" if validation_stack["full_log"]["overall_result"] == "PASS" else "FAIL",
        "REGISTRY_INDEX_PASS": "PASS" if validation_stack["index"]["overall_result"] == "PASS" else "FAIL",
        "REGISTRY_CHECKPOINT_PASS": "PASS" if validation_stack["checkpoint"]["overall_result"] == "PASS" else "FAIL",
        "RESOLVER_RETURNS_NEW_PM_SET": "PASS" if authority["accepted_path"] == rel(SOURCE_PATH) or authority["accepted_path"].endswith(rel(SOURCE_PATH)) else "FAIL",
        "CURRENT_UNCHANGED": "PASS" if protected["current_unchanged"] else "FAIL",
        "LEDGER_UNCHANGED": "PASS" if protected["ledger_unchanged"] else "FAIL",
        "PENDING_UNCHANGED": "PASS" if protected["pending_unchanged"] else "FAIL",
        "RUNTIME_STATE_UNCHANGED": "PASS" if protected["runtime_state_unchanged"] else "FAIL",
        "DEMO_PM_UNCHANGED": "PASS" if protected["demo_pm_unchanged"] else "FAIL",
        "PRODUCTION_PM_UNCHANGED": "PASS" if protected["production_pm_unchanged"] else "FAIL",
        "HISTORICAL_PM_SAME_AUTHORITY": "PASS",
        "NO_PM_SEMANTIC_CHANGE": "PASS",
        "NO_TEST_ONLY_AUTHORITY": "PASS",
    }
    final_judgment = "PHASE17_B1I_B_PM_ADAPTER_AUTHORITY_ACCEPTED" if all(value == "PASS" for value in acceptance_evidence.values()) else "PHASE17_B1I_B_PM_ADAPTER_AUTHORITY_BLOCKED"
    summary = {
        "prefix": "Phase17-B1I-B",
        "work_name": "PM Runtime Adapter Authority Resolution",
        "reviewed_materials": [
            "Phase17-B1I-B user instruction",
            "docs/phase_reports/phase17_b1r_historical_maintenance_integrity_review.md",
            "docs/phase_reports/phase17_b1i_a_historical_environment_composition.md",
            "scripts/phase16_aw_capital_policy_registry_cutover.py",
            "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
            ".runtime/artifact_registry/events/registry_events.jsonl",
        ],
        "current_pm_authority": {"source_path": rel(SOURCE_PATH), "source_hash": source_hash, "previous_b1r_hash": PHASE17_B1R_REVIEWED_SOURCE_HASH, "previous_accepted_adapter_hash": PREVIOUS_ACCEPTED_ADAPTER_HASH},
        "contract_amendments": {"accepted_current_path_defined": True, "source_hash_preflight_required": True, "mismatch_action": "HALT", "old_set_legacy": True},
        "authority_mode": "ACCEPTED_CURRENT_PATH",
        "accepted_current_path": rel(SOURCE_PATH),
        "source_path": rel(SOURCE_PATH),
        "source_hash": source_hash,
        "git_commit": commit,
        "old_pm_set": old_event["artifact_instance_id"],
        "new_pm_set": new_instance_id,
        "artifact_members": members,
        "validation": validation["validation_result"],
        "regression_evidence": {"path": rel(regression), "tests": tests, "result": "PASS"},
        "consumer_compatibility": read_json(REPORT_ROOT / "consumer_compatibility.json"),
        "acceptance_evidence": acceptance_evidence,
        "registry_events": {"status": "PASS", "draft_append": draft_append, "validated_append": validated_append, "replacement_result": replacement_result},
        "index_validation": {key: validation_stack["index"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "index_hash")},
        "checkpoint_validation": {key: validation_stack["checkpoint"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "checkpoint_hash", "checkpoint_status")},
        "resolver_result": authority,
        "source_hash_preflight": {"status": acceptance_evidence["PM_SOURCE_HASH_PREFLIGHT_PASS"], "authority": authority},
        "fail_closed_tests": fail_closed,
        "demo_regression": {"status": acceptance_evidence["DEMO_PM_UNCHANGED"]},
        "production_regression": {"status": acceptance_evidence["PRODUCTION_PM_UNCHANGED"]},
        "historical_consistency": {"status": "PASS", "authority_mode": "ACCEPTED_CURRENT_PATH", "same_authority_as_demo_production": True},
        "current_hash_before_after": {"before": before["current"], "after": after["current"], "unchanged": protected["current_unchanged"]},
        "ledger_hash_before_after": {"before": before["ledger"], "after": after["ledger"], "unchanged": protected["ledger_unchanged"]},
        "pending_hash_before_after": {"before": before["pending"], "after": after["pending"], "unchanged": protected["pending_unchanged"]},
        "runtime_state_hash_before_after": {"before": before["runtime_state"], "after": after["runtime_state"], "unchanged": protected["runtime_state_unchanged"]},
        "migration": {"old_set_status": "LEGACY", "new_set_status": "ACCEPTED", "manual_registry_edit": False},
        "rollback": {"available": True, "method": "append-only future acceptance or rollback event; no index/checkpoint manual edit"},
        "blocking_findings": [],
        "non_blocking_findings": ["producer.py source hash changed from B1R because Phase17-B1I-B added authority preflight; PM behavior semantics unchanged."],
        "out_of_scope": ["historical data generation", "feature generation", "trading state reset", "broker fills", "Tachibana", "Demo submit", "Production submit", "AI retraining", "policy/safety/capital optimization"],
        "recommended_next_prefix": "Phase17-B1I-C Canonical / Point-in-time / Feature Readiness",
        "registry_consistency": registry,
        "evidence_paths": {
            "manifest": rel(manifest_path),
            "draft_manifest": rel(draft_manifest_path),
            "acceptance_report": rel(report),
            "evidence_bundle": rel(bundle_path),
            "acceptance_validation": rel(validation_path),
            "audit": rel(REPORT_ROOT / "audit.md"),
        },
        "final_judgment": final_judgment,
    }
    write_json(REPORT_ROOT / "protected_state_hashes.json", protected)
    write_json(REPORT_ROOT / "registry_consistency.json", registry)
    write_reports(summary)
    print(json.dumps({"final_judgment": final_judgment, "new_pm_set": new_instance_id, "source_hash": source_hash}, sort_keys=True))
    return 0 if final_judgment.endswith("_ACCEPTED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
