from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.inventory import sha256_file, stable_json_hash


BOOTSTRAP_GENERATION_VERSION = "phase19_ad_u1_b_bootstrap_generation_v1"
BOOTSTRAP_GENERATION_SCHEMA_VERSION = "accepted_buy_ai_generation_manifest.v1"
HUMAN_REVIEW_SCHEMA_VERSION = "bootstrap_generation_human_review.v1"
ACCEPTED_DECISION_SCHEMA_VERSION = "bootstrap_accepted_generation_decision.v1"

REUSE_ELIGIBLE = "REUSE_ELIGIBLE"
REUSE_REVIEW_REQUIRED = "REUSE_REVIEW_REQUIRED"
REUSE_BLOCKED = "REUSE_BLOCKED"

REQUIRED_COMPONENT_ROLES = {
    "candidate": {"MODEL", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE"},
    "opportunity": {"MODEL", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE"},
}


class BootstrapGenerationError(RuntimeError):
    pass


class BootstrapGenerationValidationError(BootstrapGenerationError):
    pass


class HumanReviewError(BootstrapGenerationError):
    pass


@dataclass(frozen=True)
class BootstrapArtifacts:
    generation_candidate: dict[str, Any]
    accepted_manifest: dict[str, Any] | None
    accepted_decision: dict[str, Any] | None
    human_review_validation: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def generation_hash(payload: dict[str, Any]) -> str:
    return stable_json_hash({key: value for key, value in payload.items() if key not in {"aggregate_hash"}})


def reviewed_payload_hash(payload: dict[str, Any]) -> str:
    return str(payload.get("aggregate_hash") or generation_hash(payload))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def component_member_by_role(component: dict[str, Any], role: str) -> dict[str, Any] | None:
    for member in component.get("members") or component.get("member_artifacts") or []:
        if str(member.get("member_role") or member.get("role") or "").upper() == role:
            return member
    return None


def evaluate_component_reuse(
    *,
    component_type: str,
    component: dict[str, Any],
    repo_root: Path | str = Path.cwd(),
    expected_schema_hashes: dict[str, str] | None = None,
    validation_applicability: dict[str, Any] | None = None,
    freshness: dict[str, Any] | None = None,
    policy_version: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    expected_schema_hashes = expected_schema_hashes or {}
    checks: dict[str, Any] = {}
    blockers: list[str] = []
    review_reasons: list[str] = []
    member_records: list[dict[str, Any]] = []

    required_roles = REQUIRED_COMPONENT_ROLES[component_type]
    for role in sorted(required_roles):
        member = component_member_by_role(component, role)
        if not member:
            blockers.append(f"missing_member_role:{role}")
            continue
        physical = str(member.get("physical_path") or "")
        path = repo / physical if physical and not Path(physical).is_absolute() else Path(physical)
        exists = path.is_file()
        actual_hash = sha256_file(path) if exists else None
        expected_hash = str(member.get("content_hash") or "")
        schema_hash = str(member.get("schema_hash") or "")
        if not exists:
            blockers.append(f"member_file_missing:{role}")
        if actual_hash and expected_hash and actual_hash != expected_hash:
            blockers.append(f"member_hash_mismatch:{role}")
        expected_schema = expected_schema_hashes.get(role)
        if expected_schema and schema_hash != expected_schema:
            blockers.append(f"schema_hash_mismatch:{role}")
        member_records.append(
            {
                "role": role,
                "logical_artifact_id": member.get("logical_artifact_id"),
                "artifact_path": physical,
                "artifact_hash": expected_hash,
                "actual_hash": actual_hash,
                "schema_hash": schema_hash,
                "exists": exists,
            }
        )

    if component_type == "opportunity":
        linked_candidate = str(component.get("candidate_member_ref") or component.get("candidate_source_ref") or "")
        if linked_candidate and linked_candidate != "same_generation_candidate_member":
            review_reasons.append("opportunity_candidate_binding_requires_same_generation_manifest")

    if component.get("known_exceptions"):
        review_reasons.append("known_exceptions_require_human_review")
    if not validation_applicability or validation_applicability.get("status") not in {"PASS", "APPLICABLE"}:
        review_reasons.append("validation_applicability_missing_or_not_pass")
    if not freshness or freshness.get("status") not in {"PASS", "ELIGIBLE"}:
        review_reasons.append("freshness_status_missing_or_not_pass")
    if not policy_version:
        review_reasons.append("policy_version_missing")

    checks["required_roles"] = sorted(required_roles)
    checks["members"] = member_records
    checks["validation_applicability"] = validation_applicability or {}
    checks["freshness"] = freshness or {}
    checks["policy_version"] = policy_version
    decision = REUSE_BLOCKED if blockers else (REUSE_REVIEW_REQUIRED if review_reasons else REUSE_ELIGIBLE)
    return {
        "component_type": component_type,
        "source_generation": component.get("source_generation") or component.get("artifact_set_id"),
        "component_revision": component.get("artifact_set_hash") or component.get("content_hash"),
        "reused": decision != REUSE_BLOCKED,
        "artifact_path": component_member_by_role(component, "MODEL").get("physical_path") if component_member_by_role(component, "MODEL") else None,
        "artifact_hash": component.get("artifact_set_hash") or component.get("content_hash"),
        "model_hash": (component_member_by_role(component, "MODEL") or {}).get("content_hash"),
        "schema_hash": stable_json_hash(component.get("schema_hashes") or {}),
        "dataset_lineage": component.get("source_lineage_ref"),
        "training_cutoff": component.get("training_cutoff"),
        "validation_evidence": component.get("validation_evidence_refs") or [],
        "validation_applicability": validation_applicability or {},
        "freshness_status": (freshness or {}).get("status", "MISSING"),
        "policy_version": policy_version,
        "reuse_decision": decision,
        "reuse_reason": ";".join(blockers or review_reasons or ["reuse_contract_pass"]),
        "checks": checks,
    }


def build_bootstrap_generation_candidate(
    *,
    generation_id: str,
    candidate_component: dict[str, Any],
    opportunity_component: dict[str, Any],
    candidate_reuse: dict[str, Any],
    opportunity_reuse: dict[str, Any],
    calibration_member: dict[str, Any],
    validation: dict[str, Any],
    runtime_baseline: dict[str, Any],
    freshness: dict[str, Any],
    dataset_lineage: dict[str, Any],
    split: dict[str, Any],
    source_commit: str,
    policy_versions: dict[str, str],
    effective_from: str,
    rollback_reference: dict[str, Any],
    bootstrap_reason: str,
    human_review_reference: str | None = None,
    previous_generation: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if candidate_reuse.get("reuse_decision") == REUSE_BLOCKED:
        raise BootstrapGenerationValidationError("candidate reuse is blocked")
    if opportunity_reuse.get("reuse_decision") == REUSE_BLOCKED:
        raise BootstrapGenerationValidationError("opportunity reuse is blocked")
    if not calibration_member:
        raise BootstrapGenerationValidationError("calibration member is required")
    if not runtime_baseline:
        raise BootstrapGenerationValidationError("runtime baseline is required")
    if not validation.get("validation_applicability"):
        raise BootstrapGenerationValidationError("validation applicability is required")
    _validate_temporal_fields(dataset_lineage, split, freshness, effective_from)

    candidate_member = _member_ref(candidate_component, "candidate", "MODEL")
    opportunity_member = _member_ref(opportunity_component, "opportunity", "MODEL")
    opportunity_member["candidate_member_ref"] = candidate_member["member_id"]
    payload = {
        "schema_version": BOOTSTRAP_GENERATION_SCHEMA_VERSION,
        "builder_version": BOOTSTRAP_GENERATION_VERSION,
        "generation_id": generation_id,
        "generation_type": "BOOTSTRAP",
        "authority_scope": "BUY_AI_ACCEPTED_GENERATION_DRAFT",
        "dataset_lineage": dataset_lineage,
        "split": split,
        "candidate_member": candidate_member,
        "opportunity_member": opportunity_member,
        "calibration_member": calibration_member,
        "validation": validation,
        "runtime_baseline": runtime_baseline,
        "freshness": freshness,
        "component_hashes": {
            "candidate": candidate_reuse.get("artifact_hash"),
            "opportunity": opportunity_reuse.get("artifact_hash"),
            "calibration": calibration_member.get("content_hash"),
            "runtime_baseline": runtime_baseline.get("baseline_hash") or runtime_baseline.get("content_hash"),
        },
        "component_reuse": {
            "candidate": candidate_reuse,
            "opportunity": opportunity_reuse,
        },
        "authority_decision": "REVIEW_REQUIRED",
        "previous_generation": previous_generation,
        "source_commit": source_commit,
        "policy_versions": policy_versions,
        "effective_from": effective_from,
        "accepted_at": None,
        "rollback_reference": rollback_reference,
        "bootstrap_reason": bootstrap_reason,
        "human_review_reference": human_review_reference,
        "created_at": created_at or utc_now(),
        "runtime_transition_state": "NOT_COMMITTED",
        "runtime_pointer_written": False,
        "legacy_runtime_authority": False,
    }
    payload["aggregate_hash"] = generation_hash(payload)
    return payload


def validate_bootstrap_generation_manifest(manifest: dict[str, Any], *, accepted: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    required = {
        "generation_id",
        "generation_type",
        "authority_scope",
        "dataset_lineage",
        "split",
        "candidate_member",
        "opportunity_member",
        "calibration_member",
        "validation",
        "runtime_baseline",
        "freshness",
        "component_hashes",
        "aggregate_hash",
        "authority_decision",
        "source_commit",
        "policy_versions",
        "effective_from",
        "rollback_reference",
        "bootstrap_reason",
        "human_review_reference",
    }
    for field in sorted(required):
        if field not in manifest:
            errors.append(f"missing_field:{field}")
    if manifest.get("generation_type") != "BOOTSTRAP":
        errors.append("generation_type_must_be_BOOTSTRAP")
    if manifest.get("opportunity_member", {}).get("candidate_member_ref") != manifest.get("candidate_member", {}).get("member_id"):
        errors.append("opportunity_candidate_member_binding_mismatch")
    if manifest.get("aggregate_hash") != generation_hash(manifest):
        errors.append("aggregate_hash_mismatch")
    if manifest.get("runtime_pointer_written") is not False:
        errors.append("runtime_pointer_written_forbidden")
    if manifest.get("runtime_transition_state") == "COMMITTED":
        errors.append("committed_transition_forbidden_in_ad_u1_b")
    if accepted:
        if manifest.get("authority_decision") != "ACCEPTED":
            errors.append("accepted_manifest_requires_authority_decision_ACCEPTED")
        if not manifest.get("accepted_at"):
            errors.append("accepted_manifest_requires_accepted_at")
    return {
        "schema_version": "bootstrap_generation_manifest_validation.v1",
        "overall_result": "PASS" if not errors else "FAIL",
        "failure_class": "NONE" if not errors else "HALT",
        "errors": errors,
    }


def build_human_review_artifact(
    *,
    generation_manifest: dict[str, Any],
    reviewer: str,
    decision: str,
    decision_reason: str,
    limitations: list[str] | None = None,
    required_followups: list[str] | None = None,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": HUMAN_REVIEW_SCHEMA_VERSION,
        "review_id": f"bootstrap-review-{uuid.uuid4()}",
        "generation_id": generation_manifest["generation_id"],
        "reviewed_at": reviewed_at or utc_now(),
        "reviewer": reviewer,
        "decision": decision,
        "decision_reason": decision_reason,
        "reviewed_hash": reviewed_payload_hash(generation_manifest),
        "limitations": limitations or [],
        "required_followups": required_followups or [],
    }


def materialize_accepted_generation(
    *,
    generation_candidate: dict[str, Any],
    human_review: dict[str, Any] | None,
) -> BootstrapArtifacts:
    review_validation = validate_human_review(generation_candidate=generation_candidate, human_review=human_review)
    if review_validation["overall_result"] != "PASS":
        return BootstrapArtifacts(generation_candidate, None, None, review_validation)
    accepted_manifest = dict(generation_candidate)
    accepted_manifest["authority_scope"] = "BUY_AI_ACCEPTED_GENERATION"
    accepted_manifest["authority_decision"] = "ACCEPTED"
    accepted_manifest["accepted_at"] = human_review["reviewed_at"]
    accepted_manifest["human_review_reference"] = human_review["review_id"]
    accepted_manifest["runtime_transition_state"] = "NOT_COMMITTED"
    accepted_manifest["runtime_pointer_written"] = False
    accepted_manifest["aggregate_hash"] = generation_hash(accepted_manifest)
    accepted_decision = {
        "schema_version": ACCEPTED_DECISION_SCHEMA_VERSION,
        "generation_id": accepted_manifest["generation_id"],
        "decision": "ACCEPTED",
        "accepted_at": accepted_manifest["accepted_at"],
        "accepted_manifest_hash": accepted_manifest["aggregate_hash"],
        "review_id": human_review["review_id"],
        "reviewed_hash": human_review["reviewed_hash"],
        "runtime_transition_state": "NOT_COMMITTED",
        "runtime_pointer_written": False,
    }
    return BootstrapArtifacts(generation_candidate, accepted_manifest, accepted_decision, review_validation)


def validate_human_review(
    *,
    generation_candidate: dict[str, Any],
    human_review: dict[str, Any] | None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not human_review:
        errors.append("human_review_missing")
        return _review_result(errors)
    if human_review.get("schema_version") != HUMAN_REVIEW_SCHEMA_VERSION:
        errors.append("human_review_schema_mismatch")
    if human_review.get("generation_id") != generation_candidate.get("generation_id"):
        errors.append("human_review_generation_id_mismatch")
    if human_review.get("decision") != "APPROVE":
        errors.append("human_review_not_approved")
    if not human_review.get("reviewer"):
        errors.append("human_review_reviewer_missing")
    if human_review.get("reviewed_hash") != reviewed_payload_hash(generation_candidate):
        errors.append("human_review_hash_mismatch")
    return _review_result(errors)


def registry_append_evidence(*, event_log_before: dict[str, Any] | None, event_log_after: dict[str, Any] | None = None) -> dict[str, Any]:
    before_count = int((event_log_before or {}).get("event_count") or 0)
    after_count = int((event_log_after or event_log_before or {}).get("event_count") or 0)
    return {
        "schema_version": "bootstrap_generation_registry_append_evidence.v1",
        "registry_append_performed": event_log_after is not None and after_count == before_count + 1,
        "append_only": after_count >= before_count,
        "event_count_before": before_count,
        "event_count_after": after_count,
        "runtime_pointer_written": False,
        "reason": "AD-U1-B does not perform Runtime Transition COMMITTED pointer replacement.",
    }


def _review_result(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "bootstrap_generation_human_review_validation.v1",
        "overall_result": "PASS" if not errors else "REVIEW_REQUIRED",
        "failure_class": "NONE" if not errors else "REVIEW_REQUIRED",
        "errors": errors,
    }


def _member_ref(component: dict[str, Any], component_type: str, role: str) -> dict[str, Any]:
    member = component_member_by_role(component, role)
    if not member:
        raise BootstrapGenerationValidationError(f"{component_type} {role} member missing")
    return {
        "member_id": f"{component_type}:{member.get('logical_artifact_id')}",
        "component_type": component_type,
        "source_artifact_set_id": component.get("artifact_set_id"),
        "logical_artifact_id": member.get("logical_artifact_id"),
        "artifact_path": member.get("physical_path"),
        "artifact_hash": member.get("content_hash"),
        "model_hash": member.get("content_hash") if role == "MODEL" else None,
        "schema_hash": member.get("schema_hash"),
    }


def _validate_temporal_fields(dataset_lineage: dict[str, Any], split: dict[str, Any], freshness: dict[str, Any], effective_from: str) -> None:
    if not effective_from:
        raise BootstrapGenerationValidationError("effective_from is required")
    if not (dataset_lineage.get("training_cutoff") or freshness.get("model_training_cutoff")):
        raise BootstrapGenerationValidationError("training_cutoff is required")
    if not (dataset_lineage.get("calibration_cutoff") or split.get("calibration", {}).get("end")):
        raise BootstrapGenerationValidationError("calibration_cutoff is required")
    if not dataset_lineage.get("dataset_version"):
        raise BootstrapGenerationValidationError("dataset lineage is required")
