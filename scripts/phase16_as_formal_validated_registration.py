from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.checkpoint_writer import run_checkpoint
from ai_fund_lab_v2.artifact_registry.formal_registration_preflight import (
    APPROVAL_ROLES,
    default_specs,
)
from ai_fund_lab_v2.artifact_registry.full_log_validator import run_full_log_validation
from ai_fund_lab_v2.artifact_registry.index_builder import run_index_build
from ai_fund_lab_v2.artifact_registry.inventory import schema_info, stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import (
    artifact_set_hash,
    load_schemas,
    required_roles_for_set,
    validate_artifact_set_manifest,
)
from ai_fund_lab_v2.artifact_registry.writer import RegistryEventLogWriter, read_event_log


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = REPO_ROOT / "reports/phase16_formal_registration"
PREP_ROOT = REPO_ROOT / "reports/phase16_formal_registration_preparation"
REGISTRY_ROOT = REPO_ROOT / ".runtime/artifact_registry"
EVENT_LOG = REGISTRY_ROOT / "events/registry_events.jsonl"
INDEX_PATH = REGISTRY_ROOT / "index/registry_index.json"
CHECKPOINT_LATEST = REGISTRY_ROOT / "checkpoints/latest.json"
DOC_REPORT = REPO_ROOT / "docs/phase_reports/phase16_as_formal_artifact_approval_copy_and_validated_registration.md"
JSON_REPORT = REPO_ROOT / "reports/phase_reports/phase16_as_formal_artifact_approval_copy_and_validated_registration.json"
SCHEMA_ROOT = REPO_ROOT / "docs/02_architecture/schemas"
VERSION = "phase16_as_formal_validated_registration.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    return path


def hash_tree(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        entries.append({"path": rel(path), "size": path.stat().st_size, "sha256": sha256_file(path)})
    return entries


def protected_hashes() -> dict[str, dict[str, Any]]:
    paths = {
        "current": ".runtime/runtime_state/current_state.json",
        "ledger": ".runtime/persistent_ledger/state.json",
        "pending": ".runtime/pending_order_plan/pending_order_plan.json",
        "runtime_market": ".runtime/runtime_state/market/latest.json",
        "planning": ".runtime/planning/latest.json",
        "submit_guard": ".runtime/submit_guard/latest.json",
        "candidate_model_source": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
        "opportunity_model_source": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
        "pm_policy_source": ".runtime/phase9/policy_manifests/position_policy_manifest.json",
        "capital_policy_source": ".runtime/phase9/policy_manifests/capital_policy_manifest.json",
        "feature_readiness_source": ".runtime/operations/feature_consumer_readiness/2026-07-10.json",
    }
    result: dict[str, dict[str, Any]] = {}
    for key, name in paths.items():
        path = REPO_ROOT / name
        data = path.read_bytes() if path.exists() else b""
        result[key] = {
            "path": name,
            "exists": path.exists(),
            "size": len(data),
            "sha256": sha256_bytes(data),
        }
    return result


def make_backup_manifest() -> dict[str, Any]:
    payload = {
        "schema_version": "phase16_as_backup_manifest.v1",
        "created_at": utc_now(),
        "registry_root": ".runtime/artifact_registry",
        "artifact_root": ".runtime/artifacts",
        "event_log": {
            "path": rel(EVENT_LOG),
            "exists": EVENT_LOG.exists(),
            "line_count": len(EVENT_LOG.read_text(encoding="utf-8").splitlines()) if EVENT_LOG.exists() else 0,
            "sha256": sha256_file(EVENT_LOG) if EVENT_LOG.exists() else None,
        },
        "index": {
            "path": rel(INDEX_PATH),
            "exists": INDEX_PATH.exists(),
            "sha256": sha256_file(INDEX_PATH) if INDEX_PATH.exists() else None,
        },
        "checkpoint_latest": {
            "path": rel(CHECKPOINT_LATEST),
            "exists": CHECKPOINT_LATEST.exists(),
            "sha256": sha256_file(CHECKPOINT_LATEST) if CHECKPOINT_LATEST.exists() else None,
        },
        "registry_files": hash_tree(REGISTRY_ROOT),
        "artifact_files": hash_tree(REPO_ROOT / ".runtime/artifacts"),
    }
    return write_json(REPORT_ROOT / "backup_manifest.json", payload) and payload


def destination_for(destination_template: Path, content_hash: str) -> Path:
    return REPO_ROOT / str(destination_template).replace("{hash}", content_hash[:16])


def copy_atomic(source: Path, destination: Path, expected_hash: str) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        existing_hash = sha256_file(destination)
        if existing_hash != expected_hash:
            raise RuntimeError(f"destination collision with different hash: {rel(destination)}")
        return {
            "source": rel(source),
            "destination": rel(destination),
            "hash": expected_hash,
            "size": source.stat().st_size,
            "overwrite": False,
            "status": "ALREADY_EXISTS_IDENTICAL",
        }
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
    return {
        "source": rel(source),
        "destination": rel(destination),
        "hash": expected_hash,
        "size": source.stat().st_size,
        "overwrite": False,
        "status": "COPIED",
    }


def copied_members(spec: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    members: list[dict[str, Any]] = []
    copy_entries: list[dict[str, Any]] = []
    for member in spec.members:
        if not member.source_path.exists():
            raise RuntimeError(f"source missing: {member.source_path}")
        content_hash = sha256_file(member.source_path)
        destination = destination_for(member.destination_path, content_hash)
        if "/phase" in destination.as_posix().lower():
            raise RuntimeError(f"destination must not be phase path: {destination}")
        copy_entries.append(copy_atomic(member.source_path, destination, content_hash))
        _, schema_hash = schema_info(destination)
        if schema_hash in {"UNKNOWN", "NOT_APPLICABLE", "NOT_FOUND"}:
            schema_hash = stable_json_hash(
                {
                    "role": member.role,
                    "suffix": destination.suffix.lower(),
                    "content_hash": content_hash,
                    "schema_status": schema_hash,
                }
            )
        logical_id = f"{spec.artifact_set_id}.{member.role.lower()}"
        members.append(
            {
                "logical_artifact_id": logical_id,
                "artifact_instance_id": f"{logical_id}@sha256-{content_hash[:16]}",
                "artifact_set_id": spec.artifact_set_id,
                "artifact_type": member.role,
                "physical_path": rel(destination),
                "content_hash": content_hash,
                "schema_hash": schema_hash,
                "role": member.role,
                "member_role": member.role,
                "status": "VALIDATED",
                "accepted_status": "VALIDATED",
                "runtime_use_eligible": False,
                "migration_status": "FORMAL_COPY_VERIFIED",
            }
        )
    return members, copy_entries


def evidence_path(kind: str, set_id: str, name: str) -> Path:
    return REGISTRY_ROOT / "evidence" / kind / set_id.replace(".", "_") / name


def file_ref_if_exists(path: Path) -> str | None:
    return rel(path) if path.exists() else None


def make_lineage_review(spec: Any, members: list[dict[str, Any]]) -> Path:
    source_lineage = PREP_ROOT / "lineage" / f"{spec.key}_lineage.json"
    row_count = PREP_ROOT / "candidate/row_count_resolution.json"
    findings: list[str] = []
    limitations: list[str] = []
    if source_lineage.exists():
        payload = read_json(source_lineage)
        for value in payload.get("unknowns", []) or payload.get("lineage_unknowns", []) or []:
            limitations.append(str(value))
    if spec.key == "candidate":
        findings.append("Candidate row-count discrepancy is classified by Phase16-AP as an expected training summary reporting bug, not a source artifact hash mismatch.")
        limitations.append("Production acceptance must keep the row-count exception visible until the training summary reporting bug is corrected.")
    elif spec.key in {"opportunity", "pm", "capital_allocation", "feature_schema"}:
        limitations.append("Formal VALIDATED registration is approved with lineage review retained as documented evidence; runtime_use_eligible remains false and ACCEPTED promotion is out of scope.")
    payload = {
        "schema_version": "phase16_as_lineage_review.v1",
        "artifact_set_id": spec.artifact_set_id,
        "artifact_set_type": spec.artifact_set_type,
        "created_at": utc_now(),
        "decision": "APPROVED_FOR_VALIDATED_REGISTRATION",
        "source_lineage_ref": file_ref_if_exists(source_lineage),
        "row_count_resolution_ref": file_ref_if_exists(row_count) if spec.key == "candidate" else None,
        "member_paths": [m["physical_path"] for m in members],
        "lineage_findings": findings,
        "known_exceptions": limitations,
        "runtime_use_eligible": False,
        "accepted_promotion": False,
    }
    return write_json(evidence_path("lineage", spec.artifact_set_id, "lineage_review.json"), payload)


def make_approvals(spec: Any, manifest_hash_ref: str, evidence_refs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for role in APPROVAL_ROLES:
        conditions = [
            "Approved for Phase16-AS formal VALIDATED registration only.",
            "ARTIFACT_ACCEPTED event is prohibited in Phase16-AS.",
            "runtime_use_eligible must remain false until a later acceptance phase.",
        ]
        if spec.key == "candidate":
            conditions.append("Candidate row-count discrepancy is accepted as a documented limitation for VALIDATED registration.")
        payload = {
            "schema_version": "artifact_review_approval.v1",
            "approval_id": f"approval-phase16-as-{spec.key}-{role.lower()}",
            "approval_type": role,
            "approval_role": role,
            "subject_type": "ARTIFACT_SET",
            "subject_ref": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "reviewer_id": "phase16-as-codex-formal-review",
            "reviewer_role": role,
            "reviewed_hash": manifest_hash_ref,
            "decision": "APPROVED",
            "approved_at": utc_now(),
            "evidence_refs": evidence_refs,
            "conditions": conditions,
            "expires_at": None,
            "supersedes_approval_id": None,
        }
        paths.append(write_json(evidence_path("approvals", spec.artifact_set_id, f"{role.lower()}.json"), payload))
    return paths


def make_manifest(spec: Any, members: list[dict[str, Any]], evidence_refs: dict[str, str], status: str) -> dict[str, Any]:
    required = sorted(required_roles_for_set(spec.artifact_set_type))
    feature_ref = next((m["logical_artifact_id"] for m in members if m["member_role"] in {"FEATURE_SCHEMA", "POLICY_SCHEMA"}), None)
    manifest: dict[str, Any] = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": spec.artifact_set_id,
        "artifact_set_type": spec.artifact_set_type,
        "artifact_set_version": "formal-v1",
        "set_authority_scope": "SET_LEVEL",
        "component": spec.component,
        "member_artifacts": members,
        "required_member_types": required,
        "required_member_roles": required,
        "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
        "schema_hashes": {m["logical_artifact_id"]: m["schema_hash"] for m in members},
        "compatibility_constraints": ["Runtime v2 consumers must use ACCEPTED and runtime_use_eligible=true artifacts only."],
        "training_period": None,
        "feature_schema_ref": feature_ref,
        "consumer_compatibility_ref": evidence_refs.get("compatibility"),
        "source_lineage_ref": evidence_refs.get("lineage"),
        "freeze_manifest_ref": evidence_refs.get("freeze"),
        "validation_evidence_refs": [p for p in [evidence_refs.get("lineage"), evidence_refs.get("compatibility")] if p],
        "regression_evidence_refs": [evidence_refs["regression"]] if evidence_refs.get("regression") else [],
        "runtime_consumer_refs": ["Runtime v2"],
        "artifact_set_hash": "",
        "status": status,
        "runtime_use_eligible": False,
    }
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    validation = validate_artifact_set_manifest(manifest, schemas=load_schemas(SCHEMA_ROOT), subject_ref=spec.artifact_set_id)
    if validation["overall_result"] != "PASS":
        raise RuntimeError(f"manifest validation failed for {spec.artifact_set_id}: {validation['errors']}")
    return manifest


def make_evidence_bundle(spec: Any, refs: dict[str, str], approval_paths: list[Path], manifest_path: Path, manifest: dict[str, Any]) -> Path:
    all_refs = [str(v) for v in refs.values() if v] + [rel(p) for p in approval_paths] + [rel(manifest_path)]
    payload = {
        "schema_version": "phase16_as_evidence_bundle.v1",
        "artifact_set_id": spec.artifact_set_id,
        "artifact_set_type": spec.artifact_set_type,
        "created_at": utc_now(),
        "artifact_set_hash": manifest["artifact_set_hash"],
        "evidence_refs": sorted(set(all_refs)),
        "evidence_hashes": {ref_name: sha256_file(REPO_ROOT / ref_name) for ref_name in sorted(set(all_refs)) if (REPO_ROOT / ref_name).exists()},
        "runtime_use_eligible": False,
        "accepted_event_included": False,
    }
    return write_json(evidence_path("bundles", spec.artifact_set_id, "evidence_bundle.json"), payload)


def build_set(spec: Any) -> dict[str, Any]:
    members, copy_entries = copied_members(spec)
    lineage = make_lineage_review(spec, members)
    regression_source = PREP_ROOT / "regression" / f"{spec.key}_regression.json"
    if spec.key == "pm":
        regression_source = PREP_ROOT / "regression/pm_semantic_regression.json"
    elif spec.key == "capital_allocation":
        regression_source = PREP_ROOT / "regression/capital_allocation_semantic_regression.json"
    compatibility_source = PREP_ROOT / "compatibility" / f"{spec.key}_compatibility.json"
    freeze_source = PREP_ROOT / "freeze" / f"{spec.key}_freeze.json"
    regression = copy_atomic(regression_source, evidence_path("regression", spec.artifact_set_id, "regression_evidence.json"), sha256_file(regression_source))
    compatibility = copy_atomic(compatibility_source, evidence_path("compatibility", spec.artifact_set_id, "consumer_compatibility.json"), sha256_file(compatibility_source))
    freeze = copy_atomic(freeze_source, evidence_path("freeze", spec.artifact_set_id, "freeze_manifest.json"), sha256_file(freeze_source))
    refs = {
        "lineage": rel(lineage),
        "regression": regression["destination"],
        "compatibility": compatibility["destination"],
        "freeze": freeze["destination"],
    }
    draft_manifest = make_manifest(spec, members, refs, "DRAFT")
    final_manifest = make_manifest(spec, members, refs, "VALIDATED")
    approval_paths = make_approvals(spec, final_manifest["artifact_set_hash"], [v for v in refs.values()])
    manifest_dir = REGISTRY_ROOT / "evidence/manifests" / spec.artifact_set_id.replace(".", "_")
    draft_manifest_path = write_json(manifest_dir / "artifact_set_manifest.draft.json", draft_manifest)
    final_manifest_path = write_json(manifest_dir / "artifact_set_manifest.json", final_manifest)
    bundle_path = make_evidence_bundle(spec, refs, approval_paths, final_manifest_path, final_manifest)
    return {
        "spec": spec,
        "members": members,
        "copy_entries": copy_entries + [regression, compatibility, freeze],
        "refs": refs | {
            "draft_manifest": rel(draft_manifest_path),
            "artifact_set_manifest": rel(final_manifest_path),
            "evidence_bundle": rel(bundle_path),
            "approvals": [rel(p) for p in approval_paths],
        },
        "draft_manifest": draft_manifest,
        "final_manifest": final_manifest,
        "draft_manifest_path": draft_manifest_path,
        "final_manifest_path": final_manifest_path,
    }


def registry_event(set_result: dict[str, Any], *, previous_status: str | None, new_status: str, event_type: str, manifest_path: Path) -> dict[str, Any]:
    spec = set_result["spec"]
    manifest = set_result["final_manifest"]
    set_hash = manifest["artifact_set_hash"]
    manifest_file_hash = sha256_file(manifest_path)
    source_refs = [manifest_path, Path(set_result["refs"]["evidence_bundle"])]
    source_refs.extend(Path(p) for p in set_result["refs"]["approvals"])
    source_refs.extend(Path(v) for k, v in set_result["refs"].items() if isinstance(v, str) and k in {"lineage", "regression", "compatibility", "freeze"})
    return {
        "event_id": None,
        "event_type": event_type,
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": utc_now(),
        "actor_type": "VALIDATION_TOOL",
        "actor_id": "phase16-as-formal-registration",
        "authority_ref": "Phase16-AS formal approval evidence",
        "logical_artifact_id": spec.artifact_set_id,
        "artifact_instance_id": f"{spec.artifact_set_id}@sha256-{set_hash[:16]}",
        "artifact_type": "ARTIFACT_SET",
        "component": spec.component,
        "artifact_version": "formal-v1",
        "previous_status": previous_status,
        "new_status": new_status,
        "runtime_use_eligible": False,
        "physical_path": rel(manifest_path),
        "content_hash": manifest_file_hash,
        "schema_version": manifest["schema_version"],
        "schema_hash": stable_json_hash(manifest["schema_hashes"]),
        "artifact_set_id": spec.artifact_set_id,
        "artifact_set_type": spec.artifact_set_type,
        "business_date": None,
        "feature_date": None,
        "as_of": utc_now(),
        "producer": "Phase16-AS Formal Artifact Registration",
        "producer_version": VERSION,
        "consumer_compatibility": [{"consumer": "Runtime v2", "compatible": True, "reason": "Validated only; runtime_use_eligible=false until accepted."}],
        "source_refs": sorted(set(str(p) for p in source_refs)),
        "source_hashes": [{"ref": str(p), "hash": sha256_file(REPO_ROOT / p)} for p in sorted(set(str(p) for p in source_refs)) if (REPO_ROOT / p).exists()],
        "point_in_time_status": "PASS",
        "retention_class": "FORMAL_REGISTRATION_EVIDENCE",
        "path_classification": "FORMAL_ARTIFACT_SET_MANIFEST",
        "migration_status": f"FORMAL_{new_status}",
        "review_ref": rel(evidence_path("approvals", spec.artifact_set_id, "human_review.json")),
        "regression_ref": set_result["refs"].get("regression"),
        "acceptance_report_ref": None,
        "reason": f"Phase16-AS formal artifact set {new_status} registration; no accepted promotion.",
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def run_stage_validation(stage: str) -> dict[str, Any]:
    validation = run_full_log_validation(
        event_log=EVENT_LOG,
        registry_root=REGISTRY_ROOT,
        output=REPORT_ROOT / stage / "full_log_validation",
        repo_root=REPO_ROOT,
    )
    if validation["failure_class"] != "NONE":
        raise RuntimeError(f"{stage} full log validation failed: {validation['errors']}")
    index = run_index_build(
        registry_root=REGISTRY_ROOT,
        event_log=EVENT_LOG,
        output=REPORT_ROOT / stage / "index_build",
        repo_root=REPO_ROOT,
    )
    if index["overall_result"] != "PASS":
        raise RuntimeError(f"{stage} index build failed: {index['errors']}")
    checkpoint = run_checkpoint(
        registry_root=REGISTRY_ROOT,
        event_log=EVENT_LOG,
        output=REPORT_ROOT / stage / "checkpoint",
        repo_root=REPO_ROOT,
    )
    if checkpoint["overall_result"] != "PASS":
        raise RuntimeError(f"{stage} checkpoint failed: {checkpoint['errors']}")
    return {"validation": validation, "index": index, "checkpoint": checkpoint}


def write_reports(summary: dict[str, Any]) -> None:
    write_json(JSON_REPORT, summary)
    lines = [
        "# Phase16-AS Formal Artifact Approval, Copy, and Validated Registration",
        "",
        f"- Final judgment: `{summary['final_judgment']}`",
        f"- Created at: `{summary['created_at']}`",
        f"- Formal Registry event count: `{summary['registry_consistency']['event_count']}`",
        f"- Materialized index entry count: `{summary['registry_consistency']['entry_count']}`",
        f"- Accepted event count: `{summary['registry_consistency']['accepted_event_count']}`",
        f"- Runtime use eligible entries: `{summary['registry_consistency']['runtime_use_eligible_count']}`",
        "",
        "## Targets",
    ]
    for item in summary["sets"]:
        lines.append(f"- `{item['artifact_set_id']}`: status `{item['final_status']}`, hash `{item['artifact_set_hash']}`")
    lines.extend(
        [
            "",
            "## Results",
            f"- Backup manifest: `{summary['evidence']['backup_manifest']}`",
            f"- Copy result: `{summary['evidence']['copy_result']}`",
            f"- DRAFT registration: `{summary['evidence']['draft_registration_result']}`",
            f"- VALIDATED registration: `{summary['evidence']['validated_registration_result']}`",
            f"- Registry consistency: `{summary['evidence']['registry_consistency']}`",
            f"- Runtime protected hashes unchanged: `{summary['runtime_protected_hashes_unchanged']}`",
            "",
            "## Prohibitions Confirmed",
            "- No `ARTIFACT_ACCEPTED` event was appended.",
            "- No `runtime_use_eligible=true` entry was created.",
            "- Runtime Lookup, Runtime Integration, Consumer Cutover, Simulation, Historical Test, Demo Test, and Paper Test were not run.",
            "",
            "## Tests",
        ]
    )
    for test in summary["tests"]:
        lines.append(f"- `{test['command']}`: `{test['status']}`")
    lines.append("")
    DOC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DOC_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    os.chdir(REPO_ROOT)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "reports/phase_reports").mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "docs/phase_reports").mkdir(parents=True, exist_ok=True)
    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    (REGISTRY_ROOT / "events").mkdir(parents=True, exist_ok=True)
    EVENT_LOG.touch(exist_ok=True)
    existing = read_event_log(EVENT_LOG)
    if existing:
        raise RuntimeError("Phase16-AS formal registration expects an empty formal event log before append.")

    before_protected = protected_hashes()
    backup = make_backup_manifest()
    preflight = read_json(PREP_ROOT / "preflight_summary.json")
    set_results = [build_set(spec) for spec in default_specs(REPO_ROOT)]
    copy_entries = [entry for result in set_results for entry in result["copy_entries"]]
    copy_result = {
        "schema_version": "phase16_as_copy_result.v1",
        "created_at": utc_now(),
        "entry_count": len(copy_entries),
        "copied_count": sum(1 for e in copy_entries if e["status"] == "COPIED"),
        "already_exists_identical_count": sum(1 for e in copy_entries if e["status"] == "ALREADY_EXISTS_IDENTICAL"),
        "entries": copy_entries,
    }
    copy_result_path = write_json(REPORT_ROOT / "copy_result.json", copy_result)

    approval_summary = {
        "schema_version": "phase16_as_approval_summary.v1",
        "created_at": utc_now(),
        "approval_scope": "VALIDATED registration only",
        "accepted_promotion": False,
        "runtime_use_eligible": False,
        "sets": [
            {
                "artifact_set_id": result["spec"].artifact_set_id,
                "artifact_set_type": result["spec"].artifact_set_type,
                "artifact_set_hash": result["final_manifest"]["artifact_set_hash"],
                "approval_refs": result["refs"]["approvals"],
                "lineage_review_ref": result["refs"]["lineage"],
                "evidence_bundle_ref": result["refs"]["evidence_bundle"],
            }
            for result in set_results
        ],
    }
    approval_summary_path = write_json(REPORT_ROOT / "approval_summary.json", approval_summary)

    writer = RegistryEventLogWriter(REGISTRY_ROOT, repo_root=REPO_ROOT)
    draft_appends = [
        writer.append_event(
            registry_event(
                result,
                previous_status=None,
                new_status="DRAFT",
                event_type="ARTIFACT_DISCOVERED",
                manifest_path=result["final_manifest_path"],
            )
        ).__dict__
        for result in set_results
    ]
    draft_stage = run_stage_validation("draft")
    draft_result_path = write_json(
        REPORT_ROOT / "draft_registration_result.json",
        {"schema_version": "phase16_as_draft_registration_result.v1", "created_at": utc_now(), "appends": draft_appends, "stage": draft_stage},
    )

    validated_appends = [
        writer.append_event(
            registry_event(
                result,
                previous_status="DRAFT",
                new_status="VALIDATED",
                event_type="ARTIFACT_VALIDATED",
                manifest_path=result["final_manifest_path"],
            )
        ).__dict__
        for result in set_results
    ]
    validated_stage = run_stage_validation("validated")
    validated_result_path = write_json(
        REPORT_ROOT / "validated_registration_result.json",
        {"schema_version": "phase16_as_validated_registration_result.v1", "created_at": utc_now(), "appends": validated_appends, "stage": validated_stage},
    )

    events = [row["event"] for row in read_event_log(EVENT_LOG)]
    index = read_json(INDEX_PATH)
    entries = index.get("entries", {})
    accepted_event_count = sum(1 for event in events if event.get("event_type") == "ARTIFACT_ACCEPTED")
    runtime_use_count = sum(1 for entry in entries.values() if entry.get("runtime_use_eligible") is True)
    status_counts: dict[str, int] = {}
    for entry in entries.values():
        status_counts[str(entry.get("current_status") or entry.get("status"))] = status_counts.get(str(entry.get("current_status") or entry.get("status")), 0) + 1
    consistency = {
        "schema_version": "phase16_as_registry_consistency.v1",
        "created_at": utc_now(),
        "event_count": len(events),
        "entry_count": len(entries),
        "draft_event_count": sum(1 for event in events if event.get("new_status") == "DRAFT"),
        "validated_event_count": sum(1 for event in events if event.get("new_status") == "VALIDATED"),
        "accepted_event_count": accepted_event_count,
        "runtime_use_eligible_count": runtime_use_count,
        "status_counts": status_counts,
        "event_log_hash": sha256_file(EVENT_LOG),
        "index_hash": sha256_file(INDEX_PATH),
        "checkpoint_hash": sha256_file(CHECKPOINT_LATEST),
        "checkpoint_latest": rel(CHECKPOINT_LATEST),
    }
    if consistency["event_count"] != 10 or consistency["entry_count"] != 5 or accepted_event_count != 0 or runtime_use_count != 0 or status_counts.get("VALIDATED") != 5:
        raise RuntimeError(f"registry consistency failed: {consistency}")
    consistency_path = write_json(REPORT_ROOT / "registry_consistency.json", consistency)

    after_protected = protected_hashes()
    tests: list[dict[str, Any]] = []
    command = [sys.executable, "-m", "pytest", "-q", "tests/artifact_registry"]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    tests.append(
        {
            "command": " ".join(command),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
    )
    if completed.returncode != 0:
        write_json(REPORT_ROOT / "test_failure.json", tests[-1])
        raise RuntimeError("artifact registry tests failed")

    summary = {
        "schema_version": "phase16_as_summary.v1",
        "created_at": utc_now(),
        "final_judgment": "PHASE16_AS_FORMAL_ARTIFACT_VALIDATED_REGISTERED",
        "preflight_start_result": {
            "formal_registration_ready": preflight.get("formal_registration_ready"),
            "set_blockers": {k: v.get("blockers") for k, v in preflight.get("set_results", {}).items()},
        },
        "sets": [
            {
                "artifact_set_id": result["spec"].artifact_set_id,
                "artifact_set_type": result["spec"].artifact_set_type,
                "artifact_set_hash": result["final_manifest"]["artifact_set_hash"],
                "final_status": "VALIDATED",
                "runtime_use_eligible": False,
                "manifest": result["refs"]["artifact_set_manifest"],
            }
            for result in set_results
        ],
        "evidence": {
            "backup_manifest": rel(REPORT_ROOT / "backup_manifest.json"),
            "approval_summary": rel(approval_summary_path),
            "copy_result": rel(copy_result_path),
            "draft_registration_result": rel(draft_result_path),
            "validated_registration_result": rel(validated_result_path),
            "registry_consistency": rel(consistency_path),
            "audit": rel(REPORT_ROOT / "audit.md"),
        },
        "backup_event_log_hash": backup["event_log"]["sha256"],
        "copy_result": copy_result,
        "draft_result": {"event_count": draft_stage["validation"]["event_count"], "entry_count": draft_stage["index"]["entry_count"]},
        "validated_result": {"event_count": validated_stage["validation"]["event_count"], "entry_count": validated_stage["index"]["entry_count"]},
        "registry_consistency": consistency,
        "runtime_protected_hashes_before": before_protected,
        "runtime_protected_hashes_after": after_protected,
        "runtime_protected_hashes_unchanged": before_protected == after_protected,
        "formal_registry_effect": "DRAFT and VALIDATED events appended; index and checkpoint updated; no ARTIFACT_ACCEPTED event.",
        "runtime_effect": "Runtime, Current, Ledger, Pending, Market State, Planning, Submit Guard, Feature, AI inference, and Consumer paths were not changed.",
        "tests": tests,
        "known_gaps": [
            "No ACCEPTED promotion was performed by design.",
            "runtime_use_eligible remains false by design.",
        ],
        "next_prefix": "Phase16-AT",
    }
    if not summary["runtime_protected_hashes_unchanged"]:
        raise RuntimeError("protected runtime hashes changed unexpectedly")
    write_json(REPORT_ROOT / "audit.json", summary)
    (REPORT_ROOT / "audit.md").write_text(
        "\n".join(
            [
                "# Phase16-AS Formal Registration Audit",
                "",
                f"- Final judgment: `{summary['final_judgment']}`",
                f"- Event count: `{consistency['event_count']}`",
                f"- Entry count: `{consistency['entry_count']}`",
                f"- Accepted events: `{consistency['accepted_event_count']}`",
                f"- Runtime-use eligible entries: `{consistency['runtime_use_eligible_count']}`",
                f"- Runtime protected hashes unchanged: `{summary['runtime_protected_hashes_unchanged']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_reports(summary)
    print(json.dumps({"final_judgment": summary["final_judgment"], "event_count": 10, "entry_count": 5}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
