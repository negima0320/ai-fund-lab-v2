from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import bundle_hash_for, sha256_file_bytes
from ai_fund_lab_v2.artifact_registry.full_log_validator import FullEventLogValidator
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import load_schemas, read_json, validate_registry_event
from ai_fund_lab_v2.artifact_registry.writer import (
    EVENT_LOG_RELATIVE_PATH,
    LOCK_RELATIVE_PATH,
    _LockedFile,
    append_line_atomic,
    event_id_for_fingerprint,
    read_event_log,
)


ACCEPTANCE_WRITER_VERSION = "phase16al_authority_gated_acceptance_writer_v1"
FORMAL_REGISTRY_ROOT = Path(".runtime/artifact_registry")
FORMAL_SET_TYPES = {
    "CANDIDATE_AI_SET",
    "OPPORTUNITY_AI_SET",
    "POSITION_MANAGEMENT_POLICY_SET",
    "CAPITAL_ALLOCATION_POLICY_SET",
    "FEATURE_SCHEMA_SET",
    "SAFETY_POLICY_SET",
}
LEGACY_SET_TYPES = {"CANDIDATE_ACCEPTED_SET", "OPPORTUNITY_ACCEPTED_SET", "PM_ACCEPTED_SET"}
REQUIRED_APPROVAL_ROLES = {"HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL"}


class ArtifactAcceptanceWriterError(RuntimeError):
    pass


class AcceptanceGateError(ArtifactAcceptanceWriterError):
    pass


class FormalRegistryWriteRejected(ArtifactAcceptanceWriterError):
    pass


class AcceptanceDuplicateEventError(ArtifactAcceptanceWriterError):
    pass


@dataclass(frozen=True)
class AcceptanceWriterInputs:
    registry_root: Path
    evidence_bundle: Path
    validation_result: Path
    artifact_set_manifest: Path
    acceptance_report: Path
    regression_evidence: Path
    approvals: tuple[Path, ...]
    output_root: Path = Path("reports/phase16_acceptance_writer")
    rollback_target: Path | None = None
    allow_formal_registry_write: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def acceptance_event_fingerprint(event: dict[str, Any]) -> str:
    payload = {
        "event_type": event.get("event_type"),
        "logical_artifact_id": event.get("logical_artifact_id"),
        "artifact_instance_id": event.get("artifact_instance_id"),
        "artifact_set_id": event.get("artifact_set_id"),
        "artifact_set_type": event.get("artifact_set_type"),
        "new_status": event.get("new_status"),
        "runtime_use_eligible": event.get("runtime_use_eligible"),
        "content_hash": event.get("content_hash"),
        "schema_hash": event.get("schema_hash"),
        "authority_ref": event.get("authority_ref"),
        "acceptance_report_ref": event.get("acceptance_report_ref"),
        "evidence_bundle_ref": event.get("evidence_bundle_ref"),
        "regression_ref": event.get("regression_ref"),
        "consumer_compatibility_ref": event.get("consumer_compatibility_ref"),
    }
    return stable_json_hash(payload)


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


class ArtifactAcceptanceWriter:
    def __init__(self, *, inputs: AcceptanceWriterInputs, repo_root: Path | str | None = None, lock_timeout_seconds: float = 10.0) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.inputs = inputs
        self.registry_root = self._resolve(inputs.registry_root)
        self.event_log_path = self.registry_root / EVENT_LOG_RELATIVE_PATH
        self.lock_path = self.registry_root / LOCK_RELATIVE_PATH
        self.lock_timeout_seconds = lock_timeout_seconds
        self.schemas = load_schemas(self.repo_root / "docs/02_architecture/schemas")

    def append_acceptance(self, *, actor: str = "phase16al-acceptance-writer", reason: str = "Authority-gated Artifact Set acceptance") -> dict[str, Any]:
        self._reject_formal_registry_root()
        self._initialize_storage()
        before_hash = sha256_path(self.event_log_path)
        before_count = self._safe_event_count()
        operation_id = f"acceptance-operation-{uuid.uuid4()}"
        errors: list[str] = []
        warnings: list[str] = []
        event: dict[str, Any] | None = None
        fingerprint: str | None = None

        try:
            with _LockedFile(self.lock_path, timeout_seconds=self.lock_timeout_seconds):
                full_log = FullEventLogValidator(event_log_path=self.event_log_path, registry_root=self.registry_root, repo_root=self.repo_root).validate(include_events=True)
                if full_log.get("overall_result") != "PASS" or full_log.get("failure_class") != "NONE":
                    raise AcceptanceGateError("full event log validation did not PASS/NONE")

                docs = self._load_inputs()
                manifest = docs["manifest"]
                bundle = docs["bundle"]
                validation = docs["validation"]
                report = docs["report"]
                regression = docs["regression"]
                approvals = docs["approvals"]
                self._validate_gates(manifest, bundle, validation, report, regression, approvals)
                previous = self._current_lifecycle(full_log.get("events") or [], manifest)
                previous_status = previous.get("status")
                rollback = previous_status == "LEGACY"
                if previous_status != "VALIDATED" and not rollback:
                    raise AcceptanceGateError(f"previous_status must be VALIDATED for normal acceptance: {previous_status}")
                if rollback:
                    self._validate_rollback(report, regression, approvals, previous)

                event = self._build_event(manifest, bundle, report, regression, approvals, previous_status, actor=actor, reason=reason)
                fingerprint = acceptance_event_fingerprint(event)
                event["event_id"] = event.get("event_id") or event_id_for_fingerprint(fingerprint)
                self._validate_acceptance_event(event, manifest, bundle, report, regression, approvals)

                existing = read_event_log(self.event_log_path)
                if any(row["event"].get("event_id") == event["event_id"] for row in existing):
                    raise AcceptanceDuplicateEventError(f"duplicate event_id: {event['event_id']}")
                if any(acceptance_event_fingerprint(row["event"]) == fingerprint for row in existing if row["event"].get("event_type") == "ARTIFACT_ACCEPTED"):
                    raise AcceptanceDuplicateEventError(f"duplicate acceptance fingerprint: {fingerprint}")
                if self._has_active_eligible(existing, str(event["logical_artifact_id"]), str(event["artifact_instance_id"])):
                    raise AcceptanceGateError("DUPLICATE_ACTIVE_ELIGIBLE")

                line = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
                append_line_atomic(self.event_log_path, line)
        except Exception as exc:
            errors.append(str(exc))
            after_hash = sha256_path(self.event_log_path)
            after_count = self._safe_event_count(fallback=before_count)
            result = self._operation_result(
                operation_id=operation_id,
                event=event,
                fingerprint=fingerprint,
                before_hash=before_hash,
                after_hash=after_hash,
                before_count=before_count,
                after_count=after_count,
                appended=False,
                errors=errors,
                warnings=warnings,
            )
            self._write_report(result)
            raise

        after_hash = sha256_path(self.event_log_path)
        after_count = len(read_event_log(self.event_log_path))
        result = self._operation_result(
            operation_id=operation_id,
            event=event,
            fingerprint=fingerprint,
            before_hash=before_hash,
            after_hash=after_hash,
            before_count=before_count,
            after_count=after_count,
            appended=True,
            errors=errors,
            warnings=warnings,
        )
        self._write_report(result)
        return result

    def _resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else self.repo_root / path

    def _reject_formal_registry_root(self) -> None:
        if self.inputs.allow_formal_registry_write:
            return
        formal = (self.repo_root / FORMAL_REGISTRY_ROOT).resolve()
        root = self.registry_root.resolve()
        log = self.event_log_path.resolve()
        if root == formal or formal in root.parents or log == formal / EVENT_LOG_RELATIVE_PATH or formal in log.parents:
            raise FormalRegistryWriteRejected("formal Registry write is prohibited in Phase16-AL")

    def _initialize_storage(self) -> None:
        (self.registry_root / "events").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "locks").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "schema").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "checkpoints").mkdir(parents=True, exist_ok=True)
        self.event_log_path.touch(exist_ok=True)
        self.lock_path.touch(exist_ok=True)

    def _safe_event_count(self, fallback: int = 0) -> int:
        try:
            return len(read_event_log(self.event_log_path))
        except Exception:
            return fallback

    def _load_inputs(self) -> dict[str, Any]:
        validation_payload = read_json(self.inputs.validation_result)
        validation = validation_payload.get("validation_result") if validation_payload.get("validation_result") else validation_payload
        try:
            return {
                "bundle": read_json(self.inputs.evidence_bundle),
                "validation": validation,
                "validation_wrapper": validation_payload,
                "manifest": read_json(self.inputs.artifact_set_manifest),
                "report": read_json(self.inputs.acceptance_report),
                "regression": read_json(self.inputs.regression_evidence),
                "approvals": [read_json(path) for path in self.inputs.approvals],
            }
        except Exception as exc:
            raise AcceptanceGateError(f"acceptance input unreadable: {exc}") from exc

    def _validate_gates(
        self,
        manifest: dict[str, Any],
        bundle: dict[str, Any],
        validation: dict[str, Any],
        report: dict[str, Any],
        regression: dict[str, Any],
        approvals: list[dict[str, Any]],
    ) -> None:
        set_id = str(manifest.get("artifact_set_id") or "")
        set_type = str(manifest.get("artifact_set_type") or "")
        if set_type in LEGACY_SET_TYPES or set_type not in FORMAL_SET_TYPES:
            raise AcceptanceGateError(f"formal set type rejected: {set_type}")
        if manifest.get("set_authority_scope") != "SET_LEVEL":
            raise AcceptanceGateError("set_authority_scope must be SET_LEVEL")
        for payload, label in ((bundle, "bundle"), (validation, "validation"), (report, "report"), (regression, "regression")):
            if payload.get("artifact_set_id") != set_id:
                raise AcceptanceGateError(f"{label} artifact_set_id mismatch")
            if payload.get("artifact_set_type") != set_type:
                raise AcceptanceGateError(f"{label} artifact_set_type mismatch")
        if validation.get("overall_result") != "PASS" or validation.get("failure_class") != "NONE":
            raise AcceptanceGateError("validation result did not PASS/NONE")
        if validation.get("eligibility_result") not in {"PASS", "ELIGIBLE_FOR_ACCEPTANCE_EVENT"}:
            raise AcceptanceGateError("validation eligibility result is not acceptance eligible")
        if bundle_hash_for(bundle) != bundle.get("evidence_bundle_hash", bundle_hash_for(bundle)):
            raise AcceptanceGateError("evidence bundle hash mismatch")
        if report.get("decision") != "ACCEPT":
            raise AcceptanceGateError("Acceptance Report decision is not ACCEPT")
        if report.get("artifact_set_hash") != manifest.get("artifact_set_hash"):
            raise AcceptanceGateError("Artifact Set hash mismatch")
        if regression.get("result") != "PASS":
            raise AcceptanceGateError("Regression result is not PASS")
        for field in ("semantic_equality_result", "consumer_compatibility_result", "point_in_time_result"):
            if regression.get(field) != "PASS":
                raise AcceptanceGateError(f"Regression {field} is not PASS")
            report_field = "regression_result" if field == "semantic_equality_result" else field
            if report.get(report_field) != "PASS":
                raise AcceptanceGateError(f"Acceptance Report {report_field} is not PASS")
        roles = [str(item.get("approval_role") or item.get("approval_type") or "") for item in approvals]
        if set(roles) != REQUIRED_APPROVAL_ROLES or len(roles) != len(set(roles)):
            raise AcceptanceGateError("approval roles missing or duplicated")
        for approval in approvals:
            role = str(approval.get("approval_role") or approval.get("approval_type") or "")
            if approval.get("decision") != "APPROVED":
                raise AcceptanceGateError(f"approval {role} is not APPROVED")
            if approval.get("subject_type") != "ARTIFACT_SET" or approval.get("subject_ref") != set_id:
                raise AcceptanceGateError(f"approval {role} subject mismatch")
            if approval.get("artifact_set_type") != set_type:
                raise AcceptanceGateError(f"approval {role} artifact_set_type mismatch")
            if approval.get("reviewed_hash") != manifest.get("artifact_set_hash"):
                raise AcceptanceGateError(f"approval {role} reviewed_hash mismatch")
        member_hashes = manifest.get("member_hashes") or {}
        schema_hashes = manifest.get("schema_hashes") or {}
        for member in manifest.get("member_artifacts") or []:
            logical_id = member.get("logical_artifact_id")
            if member_hashes.get(logical_id) != member.get("content_hash"):
                raise AcceptanceGateError("member content hash mismatch")
            if schema_hashes.get(logical_id) != member.get("schema_hash"):
                raise AcceptanceGateError("member schema hash mismatch")
        for ref_field, expected_path in (
            ("artifact_set_manifest_ref", self.inputs.artifact_set_manifest),
            ("acceptance_report_ref", self.inputs.acceptance_report),
            ("regression_evidence_ref", self.inputs.regression_evidence),
        ):
            if bundle.get(ref_field) != str(expected_path):
                raise AcceptanceGateError(f"{ref_field} mismatch")

    def _current_lifecycle(self, events: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
        logical_id = str(manifest.get("artifact_set_id"))
        instance_id = f"{logical_id}@sha256-{str(manifest.get('artifact_set_hash'))[:16]}"
        current: dict[str, Any] = {}
        for event in events:
            if event.get("logical_artifact_id") == logical_id and event.get("artifact_instance_id") == instance_id:
                current = {
                    "status": event.get("new_status"),
                    "runtime_use_eligible": bool(event.get("runtime_use_eligible")),
                    "event": event,
                }
        if not current:
            raise AcceptanceGateError("target Artifact Set is not registered in Event Log")
        return current

    def _validate_rollback(self, report: dict[str, Any], regression: dict[str, Any], approvals: list[dict[str, Any]], previous: dict[str, Any]) -> None:
        previous_event = previous.get("event") or {}
        if not report.get("rollback_target_ref") or not regression.get("regression_evidence_id"):
            raise AcceptanceGateError("rollback acceptance requires rollback target and new regression")
        if report.get("acceptance_report_id") == previous_event.get("acceptance_report_ref"):
            raise AcceptanceGateError("rollback acceptance report must be new")
        if regression.get("regression_evidence_id") == previous_event.get("regression_ref"):
            raise AcceptanceGateError("rollback regression evidence must be new")
        if not approvals:
            raise AcceptanceGateError("rollback approval evidence must be new")

    def _build_event(
        self,
        manifest: dict[str, Any],
        bundle: dict[str, Any],
        report: dict[str, Any],
        regression: dict[str, Any],
        approvals: list[dict[str, Any]],
        previous_status: str,
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        set_id = str(manifest["artifact_set_id"])
        set_hash = str(manifest["artifact_set_hash"])
        schema_hash = stable_json_hash(manifest.get("schema_hashes") or {})
        approval_refs = [item["approval_ref"] for item in bundle.get("approval_refs") or []]
        source_refs = [str(bundle.get("source_lineage_ref")), *(manifest.get("validation_evidence_refs") or [])]
        source_hashes = [{"ref": str(path), "hash": sha256_file_bytes(Path(path))} for path in (self.inputs.artifact_set_manifest, self.inputs.acceptance_report, self.inputs.regression_evidence)]
        return {
            "event_id": None,
            "event_type": "ARTIFACT_ACCEPTED",
            "event_schema_version": "artifact_registry_event.v1",
            "event_created_at": utc_now(),
            "actor_type": "RELEASE_PROCESS",
            "actor_id": actor,
            "authority_ref": "Artifact Acceptance Authority",
            "logical_artifact_id": set_id,
            "artifact_instance_id": f"{set_id}@sha256-{set_hash[:16]}",
            "artifact_type": "ARTIFACT_SET",
            "component": str(manifest.get("component") or "Artifact Set"),
            "artifact_version": str(manifest.get("artifact_set_version") or "v1"),
            "previous_status": previous_status,
            "new_status": "ACCEPTED",
            "runtime_use_eligible": True,
            "physical_path": None,
            "content_hash": set_hash,
            "schema_version": str(manifest.get("schema_version") or "artifact_set_manifest.v1"),
            "schema_hash": schema_hash,
            "artifact_set_id": set_id,
            "artifact_set_type": manifest.get("artifact_set_type"),
            "business_date": None,
            "feature_date": None,
            "as_of": report.get("review_completed_at"),
            "producer": "ArtifactAcceptanceWriter",
            "producer_version": ACCEPTANCE_WRITER_VERSION,
            "consumer_compatibility": [{"consumer": "Runtime", "compatible": True, "reason": "Acceptance evidence validated"}],
            "source_refs": source_refs,
            "source_hashes": source_hashes,
            "point_in_time_status": "PASS",
            "retention_class": "ACCEPTANCE_AUDIT",
            "path_classification": "ARTIFACT_SET_MANIFEST",
            "migration_status": "ACCEPTED",
            "review_ref": str(self.inputs.approvals[0].parent),
            "regression_ref": str(self.inputs.regression_evidence),
            "acceptance_report_ref": str(self.inputs.acceptance_report),
            "evidence_bundle_ref": str(self.inputs.evidence_bundle),
            "consumer_compatibility_ref": str(bundle.get("consumer_compatibility_ref")),
            "reason": reason,
            "supersedes_event_id": None,
            "previous_physical_path": None,
            "new_physical_path": None,
            "replacement_operation_id": None,
            "replacement_from_ref": None,
            "replacement_to_ref": None,
            "replacement_stage": None,
            "rollback_operation_id": report.get("rollback_operation_id"),
            "rollback_target_ref": report.get("rollback_target_ref"),
            "new_acceptance_report_ref": str(self.inputs.acceptance_report) if previous_status == "LEGACY" else None,
            "new_regression_ref": str(self.inputs.regression_evidence) if previous_status == "LEGACY" else None,
            "new_approval_refs": approval_refs if previous_status == "LEGACY" else [],
            "revoke_reason": None,
            "affected_consumers": [],
            "replacement_ref": None,
            "runtime_fail_closed_required": None,
            "incident_ref": None,
        }

    def _validate_acceptance_event(
        self,
        event: dict[str, Any],
        manifest: dict[str, Any],
        bundle: dict[str, Any],
        report: dict[str, Any],
        regression: dict[str, Any],
        approvals: list[dict[str, Any]],
    ) -> None:
        result = validate_registry_event(event, schemas=self.schemas, repo_root=self.repo_root, subject_ref=event.get("event_id") or "acceptance_event")
        if result["overall_result"] != "PASS" or result["failure_class"] != "NONE":
            raise AcceptanceGateError("acceptance event schema/cross-field validation did not PASS: " + "; ".join(result["errors"]))
        if event.get("event_type") != "ARTIFACT_ACCEPTED" or event.get("new_status") != "ACCEPTED" or event.get("runtime_use_eligible") is not True:
            raise AcceptanceGateError("acceptance event status/eligibility mismatch")
        if event.get("artifact_set_type") not in FORMAL_SET_TYPES:
            raise AcceptanceGateError("acceptance event formal set type mismatch")
        if event.get("content_hash") != manifest.get("artifact_set_hash"):
            raise AcceptanceGateError("acceptance event content hash must equal Artifact Set hash")
        if not all(event.get(field) for field in ("authority_ref", "acceptance_report_ref", "evidence_bundle_ref", "regression_ref", "consumer_compatibility_ref")):
            raise AcceptanceGateError("acceptance event evidence refs incomplete")

    def _has_active_eligible(self, rows: list[dict[str, Any]], logical_id: str, instance_id: str) -> bool:
        active: str | None = None
        for row in rows:
            event = row["event"]
            if event.get("logical_artifact_id") != logical_id:
                continue
            if event.get("new_status") == "ACCEPTED" and event.get("runtime_use_eligible") is True:
                active = str(event.get("artifact_instance_id"))
            if event.get("new_status") in {"LEGACY", "REVOKED", "REJECTED"} and active == event.get("artifact_instance_id"):
                active = None
        return active is not None and active != instance_id

    def _operation_result(
        self,
        *,
        operation_id: str,
        event: dict[str, Any] | None,
        fingerprint: str | None,
        before_hash: str | None,
        after_hash: str | None,
        before_count: int,
        after_count: int,
        appended: bool,
        errors: list[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        return {
            "schema_version": "artifact_acceptance_operation_result.v1",
            "writer_version": ACCEPTANCE_WRITER_VERSION,
            "operation_id": operation_id,
            "operated_at": utc_now(),
            "artifact_set_id": event.get("artifact_set_id") if event else None,
            "artifact_set_type": event.get("artifact_set_type") if event else None,
            "event_id": event.get("event_id") if event else None,
            "event_fingerprint": fingerprint,
            "event_appended": appended,
            "event_log_path": str(self.event_log_path),
            "event_log_hash_before": before_hash,
            "event_log_hash_after": after_hash,
            "event_count_before": before_count,
            "event_count_after": after_count,
            "overall_result": "PASS" if appended else "FAIL",
            "failure_class": "NONE" if appended else "HALT",
            "acceptance_validation_ref": str(self.inputs.validation_result),
            "index_status": "STALE_EXPECTED" if appended else "NOT_UPDATED",
            "checkpoint_status": "STALE_EXPECTED" if appended else "NOT_UPDATED",
            "warnings": warnings,
            "errors": errors,
            "recommended_action": "Run Full Event Log Validation, Index Builder, and Checkpoint Writer." if appended else "Fix gate errors before retrying.",
            "replacement_workflow": "REPLACEMENT_WORKFLOW_NOT_IMPLEMENTED",
            "revoke_workflow": "REVOKE_WORKFLOW_NOT_IMPLEMENTED",
        }

    def _write_report(self, result: dict[str, Any]) -> None:
        root = self._resolve(self.inputs.output_root)
        atomic_write_text(root / "operation_result.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
        audit = [
            "# Artifact Acceptance Writer Operation",
            "",
            f"- operation_id: {result['operation_id']}",
            f"- overall_result: {result['overall_result']}",
            f"- failure_class: {result['failure_class']}",
            f"- event_appended: {result['event_appended']}",
            f"- event_id: {result['event_id']}",
            f"- event_fingerprint: {result['event_fingerprint']}",
            f"- event_log_path: {result['event_log_path']}",
            f"- index_status: {result['index_status']}",
            f"- checkpoint_status: {result['checkpoint_status']}",
            "",
            "## Errors",
            *[f"- {item}" for item in result["errors"]],
            "",
            "## Warnings",
            *[f"- {item}" for item in result["warnings"]],
            "",
        ]
        atomic_write_text(root / "audit.md", "\n".join(audit))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append an authority-gated ARTIFACT_ACCEPTED event to an isolated Registry root.")
    parser.add_argument("--registry-root", required=True)
    parser.add_argument("--evidence-bundle", required=True)
    parser.add_argument("--validation-result", required=True)
    parser.add_argument("--artifact-set-manifest", required=True)
    parser.add_argument("--acceptance-report", required=True)
    parser.add_argument("--regression-evidence", required=True)
    parser.add_argument("--approval", action="append", required=True)
    parser.add_argument("--output", default="reports/phase16_acceptance_writer")
    args = parser.parse_args(argv)
    inputs = AcceptanceWriterInputs(
        registry_root=Path(args.registry_root),
        evidence_bundle=Path(args.evidence_bundle),
        validation_result=Path(args.validation_result),
        artifact_set_manifest=Path(args.artifact_set_manifest),
        acceptance_report=Path(args.acceptance_report),
        regression_evidence=Path(args.regression_evidence),
        approvals=tuple(Path(item) for item in args.approval),
        output_root=Path(args.output),
    )
    try:
        result = ArtifactAcceptanceWriter(inputs=inputs, repo_root=Path.cwd()).append_acceptance()
    except FormalRegistryWriteRejected as exc:
        print(json.dumps({"overall_result": "FAIL", "failure_class": "HALT", "error": str(exc)}, sort_keys=True))
        return 2
    except ArtifactAcceptanceWriterError as exc:
        print(json.dumps({"overall_result": "FAIL", "failure_class": "HALT", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({key: result[key] for key in ("overall_result", "failure_class", "event_appended", "event_id")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
