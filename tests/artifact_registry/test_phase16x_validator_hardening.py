from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.inventory import sha256_file
from ai_fund_lab_v2.artifact_registry.validator import (
    ValidationSafetyError,
    artifact_set_hash,
    load_schemas,
    schema_validate,
    validate_artifact_set_manifest,
    validate_phase16_inventory,
    validate_registry_event,
)


def _schemas() -> dict:
    return load_schemas(Path("docs/02_architecture/schemas"))


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _minimal_inventory_input(root: Path) -> Path:
    root.mkdir()
    (root / "draft_registry_events.jsonl").write_text("", encoding="utf-8")
    return root


def test_output_root_guard_rejects_same_input_output(tmp_path: Path) -> None:
    input_root = _minimal_inventory_input(tmp_path / "input")
    with pytest.raises(ValidationSafetyError):
        validate_phase16_inventory(input_root, input_root, repo_root=Path.cwd())


def test_output_root_guard_rejects_output_under_input(tmp_path: Path) -> None:
    input_root = _minimal_inventory_input(tmp_path / "input")
    with pytest.raises(ValidationSafetyError):
        validate_phase16_inventory(input_root, input_root / "out", repo_root=Path.cwd())


def test_output_root_guard_rejects_runtime_paths() -> None:
    input_root = Path("reports/phase16_registry_inventory")
    for output in (Path(".runtime"), Path(".runtime/artifact_registry"), Path(".runtime/artifacts")):
        with pytest.raises(ValidationSafetyError):
            validate_phase16_inventory(input_root, output, repo_root=Path.cwd())


def test_output_root_guard_rejects_symlink_to_runtime(tmp_path: Path) -> None:
    input_root = _minimal_inventory_input(tmp_path / "input")
    link = tmp_path / "runtime-link"
    link.symlink_to(Path.cwd() / ".runtime", target_is_directory=True)
    with pytest.raises(ValidationSafetyError):
        validate_phase16_inventory(input_root, link / "validation", repo_root=Path.cwd())


def test_output_root_guard_allows_reports_output(tmp_path: Path) -> None:
    input_root = _minimal_inventory_input(tmp_path / "input")
    summary = validate_phase16_inventory(input_root, tmp_path / "reports" / "validation", repo_root=Path.cwd())
    assert summary["protected_hash_result"] == "UNCHANGED"


def _accepted_event(tmp_path: Path) -> dict:
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"accepted": true}\n', encoding="utf-8")
    digest = sha256_file(artifact)
    schema_hash = "b" * 64
    subject = "accepted-artifact@sha256-" + digest[:16]
    return {
        "event_id": "event-accepted",
        "event_type": "ARTIFACT_ACCEPTED",
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": "2026-07-13T00:00:00+00:00",
        "actor_type": "HUMAN",
        "actor_id": "reviewer",
        "authority_ref": "acceptance-authority",
        "logical_artifact_id": "ai.test.accepted",
        "artifact_instance_id": subject,
        "artifact_type": "CANDIDATE_MODEL_ARTIFACT",
        "component": "Candidate AI",
        "artifact_version": "v1",
        "previous_status": "VALIDATED",
        "new_status": "ACCEPTED",
        "runtime_use_eligible": True,
        "physical_path": str(artifact),
        "content_hash": digest,
        "schema_version": "test.schema.v1",
        "schema_hash": schema_hash,
        "artifact_set_id": None,
        "business_date": None,
        "feature_date": None,
        "as_of": None,
        "producer": "test",
        "producer_version": "v1",
        "consumer_compatibility": [{"consumer": "Runtime", "compatible": True, "reason": None}],
        "source_refs": [],
        "source_hashes": [],
        "point_in_time_status": "PASS",
        "retention_class": "model",
        "path_classification": "TEMPORARY_REGISTERED_PATH",
        "migration_status": "VALIDATED",
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _write_evidence(tmp_path: Path, event: dict, *, report_updates: dict | None = None, regression_updates: dict | None = None, approvals: list[dict] | None = None) -> dict:
    subject = event["artifact_instance_id"]
    report = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "report-1",
        "artifact_or_set_ref": subject,
        "reviewed_artifact_hashes": {subject: event["content_hash"]},
        "reviewed_schema_hashes": {subject: event["schema_hash"]},
        "reviewed_source_refs": [],
        "human_reviewer": "human",
        "architecture_reviewer": "arch",
        "regression_reviewer": "reg",
        "release_approver": "release",
        "review_started_at": "2026-07-13T00:00:00+00:00",
        "review_completed_at": "2026-07-13T01:00:00+00:00",
        "decision": "ACCEPT",
        "acceptance_criteria_results": {"identity": "PASS"},
        "regression_results": ["PASS"],
        "known_limitations": [],
        "risk_classification": "LOW",
        "rollback_target": None,
        "replacement_target": None,
        "git_commit": None,
        "runtime_version": None,
        "feature_schema_version": None,
        "canonical_data_manifest_ref": None,
        "model_freeze_manifest_ref": None,
        "approval_signatures": ["sig"],
        "notes": None,
    }
    report.update(report_updates or {})
    regression = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": "regression-1",
        "artifact_or_set_ref": subject,
        "profile": "CANDIDATE",
        "test_scope": "unit",
        "test_command": None,
        "test_environment": "test",
        "before_refs": [],
        "after_refs": [],
        "semantic_comparison": "PASS",
        "hash_comparison": "PASS",
        "schema_comparison": "PASS",
        "candidate_decision_parity": "PASS",
        "opportunity_decision_parity": "NOT_APPLICABLE",
        "pm_decision_parity": "NOT_APPLICABLE",
        "capital_allocation_parity": "NOT_APPLICABLE",
        "planning_parity": "PASS",
        "pending_parity": "PASS",
        "submit_guard_parity": "PASS",
        "current_unchanged": True,
        "ledger_unchanged": True,
        "pending_unchanged": True,
        "runtime_state_unchanged": True,
        "result": "PASS",
        "failures": [],
        "timestamp_only_differences": [],
        "reviewer": "reg",
    }
    regression.update(regression_updates or {})
    approval_list = approvals
    if approval_list is None:
        approval_list = [
            {
                "schema_version": "artifact_review_approval.v1",
                "approval_id": f"approval-{approval_type}",
                "approval_type": approval_type,
                "subject_ref": subject,
                "reviewer_id": approval_type.lower(),
                "reviewer_role": approval_type,
                "decision": "APPROVED",
                "approved_at": "2026-07-13T02:00:00+00:00",
                "evidence_refs": ["report-1"],
                "conditions": [],
                "expires_at": None,
                "supersedes_approval_id": None,
            }
            for approval_type in ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")
        ]
    report_path = _write_json(tmp_path / "report.json", report)
    regression_path = _write_json(tmp_path / "regression.json", regression)
    approvals_path = _write_json(tmp_path / "approvals.json", approval_list)
    event["acceptance_report_ref"] = str(report_path)
    event["regression_ref"] = str(regression_path)
    event["review_ref"] = str(approvals_path)
    return event


def _validate_event(event: dict) -> dict:
    return validate_registry_event(event, schemas=_schemas(), repo_root=Path.cwd(), subject_ref="accepted-event")


def test_valid_accepted_evidence_passes(tmp_path: Path) -> None:
    result = _validate_event(_write_evidence(tmp_path, _accepted_event(tmp_path)))
    assert result["overall_result"] == "PASS"


@pytest.mark.parametrize(
    "updates",
    [
        {"report_updates": {"decision": "REJECT"}},
        {"report_updates": {"artifact_or_set_ref": "wrong-subject"}},
        {"report_updates": {"reviewed_artifact_hashes": {"x": "0" * 64}}},
        {"regression_updates": {"result": "FAIL", "failures": ["parity"]}},
    ],
)
def test_invalid_accepted_evidence_halts(tmp_path: Path, updates: dict) -> None:
    event = _write_evidence(tmp_path, _accepted_event(tmp_path), **updates)
    result = _validate_event(event)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_required_approval_role_missing_halts(tmp_path: Path) -> None:
    event = _accepted_event(tmp_path)
    approvals = [
        {
            "schema_version": "artifact_review_approval.v1",
            "approval_id": "approval-human",
            "approval_type": "HUMAN_REVIEW",
            "subject_ref": event["artifact_instance_id"],
            "reviewer_id": "human",
            "reviewer_role": "human",
            "decision": "APPROVED",
            "approved_at": "2026-07-13T02:00:00+00:00",
            "evidence_refs": ["report-1"],
            "conditions": [],
            "expires_at": None,
            "supersedes_approval_id": None,
        }
    ]
    result = _validate_event(_write_evidence(tmp_path, event, approvals=approvals))
    assert result["failure_class"] == "HALT"


def test_approval_subject_mismatch_halts(tmp_path: Path) -> None:
    event = _accepted_event(tmp_path)
    event = _write_evidence(tmp_path, event)
    approvals = json.loads(Path(event["review_ref"]).read_text(encoding="utf-8"))
    approvals[0]["subject_ref"] = "wrong"
    Path(event["review_ref"]).write_text(json.dumps(approvals), encoding="utf-8")
    result = _validate_event(event)
    assert result["failure_class"] == "HALT"


def test_evidence_path_missing_halts(tmp_path: Path) -> None:
    event = _write_evidence(tmp_path, _accepted_event(tmp_path))
    event["acceptance_report_ref"] = str(tmp_path / "missing.json")
    result = _validate_event(event)
    assert result["failure_class"] == "HALT"


def _member(role: str) -> dict:
    return {
        "logical_artifact_id": f"artifact.{role}",
        "artifact_instance_id": f"artifact.{role}@1",
        "artifact_type": role.upper(),
        "content_hash": "a" * 64,
        "schema_hash": "b" * 64,
        "role": role,
    }


def _manifest(set_type: str, roles: list[str]) -> dict:
    members = [_member(role) for role in roles]
    manifest = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": f"{set_type.lower()}-1",
        "artifact_set_type": set_type,
        "artifact_set_version": "v1",
        "component": "Test",
        "member_artifacts": members,
        "required_member_types": roles,
        "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
        "schema_hashes": {m["logical_artifact_id"]: m["schema_hash"] for m in members},
        "compatibility_constraints": ["Runtime"],
        "training_period": None,
        "feature_schema_ref": "artifact.feature_schema@1",
        "validation_evidence_refs": ["artifact.validation_evidence@1"],
        "runtime_consumer_refs": ["Runtime"],
        "artifact_set_hash": "",
        "status": "ACCEPTED",
        "runtime_use_eligible": True,
    }
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    return manifest


def _assert_manifest_passes(manifest: dict) -> None:
    result = validate_artifact_set_manifest(manifest, schemas=_schemas())
    assert result["overall_result"] == "PASS"


def test_valid_candidate_opportunity_pm_and_capital_sets_pass() -> None:
    _assert_manifest_passes(_manifest("CANDIDATE_ACCEPTED_SET", ["model", "manifest", "feature_schema", "training_metadata", "validation_evidence"]))
    _assert_manifest_passes(_manifest("OPPORTUNITY_ACCEPTED_SET", ["model", "metrics", "feature_schema", "training_metadata", "validation_evidence"]))
    _assert_manifest_passes(_manifest("PM_ACCEPTED_SET", ["code_policy", "runtime_adapter", "policy_version", "feature_version", "code_hash", "adapter_hash"]))
    _assert_manifest_passes(_manifest("CAPITAL_ALLOCATION_POLICY_SET", ["policy_artifact", "policy_schema", "policy_version", "policy_hash", "validation_evidence", "consumer_compatibility"]))


def test_candidate_member_missing_and_duplicate_halt() -> None:
    missing = _manifest("CANDIDATE_ACCEPTED_SET", ["model", "manifest", "feature_schema", "training_metadata"])
    assert validate_artifact_set_manifest(missing, schemas=_schemas())["failure_class"] == "HALT"
    duplicate = _manifest("CANDIDATE_ACCEPTED_SET", ["model", "manifest", "feature_schema", "training_metadata", "validation_evidence"])
    duplicate["member_artifacts"].append(dict(duplicate["member_artifacts"][0]))
    duplicate["artifact_set_hash"] = artifact_set_hash(duplicate)
    assert validate_artifact_set_manifest(duplicate, schemas=_schemas())["failure_class"] == "HALT"


def test_opportunity_metrics_membership_mismatch_halts_without_phase5e_string() -> None:
    manifest = _manifest("OPPORTUNITY_ACCEPTED_SET", ["model", "metrics", "feature_schema", "training_metadata", "validation_evidence"])
    metrics_id = "artifact.metrics"
    manifest["member_hashes"][metrics_id] = "c" * 64
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    result = validate_artifact_set_manifest(manifest, schemas=_schemas())
    assert result["failure_class"] == "HALT"


def test_pm_adapter_missing_halts() -> None:
    manifest = _manifest("PM_ACCEPTED_SET", ["code_policy", "policy_version", "feature_version", "code_hash", "adapter_hash"])
    assert validate_artifact_set_manifest(manifest, schemas=_schemas())["failure_class"] == "HALT"


def test_capital_policy_hash_and_set_hash_mismatch_halt() -> None:
    manifest = _manifest("CAPITAL_ALLOCATION_POLICY_SET", ["policy_artifact", "policy_schema", "policy_version", "policy_hash", "validation_evidence", "consumer_compatibility"])
    manifest["member_hashes"]["artifact.policy_hash"] = "c" * 64
    assert validate_artifact_set_manifest(manifest, schemas=_schemas())["failure_class"] == "HALT"
    manifest = _manifest("CAPITAL_ALLOCATION_POLICY_SET", ["policy_artifact", "policy_schema", "policy_version", "policy_hash", "validation_evidence", "consumer_compatibility"])
    manifest["artifact_set_hash"] = "0" * 64
    assert validate_artifact_set_manifest(manifest, schemas=_schemas())["failure_class"] == "HALT"


def test_consumer_incompatibility_review_required() -> None:
    manifest = _manifest("CANDIDATE_ACCEPTED_SET", ["model", "manifest", "feature_schema", "training_metadata", "validation_evidence"])
    manifest["runtime_consumer_refs"] = []
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    result = validate_artifact_set_manifest(manifest, schemas=_schemas())
    assert result["overall_result"] == "REVIEW_REQUIRED"


def test_runtime_required_model_missing_halts_and_optional_evidence_missing_review_required(tmp_path: Path) -> None:
    event = _accepted_event(tmp_path)
    event["physical_path"] = str(tmp_path / "missing-model.pkl")
    result = _validate_event(_write_evidence(tmp_path, event))
    assert result["failure_class"] == "HALT"

    optional = _accepted_event(tmp_path)
    optional["new_status"] = "VALIDATED"
    optional["previous_status"] = "DRAFT"
    optional["runtime_use_eligible"] = False
    optional["artifact_type"] = "VALIDATION_EVIDENCE"
    optional["retention_class"] = "validation_evidence"
    optional["consumer_compatibility"] = []
    optional["physical_path"] = str(tmp_path / "missing-evidence.json")
    optional["acceptance_report_ref"] = None
    optional["review_ref"] = None
    optional["regression_ref"] = None
    result = _validate_event(optional)
    assert result["overall_result"] == "REVIEW_REQUIRED"


def test_schema_checker_rejects_invalid_datetime_and_bad_map_value() -> None:
    schemas = _schemas()
    report_schema = schemas["artifact_acceptance_report.schema.json"]
    report = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "report",
        "artifact_or_set_ref": "subject",
        "reviewed_artifact_hashes": {"subject": 123},
        "reviewed_schema_hashes": {"subject": None},
        "reviewed_source_refs": [],
        "human_reviewer": "h",
        "architecture_reviewer": "a",
        "regression_reviewer": "r",
        "release_approver": "l",
        "review_started_at": "not-a-date",
        "review_completed_at": "2026-07-13T01:00:00+00:00",
        "decision": "ACCEPT",
        "acceptance_criteria_results": {"identity": "PASS"},
        "regression_results": [],
        "known_limitations": [],
        "risk_classification": "LOW",
        "rollback_target": None,
        "replacement_target": None,
        "git_commit": None,
        "runtime_version": None,
        "feature_schema_version": None,
        "canonical_data_manifest_ref": None,
        "model_freeze_manifest_ref": None,
        "approval_signatures": [],
        "notes": None,
    }
    issues = schema_validate(report, report_schema, field_path="$")
    assert any(issue["check_type"] == "schema_format" for issue in issues)
    assert any(issue["field_path"] == "$.reviewed_artifact_hashes.subject" for issue in issues)
