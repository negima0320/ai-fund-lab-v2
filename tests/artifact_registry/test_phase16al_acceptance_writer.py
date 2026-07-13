from __future__ import annotations

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import (
    AcceptanceEvidenceBundleBuilder,
    AcceptanceEvidenceBundleValidator,
    AcceptanceEvidencePaths,
)
from ai_fund_lab_v2.artifact_registry.acceptance_writer import (
    AcceptanceGateError,
    AcceptanceWriterInputs,
    ArtifactAcceptanceWriter,
    FormalRegistryWriteRejected,
    acceptance_event_fingerprint,
)
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import artifact_set_hash, validate_registry_event
from ai_fund_lab_v2.artifact_registry.writer import event_fingerprint, read_event_log


ROLES = ["MODEL", "MODEL_MANIFEST", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "METRICS_EVIDENCE", "CONSUMER_COMPATIBILITY"]
APPROVAL_ROLES = ["HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL"]


def _h(seed: str) -> str:
    return stable_json_hash({"seed": seed})


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _manifest(set_id: str = "candidate.set") -> dict:
    members = [
        {
            "logical_artifact_id": f"{set_id}.{role.lower()}",
            "artifact_instance_id": f"{set_id}.{role.lower()}@sha256-{_h(role)[:16]}",
            "artifact_set_id": set_id,
            "artifact_type": role,
            "physical_path": None,
            "content_hash": _h(f"{role}-content"),
            "schema_hash": _h(f"{role}-schema"),
            "role": role,
            "member_role": role,
            "status": "VALIDATED",
            "runtime_use_eligible": False,
            "source_refs": ["lineage-1"],
        }
        for role in ROLES
    ]
    manifest = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": set_id,
        "artifact_set_type": "CANDIDATE_AI_SET",
        "artifact_set_version": "v1",
        "set_authority_scope": "SET_LEVEL",
        "component": "Acceptance Writer Test",
        "member_artifacts": members,
        "required_member_types": ROLES,
        "required_member_roles": ROLES,
        "member_hashes": {item["logical_artifact_id"]: item["content_hash"] for item in members},
        "schema_hashes": {item["logical_artifact_id"]: item["schema_hash"] for item in members},
        "compatibility_constraints": ["Runtime"],
        "training_period": None,
        "feature_schema_ref": f"{set_id}.feature_schema",
        "consumer_compatibility_ref": "consumer.json",
        "source_lineage_ref": "source.json",
        "freeze_manifest_ref": "freeze.json",
        "validation_evidence_refs": ["validation.json"],
        "regression_evidence_refs": ["regression.json"],
        "runtime_consumer_refs": ["Runtime"],
        "artifact_set_hash": "",
        "status": "VALIDATED",
        "runtime_use_eligible": False,
    }
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    return manifest


def _approval(role: str, manifest: dict, **overrides) -> dict:
    payload = {
        "schema_version": "artifact_review_approval.v1",
        "approval_id": f"approval-{role}",
        "approval_type": role,
        "approval_role": role,
        "subject_type": "ARTIFACT_SET",
        "subject_ref": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "reviewer_id": "reviewer",
        "reviewer_role": "release",
        "reviewed_hash": manifest["artifact_set_hash"],
        "decision": "APPROVED",
        "approved_at": "2026-07-13T00:00:00+00:00",
        "evidence_refs": ["acceptance.json"],
        "conditions": [],
        "expires_at": None,
        "supersedes_approval_id": None,
    }
    payload.update(overrides)
    return payload


def _regression(manifest: dict, **overrides) -> dict:
    payload = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": "regression-1",
        "artifact_or_set_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "profile": "CANDIDATE",
        "test_scope": "semantic",
        "test_command": None,
        "test_environment": "tmp",
        "before_refs": [],
        "after_refs": [],
        "baseline_ref": "baseline",
        "candidate_ref": manifest["artifact_set_id"],
        "semantic_comparison": "PASS",
        "semantic_equality_result": "PASS",
        "hash_comparison": "PASS",
        "schema_comparison": "PASS",
        "candidate_decision_parity": "PASS",
        "opportunity_decision_parity": "NOT_APPLICABLE",
        "pm_decision_parity": "NOT_APPLICABLE",
        "capital_allocation_parity": "NOT_APPLICABLE",
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
        "reviewer": "reviewer",
    }
    payload.update(overrides)
    return payload


def _report(manifest: dict, manifest_path: Path, **overrides) -> dict:
    payload = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "acceptance-1",
        "artifact_or_set_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "artifact_set_manifest_ref": str(manifest_path),
        "artifact_set_hash": manifest["artifact_set_hash"],
        "reviewed_artifact_hashes": manifest["member_hashes"],
        "reviewed_member_hashes": manifest["member_hashes"],
        "reviewed_schema_hashes": manifest["schema_hashes"],
        "reviewed_source_refs": [],
        "evidence_bundle_ref": None,
        "human_reviewer": "reviewer",
        "architecture_reviewer": "reviewer",
        "regression_reviewer": "reviewer",
        "release_approver": "reviewer",
        "review_started_at": "2026-07-13T00:00:00+00:00",
        "review_completed_at": "2026-07-13T00:01:00+00:00",
        "decision": "ACCEPT",
        "acceptance_criteria_results": {},
        "regression_results": [],
        "regression_result": "PASS",
        "consumer_compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "known_limitations": [],
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
        "notes": None,
    }
    payload.update(overrides)
    return payload


def _generic(manifest: dict) -> dict:
    return {
        "subject_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "member_hashes": manifest["member_hashes"],
        "hashes": manifest["member_hashes"],
        "consumer_id": "Runtime",
        "consumer_version": "v1",
        "expected_member_roles": manifest["required_member_roles"],
        "result": "PASS",
        "compatibility_result": "PASS",
        "automatic_retraining": False,
        "scheduler_retraining": False,
    }


def _lifecycle_event(manifest: dict, status: str, previous: str | None) -> dict:
    set_id = manifest["artifact_set_id"]
    digest = manifest["artifact_set_hash"]
    return {
        "event_id": f"event-{status.lower()}-{digest[:16]}",
        "event_type": "ARTIFACT_DISCOVERED" if status == "DRAFT" else ("ARTIFACT_VALIDATED" if status == "VALIDATED" else f"ARTIFACT_{status}"),
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": datetime(2026, 7, 13, tzinfo=timezone.utc).isoformat(),
        "actor_type": "VALIDATION_TOOL",
        "actor_id": "test",
        "authority_ref": "test-authority",
        "logical_artifact_id": set_id,
        "artifact_instance_id": f"{set_id}@sha256-{digest[:16]}",
        "artifact_type": "ARTIFACT_SET",
        "component": manifest["component"],
        "artifact_version": "v1",
        "previous_status": previous,
        "new_status": status,
        "runtime_use_eligible": status == "ACCEPTED",
        "physical_path": None,
        "content_hash": digest,
        "schema_version": manifest["schema_version"],
        "schema_hash": stable_json_hash(manifest["schema_hashes"]),
        "artifact_set_id": set_id,
        "artifact_set_type": manifest["artifact_set_type"],
        "business_date": None,
        "feature_date": None,
        "as_of": None,
        "producer": "test",
        "producer_version": "v1",
        "consumer_compatibility": [],
        "source_refs": [],
        "source_hashes": [],
        "point_in_time_status": "NOT_APPLICABLE" if status != "ACCEPTED" else "PASS",
        "retention_class": "test",
        "path_classification": "TEST",
        "migration_status": status,
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _fixture(tmp_path: Path, *, previous_status: str = "VALIDATED", mutate=None) -> tuple[AcceptanceWriterInputs, dict]:
    root = tmp_path / "input"
    manifest = _manifest()
    if mutate:
        mutate(manifest)
        manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    manifest_path = _write(root / "manifest.json", manifest)
    report_path = _write(root / "acceptance.json", _report(manifest, manifest_path))
    regression_path = _write(root / "regression.json", _regression(manifest))
    approvals_dir = root / "approvals"
    approval_paths = tuple(_write(approvals_dir / f"{role}.json", _approval(role, manifest)) for role in APPROVAL_ROLES)
    source_path = _write(root / "source.json", _generic(manifest))
    freeze_path = _write(root / "freeze.json", _generic(manifest))
    consumer_path = _write(root / "consumer.json", _generic(manifest))
    paths = AcceptanceEvidencePaths(
        artifact_set_manifest=manifest_path,
        acceptance_report=report_path,
        regression_evidence=regression_path,
        approvals=approval_paths,
        source_lineage=source_path,
        freeze_manifest=freeze_path,
        consumer_compatibility=consumer_path,
    )
    bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=Path.cwd()).build_bundle()
    validation = AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=Path.cwd()).validate()
    bundle_path = _write(root / "bundle.json", bundle)
    validation_path = _write(root / "validation_result.json", validation["validation_result"])
    registry = tmp_path / "registry"
    event_log = registry / "events" / "registry_events.jsonl"
    event_log.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if previous_status in {"DRAFT", "VALIDATED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED", "REVIEW_REQUIRED"}:
        lines.append(_lifecycle_event(manifest, "DRAFT", None))
    if previous_status in {"VALIDATED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}:
        lines.append(_lifecycle_event(manifest, "VALIDATED", "DRAFT"))
    if previous_status in {"ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}:
        accepted = _lifecycle_event(manifest, "ACCEPTED", "VALIDATED")
        accepted.update({"review_ref": str(approvals_dir), "regression_ref": str(regression_path), "acceptance_report_ref": str(report_path), "point_in_time_status": "PASS"})
        lines.append(accepted)
    if previous_status == "LEGACY":
        lines.append(_lifecycle_event(manifest, "LEGACY", "ACCEPTED"))
    if previous_status == "REVOKED":
        lines.append(_lifecycle_event(manifest, "REVOKED", "ACCEPTED"))
    if previous_status == "REJECTED":
        lines.append(_lifecycle_event(manifest, "REJECTED", "ACCEPTED"))
    event_log.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in lines), encoding="utf-8")
    inputs = AcceptanceWriterInputs(
        registry_root=registry,
        evidence_bundle=bundle_path,
        validation_result=validation_path,
        artifact_set_manifest=manifest_path,
        acceptance_report=report_path,
        regression_evidence=regression_path,
        approvals=approval_paths,
        output_root=tmp_path / "out",
    )
    return inputs, manifest


def _writer(inputs: AcceptanceWriterInputs) -> ArtifactAcceptanceWriter:
    return ArtifactAcceptanceWriter(inputs=inputs, repo_root=Path.cwd(), lock_timeout_seconds=0.01)


def test_valid_acceptance_appends_set_level_runtime_eligible_event(tmp_path: Path) -> None:
    inputs, manifest = _fixture(tmp_path)
    result = _writer(inputs).append_acceptance()
    rows = read_event_log(inputs.registry_root / "events/registry_events.jsonl")
    event = rows[-1]["event"]
    assert result["event_appended"] is True
    assert event["event_type"] == "ARTIFACT_ACCEPTED"
    assert event["logical_artifact_id"] == manifest["artifact_set_id"]
    assert event["content_hash"] == manifest["artifact_set_hash"]
    assert event["runtime_use_eligible"] is True
    assert acceptance_event_fingerprint(event) == result["event_fingerprint"]
    assert validate_registry_event(event, schemas=_writer(inputs).schemas, repo_root=Path.cwd())["overall_result"] == "PASS"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update({"overall_result": "REVIEW_REQUIRED"}),
        lambda v: v.update({"overall_result": "FAIL"}),
        lambda v: v.update({"failure_class": "HALT"}),
        lambda v: v.update({"eligibility_result": "HALT"}),
        lambda v: v.update({"artifact_set_id": "other"}),
    ],
)
def test_validation_result_gate_rejects_non_eligible(tmp_path: Path, mutation) -> None:
    inputs, _ = _fixture(tmp_path)
    payload = json.loads(inputs.validation_result.read_text())
    mutation(payload)
    inputs.validation_result.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(AcceptanceGateError):
        _writer(inputs).append_acceptance()


@pytest.mark.parametrize(
    "edit",
    [
        lambda root: (root / "approvals/HUMAN_REVIEW.json").unlink(),
        lambda root: _write(root / "approvals/HUMAN_REVIEW.json", {**json.loads((root / "approvals/HUMAN_REVIEW.json").read_text()), "decision": "REJECTED"}),
        lambda root: _write(root / "approvals/HUMAN_REVIEW.json", {**json.loads((root / "approvals/HUMAN_REVIEW.json").read_text()), "subject_ref": "other"}),
        lambda root: _write(root / "acceptance.json", {**json.loads((root / "acceptance.json").read_text()), "decision": "REJECT"}),
        lambda root: _write(root / "regression.json", {**json.loads((root / "regression.json").read_text()), "result": "FAIL"}),
        lambda root: _write(root / "regression.json", {**json.loads((root / "regression.json").read_text()), "semantic_equality_result": "FAIL"}),
        lambda root: _write(root / "regression.json", {**json.loads((root / "regression.json").read_text()), "consumer_compatibility_result": "FAIL"}),
        lambda root: _write(root / "regression.json", {**json.loads((root / "regression.json").read_text()), "point_in_time_result": "HALT"}),
    ],
)
def test_authority_gate_rejects_invalid_evidence(tmp_path: Path, edit) -> None:
    inputs, _ = _fixture(tmp_path)
    edit(inputs.artifact_set_manifest.parent)
    with pytest.raises(AcceptanceGateError):
        _writer(inputs).append_acceptance()


@pytest.mark.parametrize("previous", ["DRAFT", "REVIEW_REQUIRED", "REJECTED", "REVOKED", "ACCEPTED"])
def test_lifecycle_gate_rejects_non_validated_sources(tmp_path: Path, previous: str) -> None:
    inputs, _ = _fixture(tmp_path, previous_status=previous)
    with pytest.raises(AcceptanceGateError):
        _writer(inputs).append_acceptance()


def test_unregistered_set_rejected(tmp_path: Path) -> None:
    inputs, _ = _fixture(tmp_path, previous_status="NONE")
    with pytest.raises(AcceptanceGateError):
        _writer(inputs).append_acceptance()


def test_duplicate_acceptance_fingerprint_rejected(tmp_path: Path) -> None:
    inputs, _ = _fixture(tmp_path)
    writer = _writer(inputs)
    writer.append_acceptance()
    with pytest.raises(AcceptanceGateError):
        writer.append_acceptance()


def test_formal_registry_root_rejected_and_unchanged() -> None:
    event_log = Path(".runtime/artifact_registry/events/registry_events.jsonl")
    before = event_log.read_text(encoding="utf-8")
    inputs = AcceptanceWriterInputs(
        registry_root=Path(".runtime/artifact_registry"),
        evidence_bundle=Path("missing"),
        validation_result=Path("missing"),
        artifact_set_manifest=Path("missing"),
        acceptance_report=Path("missing"),
        regression_evidence=Path("missing"),
        approvals=(),
    )
    with pytest.raises(FormalRegistryWriteRejected):
        ArtifactAcceptanceWriter(inputs=inputs, repo_root=Path.cwd()).append_acceptance()
    assert event_log.read_text(encoding="utf-8") == before


def test_corrupt_and_partial_event_log_rejected(tmp_path: Path) -> None:
    inputs, _ = _fixture(tmp_path)
    event_log = inputs.registry_root / "events/registry_events.jsonl"
    event_log.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(AcceptanceGateError):
        _writer(inputs).append_acceptance()
    event_log.write_bytes(b'{"partial": true}')
    with pytest.raises(AcceptanceGateError):
        _writer(inputs).append_acceptance()


def test_lock_contention_rejects_and_releases(tmp_path: Path) -> None:
    inputs, _ = _fixture(tmp_path)
    lock = inputs.registry_root / "locks/registry.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    with lock.open("a+b") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(Exception):
                _writer(inputs).append_acceptance()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    _writer(inputs).append_acceptance()


def test_existing_writer_fingerprint_unchanged_for_non_acceptance(tmp_path: Path) -> None:
    event = {"event_type": "ARTIFACT_VALIDATED", "logical_artifact_id": "x", "artifact_instance_id": "x@1", "new_status": "VALIDATED", "content_hash": "a", "schema_hash": "b", "authority_ref": "c", "acceptance_report_ref": None}
    assert event_fingerprint(event) == event_fingerprint({**event, "artifact_set_type": "CANDIDATE_AI_SET", "evidence_bundle_ref": "different"})
