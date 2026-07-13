from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import (
    AcceptanceEvidenceBundleBuilder,
    AcceptanceEvidenceBundleValidator,
    AcceptanceEvidencePaths,
    AcceptanceOutputSafetyError,
    bundle_hash_for,
    ensure_safe_output_root,
    run_acceptance_evidence_validation,
    sha256_file_bytes,
)
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import artifact_set_hash


REQUIRED_ROLES = ["HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL"]
SET_ROLES = {
    "CANDIDATE_AI_SET": ["MODEL", "MODEL_MANIFEST", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "METRICS_EVIDENCE", "CONSUMER_COMPATIBILITY"],
    "OPPORTUNITY_AI_SET": ["MODEL", "METRICS", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "CONSUMER_COMPATIBILITY"],
    "POSITION_MANAGEMENT_POLICY_SET": ["CODE_POLICY", "RUNTIME_ADAPTER", "POLICY_VERSION", "FEATURE_VERSION", "BEHAVIOR_CONTRACT", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"],
    "CAPITAL_ALLOCATION_POLICY_SET": ["POLICY", "POLICY_SCHEMA", "POLICY_VERSION", "VALIDATION_EVIDENCE", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"],
    "FEATURE_SCHEMA_SET": ["FEATURE_SCHEMA", "POINT_IN_TIME_EVIDENCE", "CONSUMER_COMPATIBILITY", "SCHEMA_VALIDATION_EVIDENCE"],
}


def _h(seed: str) -> str:
    return stable_json_hash({"seed": seed})


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _member(role: str, set_id: str) -> dict:
    return {
        "logical_artifact_id": f"artifact.{role.lower()}",
        "artifact_instance_id": f"artifact.{role.lower()}@sha256-{_h(role)[:16]}",
        "artifact_set_id": set_id,
        "artifact_type": role,
        "physical_path": f"artifacts/{role.lower()}.json",
        "content_hash": _h(f"{role}-content"),
        "schema_hash": _h(f"{role}-schema"),
        "role": role,
        "member_role": role,
        "status": "VALIDATED",
        "runtime_use_eligible": False,
        "source_refs": ["lineage-1"],
    }


def _manifest(set_type: str, *, set_id: str = "set-1", roles: list[str] | None = None) -> dict:
    roles = roles or SET_ROLES[set_type]
    members = [_member(role, set_id) for role in roles]
    manifest = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": set_id,
        "artifact_set_type": set_type,
        "artifact_set_version": "v1",
        "set_authority_scope": "SET_LEVEL",
        "component": "Acceptance Test",
        "member_artifacts": members,
        "required_member_types": roles,
        "required_member_roles": roles,
        "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
        "schema_hashes": {m["logical_artifact_id"]: m["schema_hash"] for m in members},
        "compatibility_constraints": ["Runtime"],
        "training_period": None,
        "feature_schema_ref": "artifact.feature_schema",
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


def _approval(role: str, manifest: dict, *, subject: str | None = None, decision: str = "APPROVED", expires_at=None) -> dict:
    return {
        "schema_version": "artifact_review_approval.v1",
        "approval_id": f"approval-{role}",
        "approval_type": role,
        "approval_role": role,
        "subject_type": "ARTIFACT_SET",
        "subject_ref": subject or manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "reviewer_id": "same-reviewer",
        "reviewer_role": "operator",
        "reviewed_hash": manifest["artifact_set_hash"],
        "decision": decision,
        "approved_at": "2026-07-13T00:00:00+00:00",
        "evidence_refs": ["acceptance.json"],
        "conditions": [],
        "expires_at": expires_at,
        "supersedes_approval_id": None,
    }


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
        "reviewer": "same-reviewer",
    }
    payload.update(overrides)
    return payload


def _report(manifest: dict, **overrides) -> dict:
    payload = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "acceptance-1",
        "artifact_or_set_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "artifact_set_manifest_ref": "manifest.json",
        "artifact_set_hash": manifest["artifact_set_hash"],
        "reviewed_artifact_hashes": manifest["member_hashes"],
        "reviewed_member_hashes": manifest["member_hashes"],
        "reviewed_schema_hashes": manifest["schema_hashes"],
        "reviewed_source_refs": [],
        "evidence_bundle_ref": None,
        "human_reviewer": "same-reviewer",
        "architecture_reviewer": "same-reviewer",
        "regression_reviewer": "same-reviewer",
        "release_approver": "same-reviewer",
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


def _generic(manifest: dict, *, result="PASS") -> dict:
    return {
        "subject_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "member_hashes": manifest["member_hashes"],
        "hashes": manifest["member_hashes"],
        "consumer_id": "Runtime",
        "consumer_version": "v1",
        "expected_member_roles": manifest["required_member_roles"],
        "result": result,
        "compatibility_result": result,
        "automatic_retraining": False,
        "scheduler_retraining": False,
    }


def _fixture(tmp_path: Path, set_type="CANDIDATE_AI_SET", mutate=None) -> AcceptanceEvidencePaths:
    root = tmp_path / "input"
    manifest = _manifest(set_type)
    if mutate:
        mutate(manifest)
        manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    manifest_path = _write(root / "manifest.json", manifest)
    report_path = _write(root / "acceptance.json", _report(manifest, artifact_set_manifest_ref=str(manifest_path)))
    regression_path = _write(root / "regression.json", _regression(manifest))
    approval_paths = tuple(_write(root / f"approval_{role}.json", _approval(role, manifest)) for role in REQUIRED_ROLES)
    source_path = _write(root / "source.json", _generic(manifest))
    freeze_path = _write(root / "freeze.json", _generic(manifest))
    consumer_path = _write(root / "consumer.json", _generic(manifest))
    return AcceptanceEvidencePaths(
        artifact_set_manifest=manifest_path,
        acceptance_report=report_path,
        regression_evidence=regression_path,
        approvals=approval_paths,
        source_lineage=source_path,
        freeze_manifest=freeze_path,
        consumer_compatibility=consumer_path,
    )


def _validate(paths: AcceptanceEvidencePaths):
    bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=Path.cwd()).build_bundle()
    return AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=Path.cwd()).validate()


@pytest.mark.parametrize("set_type", list(SET_ROLES))
def test_valid_bundle_for_each_set_type(tmp_path: Path, set_type: str) -> None:
    paths = _fixture(tmp_path, set_type=set_type)
    result = _validate(paths)
    assert result["validation_result"]["overall_result"] == "PASS"
    assert result["eligibility_candidate_result"] == "ELIGIBLE_FOR_ACCEPTANCE_EVENT"


def test_member_validation_failures(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, mutate=lambda m: m["member_artifacts"].pop())
    result = _validate(paths)
    assert result["validation_result"]["failure_class"] == "HALT"
    assert any("missing required member" in item for item in result["validation_result"]["errors"])

    paths = _fixture(tmp_path / "dup", mutate=lambda m: m["member_artifacts"].append(dict(m["member_artifacts"][0])))
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"

    def wrong_set(manifest):
        manifest["member_artifacts"][0]["artifact_set_id"] = "other"

    assert _validate(_fixture(tmp_path / "wrong-set", mutate=wrong_set))["validation_result"]["failure_class"] == "HALT"

    def hash_mismatch(manifest):
        key = manifest["member_artifacts"][0]["logical_artifact_id"]
        manifest["member_hashes"][key] = _h("different")

    assert _validate(_fixture(tmp_path / "hash", mutate=hash_mismatch))["validation_result"]["failure_class"] == "HALT"

    def schema_mismatch(manifest):
        key = manifest["member_artifacts"][0]["logical_artifact_id"]
        manifest["schema_hashes"][key] = _h("different")

    assert _validate(_fixture(tmp_path / "schema", mutate=schema_mismatch))["validation_result"]["failure_class"] == "HALT"


def test_same_set_constraints(tmp_path: Path) -> None:
    def opportunity_split(manifest):
        for member in manifest["member_artifacts"]:
            if member["member_role"] == "METRICS":
                member["artifact_set_id"] = "other"

    assert _validate(_fixture(tmp_path, set_type="OPPORTUNITY_AI_SET", mutate=opportunity_split))["validation_result"]["failure_class"] == "HALT"

    def pm_split(manifest):
        for member in manifest["member_artifacts"]:
            if member["member_role"] == "RUNTIME_ADAPTER":
                member["artifact_set_id"] = "other"

    assert _validate(_fixture(tmp_path / "pm", set_type="POSITION_MANAGEMENT_POLICY_SET", mutate=pm_split))["validation_result"]["failure_class"] == "HALT"

    def cap_split(manifest):
        for member in manifest["member_artifacts"]:
            if member["member_role"] == "POLICY_SCHEMA":
                member["artifact_set_id"] = "other"

    assert _validate(_fixture(tmp_path / "cap", set_type="CAPITAL_ALLOCATION_POLICY_SET", mutate=cap_split))["validation_result"]["failure_class"] == "HALT"


def test_approval_failures_and_same_reviewer_allowed(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    assert _validate(paths)["validation_result"]["overall_result"] == "PASS"

    missing = AcceptanceEvidencePaths(**{**paths.__dict__, "approvals": paths.approvals[:-1]})
    assert _validate(missing)["validation_result"]["failure_class"] == "HALT"

    dup = AcceptanceEvidencePaths(**{**paths.__dict__, "approvals": paths.approvals[:3] + (paths.approvals[0],)})
    assert _validate(dup)["validation_result"]["failure_class"] == "HALT"

    approval = json.loads(paths.approvals[0].read_text())
    approval["subject_ref"] = "other"
    _write(paths.approvals[0], approval)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"

    approval["subject_ref"] = "set-1"
    approval["artifact_set_type"] = "OPPORTUNITY_AI_SET"
    _write(paths.approvals[0], approval)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"

    approval["artifact_set_type"] = "CANDIDATE_AI_SET"
    approval["decision"] = "REJECTED"
    _write(paths.approvals[0], approval)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"

    approval["decision"] = "APPROVED"
    approval["expires_at"] = "2020-01-01T00:00:00+00:00"
    _write(paths.approvals[0], approval)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"


def test_acceptance_report_failures(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    report = json.loads(paths.acceptance_report.read_text())
    for field, value in [
        ("decision", "REJECT"),
        ("artifact_set_hash", _h("wrong")),
        ("regression_result", "FAIL"),
        ("consumer_compatibility_result", "FAIL"),
        ("point_in_time_result", "HALT"),
    ]:
        changed = dict(report)
        changed[field] = value
        _write(paths.acceptance_report, changed)
        assert _validate(paths)["validation_result"]["failure_class"] == "HALT"
    changed = dict(report)
    changed["reviewed_member_hashes"] = {"MODEL": _h("wrong")}
    _write(paths.acceptance_report, changed)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"


def test_regression_failures(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    regression = json.loads(paths.regression_evidence.read_text())
    for field, value in [
        ("result", "FAIL"),
        ("semantic_equality_result", "FAIL"),
        ("consumer_compatibility_result", "FAIL"),
        ("point_in_time_result", "HALT"),
        ("candidate_ref", "other"),
        ("artifact_set_id", "other"),
    ]:
        changed = dict(regression)
        changed[field] = value
        _write(paths.regression_evidence, changed)
        assert _validate(paths)["validation_result"]["failure_class"] == "HALT"


def test_evidence_bundle_hash_and_evidence_hash_failures(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=Path.cwd()).build_bundle()
    assert bundle_hash_for(bundle) == bundle_hash_for(AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=Path.cwd()).build_bundle())

    result = AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=Path.cwd()).validate()
    assert result["validation_result"]["overall_result"] == "PASS"

    bundle["evidence_hashes"][paths.acceptance_report.name] = _h("wrong")
    assert AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=Path.cwd()).validate()["validation_result"]["failure_class"] == "HALT"

    bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=Path.cwd()).build_bundle()
    bundle["acceptance_report_ref"] = bundle["artifact_set_manifest_ref"]
    assert AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=Path.cwd()).validate()["validation_result"]["failure_class"] == "HALT"


def test_source_freeze_consumer_and_rollback_validation(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    source = json.loads(paths.source_lineage.read_text())
    source.pop("artifact_set_id")
    source.pop("subject_ref")
    _write(paths.source_lineage, source)
    assert _validate(paths)["validation_result"]["overall_result"] == "REVIEW_REQUIRED"

    paths = _fixture(tmp_path / "freeze")
    freeze = json.loads(paths.freeze_manifest.read_text())
    freeze["automatic_retraining"] = True
    _write(paths.freeze_manifest, freeze)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"

    paths = _fixture(tmp_path / "consumer")
    consumer = json.loads(paths.consumer_compatibility.read_text())
    consumer["result"] = "FAIL"
    consumer["compatibility_result"] = "FAIL"
    _write(paths.consumer_compatibility, consumer)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"

    paths = _fixture(tmp_path / "rollback")
    report = json.loads(paths.acceptance_report.read_text())
    report["rollback_target_ref"] = "rollback.json"
    _write(paths.acceptance_report, report)
    assert _validate(paths)["validation_result"]["failure_class"] == "HALT"


def test_output_safety_and_normal_reports_output(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    with pytest.raises(AcceptanceOutputSafetyError):
        ensure_safe_output_root(paths.artifact_set_manifest.parent, paths.all_paths(), repo_root=Path.cwd())
    with pytest.raises(AcceptanceOutputSafetyError):
        ensure_safe_output_root(paths.artifact_set_manifest.parent / "child", paths.all_paths(), repo_root=Path.cwd())
    with pytest.raises(AcceptanceOutputSafetyError):
        ensure_safe_output_root(Path(".runtime"), paths.all_paths(), repo_root=Path.cwd())
    runtime_link = tmp_path / "runtime-link"
    runtime_link.symlink_to(Path.cwd() / ".runtime")
    with pytest.raises(AcceptanceOutputSafetyError):
        ensure_safe_output_root(runtime_link, paths.all_paths(), repo_root=Path.cwd())

    output = tmp_path / "reports" / "phase16_acceptance_evidence"
    result = run_acceptance_evidence_validation(paths=paths, output_root=output, repo_root=Path.cwd())
    assert result["summary"]["overall_result"] == "PASS"
    assert (output / "summary.json").exists()
    assert (output / "audit.md").exists()


def test_inputs_and_formal_registry_unchanged(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    input_hashes_before = {path: sha256_file_bytes(path) for path in paths.all_paths()}
    event_log = Path(".runtime/artifact_registry/events/registry_events.jsonl")
    index = Path(".runtime/artifact_registry/index/registry_index.json")
    checkpoint = Path(".runtime/artifact_registry/checkpoints/latest.json")
    protected_before = {path: sha256_file_bytes(path) for path in (event_log, index, checkpoint)}
    run_acceptance_evidence_validation(paths=paths, output_root=tmp_path / "reports", repo_root=Path.cwd())
    assert {path: sha256_file_bytes(path) for path in paths.all_paths()} == input_hashes_before
    assert {path: sha256_file_bytes(path) for path in (event_log, index, checkpoint)} == protected_before
