from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import (
    artifact_set_hash,
    load_schemas,
    normalized_member_role,
    read_json,
    schema_validate,
)


ACCEPTANCE_EVIDENCE_VERSION = "phase16ak_acceptance_evidence_v1"
DEFAULT_SCHEMA_ROOT = Path("docs/02_architecture/schemas")
DEFAULT_CONTRACT_PATH = Path("docs/02_architecture/contracts/artifact_acceptance_role_compatibility.v1.json")
DEFAULT_OUTPUT_ROOT = Path("reports/phase16_acceptance_evidence")
FORMAL_REGISTRY_ROOT = Path(".runtime/artifact_registry")


class AcceptanceEvidenceError(RuntimeError):
    pass


class AcceptanceOutputSafetyError(AcceptanceEvidenceError):
    pass


@dataclass(frozen=True)
class AcceptanceEvidencePaths:
    artifact_set_manifest: Path
    acceptance_report: Path
    regression_evidence: Path
    approvals: tuple[Path, ...]
    source_lineage: Path
    freeze_manifest: Path
    consumer_compatibility: Path
    rollback_target: Path | None = None

    def all_paths(self) -> tuple[Path, ...]:
        optional = (self.rollback_target,) if self.rollback_target is not None else ()
        return (
            self.artifact_set_manifest,
            self.acceptance_report,
            self.regression_evidence,
            *self.approvals,
            self.source_lineage,
            self.freeze_manifest,
            self.consumer_compatibility,
            *optional,
        )


def sha256_file_bytes(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_hash(payload: dict[str, Any], *, exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    body = {key: value for key, value in payload.items() if key not in exclude}
    return stable_json_hash(body)


def evidence_key(path: Path) -> str:
    return path.name


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class AcceptanceEvidenceBundleBuilder:
    def __init__(
        self,
        *,
        paths: AcceptanceEvidencePaths,
        schema_root: Path | str = DEFAULT_SCHEMA_ROOT,
        contract_path: Path | str = DEFAULT_CONTRACT_PATH,
        repo_root: Path | str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.paths = paths
        self.schema_root = self._resolve(schema_root)
        self.contract_path = self._resolve(contract_path)
        self.schemas = load_schemas(self.schema_root)
        self.contract = read_json(self.contract_path)

    def build_bundle(self) -> dict[str, Any]:
        manifest = read_json(self.paths.artifact_set_manifest)
        report = read_json(self.paths.acceptance_report)
        regression = read_json(self.paths.regression_evidence)
        approvals = [read_json(path) for path in self.paths.approvals]
        evidence_hashes = {evidence_key(path): sha256_file_bytes(path) for path in self.paths.all_paths()}
        artifact_set_id = str(manifest.get("artifact_set_id") or report.get("artifact_set_id") or regression.get("artifact_set_id") or "")
        artifact_set_type = str(manifest.get("artifact_set_type") or report.get("artifact_set_type") or regression.get("artifact_set_type") or "")
        bundle = {
            "schema_version": "artifact_acceptance_evidence_bundle.v1",
            "evidence_bundle_id": f"acceptance-bundle-{uuid.uuid4()}-{canonical_json_hash(evidence_hashes)[:16]}",
            "artifact_set_id": artifact_set_id,
            "artifact_set_type": artifact_set_type,
            "artifact_set_manifest_ref": str(self.paths.artifact_set_manifest),
            "acceptance_report_ref": str(self.paths.acceptance_report),
            "regression_evidence_ref": str(self.paths.regression_evidence),
            "approval_refs": [
                {
                    "role": str(item.get("approval_role") or item.get("approval_type") or ""),
                    "approval_ref": str(path),
                    "approval_hash": evidence_hashes[evidence_key(path)],
                    "subject_ref": str(item.get("subject_ref") or ""),
                    "reviewer_id": str(item.get("reviewer_id") or ""),
                    "decision": str(item.get("decision") or ""),
                }
                for path, item in zip(self.paths.approvals, approvals)
            ],
            "source_lineage_ref": str(self.paths.source_lineage),
            "freeze_manifest_ref": str(self.paths.freeze_manifest),
            "consumer_compatibility_ref": str(self.paths.consumer_compatibility),
            "rollback_target_ref": str(self.paths.rollback_target) if self.paths.rollback_target else None,
            "evidence_hashes": evidence_hashes,
            "created_at": utc_now(),
            "expires_at": None,
        }
        return bundle

    def _resolve(self, path: Path | str) -> Path:
        value = Path(path)
        return value if value.is_absolute() else self.repo_root / value


class AcceptanceEvidenceBundleValidator:
    def __init__(
        self,
        *,
        paths: AcceptanceEvidencePaths,
        bundle: dict[str, Any] | None = None,
        schema_root: Path | str = DEFAULT_SCHEMA_ROOT,
        contract_path: Path | str = DEFAULT_CONTRACT_PATH,
        repo_root: Path | str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.paths = paths
        self.schema_root = self._resolve(schema_root)
        self.contract_path = self._resolve(contract_path)
        self.schemas = load_schemas(self.schema_root)
        self.contract = read_json(self.contract_path)
        self.bundle = bundle

    def validate(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        member_results: dict[str, str] = {}
        set_result = "PASS"
        role_result = "PASS"
        regression_result = "PASS"
        compatibility_result = "PASS"
        point_in_time_result = "PASS"

        documents = self._load_documents(errors)
        manifest = documents.get("manifest") or {}
        report = documents.get("report") or {}
        regression = documents.get("regression") or {}
        approvals = list(documents.get("approvals") or [])
        source = documents.get("source") or {}
        freeze = documents.get("freeze") or {}
        compatibility = documents.get("compatibility") or {}
        rollback = documents.get("rollback")
        bundle = self.bundle or AcceptanceEvidenceBundleBuilder(paths=self.paths, schema_root=self.schema_root, contract_path=self.contract_path, repo_root=self.repo_root).build_bundle()

        self._schema_check("artifact_set_manifest.schema.json", manifest, "$.manifest", errors)
        self._schema_check("artifact_acceptance_report.schema.json", report, "$.acceptance_report", errors)
        self._schema_check("artifact_regression_evidence.schema.json", regression, "$.regression", errors)
        for index, approval in enumerate(approvals):
            self._schema_check("artifact_review_approval.schema.json", approval, f"$.approvals[{index}]", errors)
        self._schema_check("artifact_acceptance_evidence_bundle.schema.json", bundle, "$.bundle", errors)

        artifact_set_id = str(manifest.get("artifact_set_id") or "")
        artifact_set_type = str(manifest.get("artifact_set_type") or "")
        if artifact_set_type in self.contract.get("legacy_aliases", {}):
            errors.append(f"legacy artifact_set_type is not allowed for new bundle output: {artifact_set_type}")

        set_errors = len(errors)
        self._validate_manifest(manifest, member_results, errors, warnings)
        if len(errors) > set_errors:
            set_result = "HALT"

        role_errors = len(errors)
        self._validate_approvals(artifact_set_id, artifact_set_type, manifest, approvals, errors, warnings)
        if len(errors) > role_errors:
            role_result = "HALT"

        report_errors = len(errors)
        self._validate_report(artifact_set_id, artifact_set_type, manifest, report, bundle, errors)
        if len(errors) > report_errors:
            set_result = "HALT"

        regression_errors = len(errors)
        self._validate_regression(artifact_set_id, artifact_set_type, regression, errors)
        if len(errors) > regression_errors:
            regression_result = "HALT"
        if regression.get("point_in_time_result") != "PASS":
            point_in_time_result = "HALT"

        compatibility_errors = len(errors)
        self._validate_generic_evidence("source_lineage", source, artifact_set_id, artifact_set_type, warnings, errors, required_result=False)
        self._validate_freeze_manifest(freeze, manifest, artifact_set_id, artifact_set_type, warnings, errors)
        self._validate_consumer_compatibility(compatibility, artifact_set_id, artifact_set_type, errors)
        if len(errors) > compatibility_errors:
            compatibility_result = "HALT"

        self._validate_rollback(report, bundle, rollback, errors)
        self._validate_evidence_hashes(bundle, errors)
        self._validate_duplicate_evidence(bundle, errors)
        bundle_hash = bundle_hash_for(bundle)

        failure_class = "HALT" if errors else ("REVIEW_REQUIRED" if warnings else "NONE")
        overall = "FAIL" if failure_class == "HALT" else ("REVIEW_REQUIRED" if failure_class == "REVIEW_REQUIRED" else "PASS")
        eligibility = "PASS" if overall == "PASS" else ("REVIEW_REQUIRED" if overall == "REVIEW_REQUIRED" else "HALT")
        result = {
            "schema_version": "artifact_acceptance_validation_result.v1",
            "validation_id": f"acceptance-validation-{uuid.uuid4()}",
            "validated_at": utc_now(),
            "artifact_set_id": artifact_set_id or "UNKNOWN",
            "artifact_set_type": artifact_set_type if artifact_set_type in self.contract.get("artifact_set_types", {}) else "CANDIDATE_AI_SET",
            "set_validation_result": set_result,
            "member_validation_results": member_results,
            "role_validation_result": role_result,
            "regression_validation_result": regression_result,
            "compatibility_validation_result": compatibility_result,
            "point_in_time_validation_result": point_in_time_result,
            "eligibility_result": eligibility,
            "overall_result": overall,
            "failure_class": failure_class,
            "errors": errors,
            "warnings": warnings,
        }
        self._schema_check("artifact_acceptance_validation_result.schema.json", result, "$.validation_result", errors)
        return {
            "schema_version": "phase16ak_acceptance_evidence_validation_output.v1",
            "builder_version": ACCEPTANCE_EVIDENCE_VERSION,
            "bundle": bundle,
            "bundle_hash": bundle_hash,
            "validation_result": result,
            "eligibility_candidate_result": eligibility_candidate(overall),
            "evidence_refs": [str(path) for path in self.paths.all_paths()],
            "recommended_action": recommended_action(overall),
        }

    def _load_documents(self, errors: list[str]) -> dict[str, Any]:
        docs: dict[str, Any] = {}
        mapping = {
            "manifest": self.paths.artifact_set_manifest,
            "report": self.paths.acceptance_report,
            "regression": self.paths.regression_evidence,
            "source": self.paths.source_lineage,
            "freeze": self.paths.freeze_manifest,
            "compatibility": self.paths.consumer_compatibility,
        }
        for key, path in mapping.items():
            docs[key] = self._read_json(path, errors)
        docs["approvals"] = [self._read_json(path, errors) for path in self.paths.approvals]
        docs["rollback"] = self._read_json(self.paths.rollback_target, errors) if self.paths.rollback_target else None
        return docs

    def _read_json(self, path: Path | None, errors: list[str]) -> dict[str, Any]:
        if path is None:
            return {}
        try:
            return read_json(path)
        except Exception as exc:
            errors.append(f"evidence file missing or unreadable: {path}: {exc}")
            return {}

    def _schema_check(self, schema_name: str, payload: dict[str, Any], field_path: str, errors: list[str]) -> None:
        schema = self.schemas.get(schema_name)
        if not schema:
            errors.append(f"schema missing: {schema_name}")
            return
        for issue in schema_validate(payload, schema, field_path=field_path):
            errors.append(f"{field_path}: {issue['message']}")

    def _validate_manifest(self, manifest: dict[str, Any], member_results: dict[str, str], errors: list[str], warnings: list[str]) -> None:
        set_id = str(manifest.get("artifact_set_id") or "")
        set_type = str(manifest.get("artifact_set_type") or "")
        set_contract = self.contract.get("artifact_set_types", {}).get(set_type)
        if not set_contract:
            errors.append(f"unknown formal artifact_set_type: {set_type}")
            return
        if manifest.get("set_authority_scope") != "SET_LEVEL":
            errors.append("set_authority_scope must be SET_LEVEL")
        required_roles = set(set_contract["required_member_roles"])
        declared_required = set(manifest.get("required_member_roles") or [])
        if declared_required != required_roles:
            errors.append("required_member_roles do not match compatibility contract")
        members = list(manifest.get("member_artifacts") or [])
        roles = [normalized_member_role(member) for member in members]
        missing = sorted(required_roles - set(roles))
        if missing:
            errors.append("missing required member roles: " + ",".join(missing))
        duplicates = sorted(role for role in set(roles) if roles.count(role) > 1)
        if duplicates:
            errors.append("duplicate member roles: " + ",".join(duplicates))
        member_hashes = manifest.get("member_hashes") or {}
        schema_hashes = manifest.get("schema_hashes") or {}
        for member in members:
            role = normalized_member_role(member)
            logical_id = str(member.get("logical_artifact_id") or "")
            member_results[role or logical_id] = "PASS"
            if member.get("artifact_set_id") not in {None, set_id}:
                member_results[role] = "HALT"
                errors.append(f"member {role} artifact_set_id mismatch")
            if member.get("status") not in {"VALIDATED", "ACCEPTED"}:
                member_results[role] = "HALT"
                errors.append(f"member {role} status is not acceptance-ready")
            if member.get("runtime_use_eligible") is not False:
                member_results[role] = "HALT"
                errors.append(f"member {role} runtime_use_eligible must be false before set acceptance")
            if logical_id and member_hashes.get(logical_id) != member.get("content_hash"):
                member_results[role] = "HALT"
                errors.append(f"member {role} content_hash does not match member_hashes")
            if logical_id and schema_hashes.get(logical_id) != member.get("schema_hash"):
                member_results[role] = "HALT"
                errors.append(f"member {role} schema_hash does not match schema_hashes")
        expected_set_hash = artifact_set_hash(manifest)
        if manifest.get("artifact_set_hash") != expected_set_hash:
            errors.append("artifact_set_hash mismatch")
        for field in ("consumer_compatibility_ref", "source_lineage_ref", "freeze_manifest_ref"):
            if not manifest.get(field):
                errors.append(f"{field} missing")
        self._validate_same_set_constraints(set_type, members, errors)

    def _validate_same_set_constraints(self, set_type: str, members: list[dict[str, Any]], errors: list[str]) -> None:
        constraints = self.contract["artifact_set_types"].get(set_type, {}).get("same_set_constraints", [])
        if not constraints:
            return
        by_role = {normalized_member_role(member): member for member in members}
        for role in constraints:
            if role not in by_role:
                return
        set_ids = {by_role[role].get("artifact_set_id") for role in constraints}
        if len(set_ids - {None}) > 1:
            errors.append(f"{set_type} same-set constraint failed: " + ",".join(constraints))
        source_refs = {json.dumps(by_role[role].get("source_refs", []), sort_keys=True) for role in constraints if by_role[role].get("source_refs") is not None}
        if len(source_refs) > 1:
            errors.append(f"{set_type} source lineage mismatch for same-set roles")

    def _validate_approvals(self, set_id: str, set_type: str, manifest: dict[str, Any], approvals: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> None:
        required_roles = set(self.contract["artifact_set_types"].get(set_type, {}).get("required_roles", []))
        roles = [str(item.get("approval_role") or item.get("approval_type") or "") for item in approvals]
        missing = sorted(required_roles - set(roles))
        if missing:
            errors.append("missing approval roles: " + ",".join(missing))
        duplicates = sorted(role for role in set(roles) if roles.count(role) > 1)
        if duplicates:
            errors.append("duplicate approval roles: " + ",".join(duplicates))
        now = datetime.now(timezone.utc)
        for approval in approvals:
            role = str(approval.get("approval_role") or approval.get("approval_type") or "")
            if approval.get("subject_type") not in {"ARTIFACT_SET", None}:
                errors.append(f"approval {role} subject_type must be ARTIFACT_SET")
            if approval.get("subject_ref") != set_id:
                errors.append(f"approval {role} subject_ref mismatch")
            if approval.get("artifact_set_type") not in {set_type, None}:
                errors.append(f"approval {role} artifact_set_type mismatch")
            if approval.get("decision") != "APPROVED":
                errors.append(f"approval {role} decision is not APPROVED")
            if approval.get("reviewed_hash") not in {manifest.get("artifact_set_hash"), None}:
                errors.append(f"approval {role} reviewed_hash mismatch")
            if not approval.get("evidence_refs"):
                errors.append(f"approval {role} evidence_refs missing")
            expires = parse_datetime(approval.get("expires_at"))
            if expires and expires < now:
                errors.append(f"approval {role} expired")

    def _validate_report(self, set_id: str, set_type: str, manifest: dict[str, Any], report: dict[str, Any], bundle: dict[str, Any], errors: list[str]) -> None:
        if report.get("artifact_set_id") != set_id or report.get("artifact_or_set_ref") != set_id:
            errors.append("acceptance report artifact_set_id/subject mismatch")
        if report.get("artifact_set_type") != set_type:
            errors.append("acceptance report artifact_set_type mismatch")
        if report.get("artifact_set_manifest_ref") != bundle.get("artifact_set_manifest_ref"):
            errors.append("acceptance report manifest ref mismatch")
        if report.get("artifact_set_hash") != manifest.get("artifact_set_hash"):
            errors.append("acceptance report artifact_set_hash mismatch")
        if report.get("decision") != "ACCEPT":
            errors.append("acceptance report decision is not ACCEPT")
        for field, expected in (("regression_result", "PASS"), ("consumer_compatibility_result", "PASS"), ("point_in_time_result", "PASS")):
            if report.get(field) != expected:
                errors.append(f"acceptance report {field} is not {expected}")
        if report.get("evidence_bundle_ref") not in {bundle.get("evidence_bundle_id"), None}:
            errors.append("acceptance report evidence_bundle_ref mismatch")
        member_hashes = manifest.get("member_hashes") or {}
        reviewed = report.get("reviewed_member_hashes") or report.get("reviewed_artifact_hashes") or {}
        if reviewed and reviewed != member_hashes:
            errors.append("acceptance report reviewed_member_hashes mismatch")
        reviewed_schema = report.get("reviewed_schema_hashes") or {}
        if reviewed_schema and reviewed_schema != (manifest.get("schema_hashes") or {}):
            errors.append("acceptance report reviewed_schema_hashes mismatch")

    def _validate_regression(self, set_id: str, set_type: str, regression: dict[str, Any], errors: list[str]) -> None:
        if regression.get("artifact_set_id") != set_id or regression.get("artifact_or_set_ref") != set_id:
            errors.append("regression artifact_set_id/subject mismatch")
        if regression.get("artifact_set_type") != set_type:
            errors.append("regression artifact_set_type mismatch")
        if not regression.get("baseline_ref"):
            errors.append("regression baseline_ref missing")
        if regression.get("candidate_ref") != set_id:
            errors.append("regression candidate_ref mismatch")
        for field, expected in (
            ("result", "PASS"),
            ("semantic_equality_result", "PASS"),
            ("consumer_compatibility_result", "PASS"),
            ("point_in_time_result", "PASS"),
        ):
            if regression.get(field) != expected:
                errors.append(f"regression {field} is not {expected}")
        if set_type == "CAPITAL_ALLOCATION_POLICY_SET":
            for field in ("planning_unchanged", "pending_unchanged", "submit_unchanged"):
                if regression.get(field) is not True:
                    errors.append(f"capital allocation regression {field} must be true")
        if set_type == "POSITION_MANAGEMENT_POLICY_SET" and regression.get("planning_unchanged") is not True:
            errors.append("position management regression planning_unchanged must be true")

    def _validate_generic_evidence(self, name: str, payload: dict[str, Any], set_id: str, set_type: str, warnings: list[str], errors: list[str], *, required_result: bool) -> None:
        subject = payload.get("artifact_set_id") or payload.get("subject_ref")
        if subject != set_id:
            warnings.append(f"{name} subject_ref is not standardized or mismatched")
        payload_type = payload.get("artifact_set_type")
        if payload_type not in {set_type, None}:
            errors.append(f"{name} artifact_set_type mismatch")
        if required_result and payload.get("result") != "PASS":
            errors.append(f"{name} result is not PASS")

    def _validate_freeze_manifest(self, freeze: dict[str, Any], manifest: dict[str, Any], set_id: str, set_type: str, warnings: list[str], errors: list[str]) -> None:
        self._validate_generic_evidence("freeze_manifest", freeze, set_id, set_type, warnings, errors, required_result=False)
        freeze_hashes = freeze.get("member_hashes") or freeze.get("hashes") or {}
        if freeze_hashes and freeze_hashes != (manifest.get("member_hashes") or {}):
            errors.append("freeze manifest member hash mismatch")
        if freeze.get("automatic_retraining") is True or freeze.get("scheduler_retraining") is True:
            errors.append("freeze manifest allows automatic retraining")

    def _validate_consumer_compatibility(self, compatibility: dict[str, Any], set_id: str, set_type: str, errors: list[str]) -> None:
        if compatibility.get("artifact_set_id") != set_id and compatibility.get("subject_ref") != set_id:
            errors.append("consumer compatibility subject mismatch")
        if compatibility.get("artifact_set_type") not in {set_type, None}:
            errors.append("consumer compatibility artifact_set_type mismatch")
        if compatibility.get("result") != "PASS" and compatibility.get("compatibility_result") != "PASS":
            errors.append("consumer compatibility result is not PASS")
        if not compatibility.get("consumer_id"):
            errors.append("consumer compatibility consumer_id missing")

    def _validate_rollback(self, report: dict[str, Any], bundle: dict[str, Any], rollback: dict[str, Any] | None, errors: list[str]) -> None:
        expected = report.get("rollback_target_ref")
        if expected != bundle.get("rollback_target_ref"):
            errors.append("rollback_target_ref mismatch between report and bundle")
        if expected and rollback is None:
            errors.append("rollback target is referenced but missing")

    def _validate_evidence_hashes(self, bundle: dict[str, Any], errors: list[str]) -> None:
        expected = bundle.get("evidence_hashes") or {}
        for path in self.paths.all_paths():
            key = evidence_key(path)
            if key not in expected:
                errors.append(f"bundle evidence hash missing for {key}")
                continue
            actual = sha256_file_bytes(path) if path.exists() else None
            if actual != expected.get(key):
                errors.append(f"bundle evidence hash mismatch for {key}")

    def _validate_duplicate_evidence(self, bundle: dict[str, Any], errors: list[str]) -> None:
        refs = [
            bundle.get("artifact_set_manifest_ref"),
            bundle.get("acceptance_report_ref"),
            bundle.get("regression_evidence_ref"),
            bundle.get("source_lineage_ref"),
            bundle.get("freeze_manifest_ref"),
            bundle.get("consumer_compatibility_ref"),
            bundle.get("rollback_target_ref"),
            *(item.get("approval_ref") for item in bundle.get("approval_refs") or []),
        ]
        values = [ref for ref in refs if ref]
        duplicates = sorted(ref for ref in set(values) if values.count(ref) > 1)
        if duplicates:
            errors.append("duplicate evidence refs: " + ",".join(duplicates))

    def _resolve(self, path: Path | str) -> Path:
        value = Path(path)
        return value if value.is_absolute() else self.repo_root / value


def bundle_hash_for(bundle: dict[str, Any]) -> str:
    return canonical_json_hash(bundle, exclude={"created_at", "evidence_bundle_id", "evidence_bundle_hash"})


def eligibility_candidate(overall: str) -> str:
    if overall == "PASS":
        return "ELIGIBLE_FOR_ACCEPTANCE_EVENT"
    if overall == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    return "NOT_ELIGIBLE"


def recommended_action(overall: str) -> str:
    if overall == "PASS":
        return "Evidence bundle can be used as candidate input for a future Acceptance Writer."
    if overall == "REVIEW_REQUIRED":
        return "Review warnings before using this bundle for acceptance."
    return "Fix HALT errors before acceptance."


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
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


def ensure_safe_output_root(output_root: Path, input_paths: tuple[Path, ...], *, repo_root: Path) -> Path:
    resolved_output = (repo_root / output_root).resolve() if not output_root.is_absolute() else output_root.resolve()
    runtime_root = (repo_root / ".runtime").resolve()
    formal_registry = (repo_root / FORMAL_REGISTRY_ROOT).resolve()
    if resolved_output == runtime_root or runtime_root in resolved_output.parents:
        raise AcceptanceOutputSafetyError("output under .runtime is prohibited")
    if resolved_output == formal_registry or formal_registry in resolved_output.parents:
        raise AcceptanceOutputSafetyError("output under formal Registry is prohibited")
    for path in input_paths:
        resolved_input = path.resolve()
        parent = resolved_input.parent
        if resolved_output == parent or parent in resolved_output.parents or resolved_output == resolved_input:
            raise AcceptanceOutputSafetyError("output under input evidence path is prohibited")
    return resolved_output


def write_outputs(result: dict[str, Any], output_root: Path, *, repo_root: Path, input_paths: tuple[Path, ...]) -> dict[str, Any]:
    safe_root = ensure_safe_output_root(output_root, input_paths, repo_root=repo_root)
    bundle = result["bundle"]
    validation = result["validation_result"]
    atomic_write_text(safe_root / "bundles" / f"{bundle['evidence_bundle_id']}.json", json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    atomic_write_text(safe_root / "validation_results" / f"{validation['validation_id']}.json", json.dumps(validation, indent=2, sort_keys=True) + "\n")
    summary = {
        "schema_version": "phase16ak_acceptance_evidence_summary.v1",
        "created_at": utc_now(),
        "artifact_set_id": validation["artifact_set_id"],
        "artifact_set_type": validation["artifact_set_type"],
        "overall_result": validation["overall_result"],
        "failure_class": validation["failure_class"],
        "eligibility_candidate_result": result["eligibility_candidate_result"],
        "bundle_hash": result["bundle_hash"],
        "bundle_path": str(safe_root / "bundles" / f"{bundle['evidence_bundle_id']}.json"),
        "validation_result_path": str(safe_root / "validation_results" / f"{validation['validation_id']}.json"),
    }
    atomic_write_text(safe_root / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    audit = render_audit(result, summary)
    atomic_write_text(safe_root / "audit.md", audit)
    return summary


def render_audit(result: dict[str, Any], summary: dict[str, Any]) -> str:
    validation = result["validation_result"]
    lines = [
        "# Artifact Acceptance Evidence Validation Audit",
        "",
        f"- builder_version: {result['builder_version']}",
        f"- artifact_set_id: {validation['artifact_set_id']}",
        f"- artifact_set_type: {validation['artifact_set_type']}",
        f"- overall_result: {validation['overall_result']}",
        f"- failure_class: {validation['failure_class']}",
        f"- eligibility_candidate_result: {result['eligibility_candidate_result']}",
        f"- bundle_hash: {result['bundle_hash']}",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in validation["errors"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in validation["warnings"])
    lines.extend(["", "## Output"])
    lines.append(f"- bundle_path: {summary['bundle_path']}")
    lines.append(f"- validation_result_path: {summary['validation_result_path']}")
    lines.append("")
    return "\n".join(lines)


def run_acceptance_evidence_validation(
    *,
    paths: AcceptanceEvidencePaths,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    builder = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=repo_root)
    bundle = builder.build_bundle()
    validator = AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=repo_root)
    result = validator.validate()
    summary = write_outputs(result, output_root, repo_root=repo_root, input_paths=paths.all_paths())
    return {"result": result, "summary": summary}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate Artifact Acceptance Evidence Bundle without Registry mutation.")
    parser.add_argument("--artifact-set-manifest", required=True)
    parser.add_argument("--acceptance-report", required=True)
    parser.add_argument("--regression-evidence", required=True)
    parser.add_argument("--approval", action="append", required=True)
    parser.add_argument("--source-lineage", required=True)
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument("--consumer-compatibility", required=True)
    parser.add_argument("--rollback-target")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args(argv)
    paths = AcceptanceEvidencePaths(
        artifact_set_manifest=Path(args.artifact_set_manifest),
        acceptance_report=Path(args.acceptance_report),
        regression_evidence=Path(args.regression_evidence),
        approvals=tuple(Path(item) for item in args.approval),
        source_lineage=Path(args.source_lineage),
        freeze_manifest=Path(args.freeze_manifest),
        consumer_compatibility=Path(args.consumer_compatibility),
        rollback_target=Path(args.rollback_target) if args.rollback_target else None,
    )
    try:
        output = run_acceptance_evidence_validation(paths=paths, output_root=Path(args.output), repo_root=Path.cwd())
    except AcceptanceOutputSafetyError as exc:
        print(json.dumps({"overall_result": "FAIL", "failure_class": "VALIDATION_ERROR", "error": str(exc)}, sort_keys=True))
        return 2
    validation = output["result"]["validation_result"]
    print(json.dumps({key: validation[key] for key in ("overall_result", "failure_class", "artifact_set_id", "artifact_set_type")}, sort_keys=True))
    return 0 if validation["overall_result"] in {"PASS", "REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
