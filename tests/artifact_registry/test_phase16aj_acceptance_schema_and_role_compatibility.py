import json
from pathlib import Path

from ai_fund_lab_v2.artifact_registry.validator import (
    artifact_set_hash,
    load_schemas,
    schema_validate,
    validate_artifact_set_manifest,
)


SCHEMA_ROOT = Path("docs/02_architecture/schemas")
CONTRACT_PATH = Path("docs/02_architecture/contracts/artifact_acceptance_role_compatibility.v1.json")
REQUIRED_ROLES = {"HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL"}


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _schemas() -> dict:
    return load_schemas(SCHEMA_ROOT)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _hash(seed: str) -> str:
    return (seed * 64)[:64]


def _member(role: str, *, set_id: str = "set-1") -> dict:
    return {
        "logical_artifact_id": f"artifact.{role.lower()}",
        "artifact_instance_id": f"artifact.{role.lower()}@sha256-{_hash('a')[:16]}",
        "artifact_type": role,
        "physical_path": f".runtime/artifacts/{role.lower()}.json",
        "content_hash": _hash("a"),
        "schema_hash": _hash("b"),
        "role": role,
        "member_role": role,
        "status": "VALIDATED",
        "runtime_use_eligible": False,
        "artifact_set_id": set_id,
    }


def _manifest(set_type: str, roles: list[str]) -> dict:
    members = [_member(role) for role in roles]
    manifest = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": "set-1",
        "artifact_set_type": set_type,
        "artifact_set_version": "v1",
        "set_authority_scope": "SET_LEVEL",
        "component": "Acceptance",
        "member_artifacts": members,
        "required_member_types": roles,
        "required_member_roles": roles,
        "member_hashes": {m["logical_artifact_id"]: m["content_hash"] for m in members},
        "schema_hashes": {m["logical_artifact_id"]: m["schema_hash"] for m in members},
        "compatibility_constraints": ["Runtime"],
        "training_period": None,
        "feature_schema_ref": "artifact.feature_schema@sha256-aaaaaaaaaaaaaaaa",
        "consumer_compatibility_ref": "compatibility/set-1.json",
        "source_lineage_ref": "lineage/set-1.json",
        "freeze_manifest_ref": "freeze/set-1.json",
        "validation_evidence_refs": ["validation/set-1.json"],
        "regression_evidence_refs": ["regression/set-1.json"],
        "runtime_consumer_refs": ["Runtime"],
        "artifact_set_hash": "",
        "status": "VALIDATED",
        "runtime_use_eligible": False,
    }
    manifest["artifact_set_hash"] = artifact_set_hash(manifest)
    return manifest


def _approval(role: str, subject: str = "set-1") -> dict:
    return {
        "role": role,
        "approval_ref": f"approvals/{role}.json",
        "approval_hash": _hash("c"),
        "subject_ref": subject,
        "reviewer_id": "operator-1",
        "decision": "APPROVED",
    }


def _bundle(roles: set[str] = REQUIRED_ROLES, subject: str = "set-1") -> dict:
    return {
        "schema_version": "artifact_acceptance_evidence_bundle.v1",
        "evidence_bundle_id": "bundle-1",
        "artifact_set_id": subject,
        "artifact_set_type": "CANDIDATE_AI_SET",
        "artifact_set_manifest_ref": "manifests/set-1.json",
        "acceptance_report_ref": "acceptance/report-1.json",
        "regression_evidence_ref": "regression/regression-1.json",
        "approval_refs": [_approval(role, subject=subject) for role in sorted(roles)],
        "source_lineage_ref": "manifests/lineage-1.json",
        "freeze_manifest_ref": "manifests/freeze-1.json",
        "consumer_compatibility_ref": "regression/compatibility-1.json",
        "rollback_target_ref": None,
        "evidence_hashes": {"manifest": _hash("d")},
        "created_at": "2026-07-13T00:00:00+00:00",
        "expires_at": None,
    }


def _assert_schema_pass(name: str, payload: dict) -> None:
    assert schema_validate(payload, _schema(name), field_path="$") == []


def _missing_roles(roles: set[str]) -> set[str]:
    return REQUIRED_ROLES - roles


def test_artifact_set_type_enum_and_required_member_matrix_are_fixed() -> None:
    contract = _contract()
    expected = {
        "CANDIDATE_AI_SET",
        "OPPORTUNITY_AI_SET",
        "POSITION_MANAGEMENT_POLICY_SET",
        "CAPITAL_ALLOCATION_POLICY_SET",
        "FEATURE_SCHEMA_SET",
        "SAFETY_POLICY_SET",
    }
    assert set(contract["artifact_set_types"]) == expected
    schema_enum = set(_schema("artifact_set_manifest.schema.json")["properties"]["artifact_set_type"]["enum"])
    assert expected.issubset(schema_enum)
    assert contract["artifact_set_types"]["OPPORTUNITY_AI_SET"]["required_member_roles"][:2] == ["MODEL", "METRICS"]


def test_role_compatibility_matrix_requires_four_roles_and_allows_same_reviewer() -> None:
    contract = _contract()
    for definition in contract["artifact_set_types"].values():
        assert set(definition["required_roles"]) == REQUIRED_ROLES
        assert definition["set_authority_scope"] == "SET_LEVEL"
    assert contract["same_reviewer_allowed"] is True
    assert contract["role_omission_allowed"] is False
    assert _missing_roles({"HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE"}) == {"RELEASE_APPROVAL"}


def test_valid_candidate_set_and_missing_member() -> None:
    roles = _contract()["artifact_set_types"]["CANDIDATE_AI_SET"]["required_member_roles"]
    manifest = _manifest("CANDIDATE_AI_SET", roles)
    _assert_schema_pass("artifact_set_manifest.schema.json", manifest)
    assert validate_artifact_set_manifest(manifest, schemas=_schemas())["overall_result"] == "PASS"

    missing = _manifest("CANDIDATE_AI_SET", [role for role in roles if role != "CONSUMER_COMPATIBILITY"])
    result = validate_artifact_set_manifest(missing, schemas=_schemas())
    assert result["failure_class"] == "HALT"


def test_valid_opportunity_set_metrics_required_and_same_set_rule() -> None:
    roles = _contract()["artifact_set_types"]["OPPORTUNITY_AI_SET"]["required_member_roles"]
    manifest = _manifest("OPPORTUNITY_AI_SET", roles)
    _assert_schema_pass("artifact_set_manifest.schema.json", manifest)
    assert validate_artifact_set_manifest(manifest, schemas=_schemas())["overall_result"] == "PASS"

    missing_metrics = _manifest("OPPORTUNITY_AI_SET", [role for role in roles if role != "METRICS"])
    assert validate_artifact_set_manifest(missing_metrics, schemas=_schemas())["failure_class"] == "HALT"

    split = _manifest("OPPORTUNITY_AI_SET", roles)
    for member in split["member_artifacts"]:
        if member["member_role"] == "METRICS":
            member["artifact_set_id"] = "other-set"
    split["artifact_set_hash"] = artifact_set_hash(split)
    assert validate_artifact_set_manifest(split, schemas=_schemas())["failure_class"] == "HALT"


def test_valid_pm_and_capital_sets_and_missing_adapter() -> None:
    pm_roles = _contract()["artifact_set_types"]["POSITION_MANAGEMENT_POLICY_SET"]["required_member_roles"]
    pm = _manifest("POSITION_MANAGEMENT_POLICY_SET", pm_roles)
    assert validate_artifact_set_manifest(pm, schemas=_schemas())["overall_result"] == "PASS"

    pm_missing_adapter = _manifest("POSITION_MANAGEMENT_POLICY_SET", [role for role in pm_roles if role != "RUNTIME_ADAPTER"])
    assert validate_artifact_set_manifest(pm_missing_adapter, schemas=_schemas())["failure_class"] == "HALT"

    capital_roles = _contract()["artifact_set_types"]["CAPITAL_ALLOCATION_POLICY_SET"]["required_member_roles"]
    capital = _manifest("CAPITAL_ALLOCATION_POLICY_SET", capital_roles)
    assert validate_artifact_set_manifest(capital, schemas=_schemas())["overall_result"] == "PASS"


def test_valid_feature_schema_set() -> None:
    roles = _contract()["artifact_set_types"]["FEATURE_SCHEMA_SET"]["required_member_roles"]
    manifest = _manifest("FEATURE_SCHEMA_SET", roles)
    _assert_schema_pass("artifact_set_manifest.schema.json", manifest)
    assert validate_artifact_set_manifest(manifest, schemas=_schemas())["overall_result"] == "PASS"


def test_evidence_bundle_four_roles_and_role_omission() -> None:
    bundle = _bundle()
    _assert_schema_pass("artifact_acceptance_evidence_bundle.schema.json", bundle)
    roles = {item["role"] for item in bundle["approval_refs"] if item["decision"] == "APPROVED"}
    assert _missing_roles(roles) == set()

    missing_release = _bundle(REQUIRED_ROLES - {"RELEASE_APPROVAL"})
    assert schema_validate(missing_release, _schema("artifact_acceptance_evidence_bundle.schema.json"), field_path="$")
    roles = {item["role"] for item in missing_release["approval_refs"] if item["decision"] == "APPROVED"}
    assert _missing_roles(roles) == {"RELEASE_APPROVAL"}


def test_acceptance_report_approval_and_regression_schema_amendment_fields() -> None:
    report = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "acceptance-1",
        "artifact_or_set_ref": "set-1",
        "artifact_set_id": "set-1",
        "artifact_set_type": "CANDIDATE_AI_SET",
        "artifact_set_manifest_ref": "manifests/set-1.json",
        "artifact_set_hash": _hash("e"),
        "reviewed_artifact_hashes": {"model": _hash("a")},
        "reviewed_member_hashes": {"MODEL": _hash("a")},
        "reviewed_schema_hashes": {"MODEL": _hash("b")},
        "reviewed_source_refs": [],
        "evidence_bundle_ref": "bundles/bundle-1.json",
        "human_reviewer": "operator-1",
        "architecture_reviewer": "operator-1",
        "regression_reviewer": "operator-1",
        "release_approver": "operator-1",
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
    _assert_schema_pass("artifact_acceptance_report.schema.json", report)

    approval = {
        "schema_version": "artifact_review_approval.v1",
        "approval_id": "approval-1",
        "approval_type": "HUMAN_REVIEW",
        "approval_role": "HUMAN_REVIEW",
        "subject_type": "ARTIFACT_SET",
        "subject_ref": "set-1",
        "artifact_set_type": "CANDIDATE_AI_SET",
        "reviewer_id": "operator-1",
        "reviewer_role": "operator",
        "reviewed_hash": _hash("e"),
        "decision": "APPROVED",
        "approved_at": "2026-07-13T00:00:00+00:00",
        "evidence_refs": ["bundles/bundle-1.json"],
        "conditions": [],
        "expires_at": None,
        "supersedes_approval_id": None,
    }
    _assert_schema_pass("artifact_review_approval.schema.json", approval)

    regression = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": "regression-1",
        "artifact_or_set_ref": "set-1",
        "artifact_set_id": "set-1",
        "artifact_set_type": "CANDIDATE_AI_SET",
        "profile": "CANDIDATE",
        "test_scope": "semantic",
        "test_command": None,
        "test_environment": "test",
        "before_refs": [],
        "after_refs": [],
        "baseline_ref": "baseline",
        "candidate_ref": "candidate",
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
        "evidence_hash": _hash("f"),
        "failures": [],
        "timestamp_only_differences": [],
        "reviewer": "operator-1",
    }
    _assert_schema_pass("artifact_regression_evidence.schema.json", regression)


def test_acceptance_event_replacement_rollback_and_revoke_fields_exist() -> None:
    props = _schema("artifact_registry_event.schema.json")["properties"]
    for field in (
        "artifact_set_type",
        "evidence_bundle_ref",
        "consumer_compatibility_ref",
        "replacement_operation_id",
        "replacement_from_ref",
        "replacement_to_ref",
        "replacement_stage",
        "rollback_operation_id",
        "rollback_target_ref",
        "new_acceptance_report_ref",
        "new_regression_ref",
        "new_approval_refs",
        "revoke_reason",
        "affected_consumers",
        "replacement_ref",
        "runtime_fail_closed_required",
        "incident_ref",
    ):
        assert field in props
    assert "ARTIFACT_ACCEPTED" in props["event_type"]["enum"]
    assert "NEW_ELIGIBLE" in props["replacement_stage"]["enum"]


def test_runtime_eligibility_preconditions_and_cross_field_rules_are_machine_readable() -> None:
    contract = _contract()
    preconditions = set(contract["runtime_eligibility_preconditions"])
    assert "Evidence Bundle complete" in preconditions
    assert "four approval roles present" in preconditions
    assert "Regression PASS" in preconditions
    assert "not REVOKED" in preconditions
    rules = set(contract["cross_field_rules"])
    assert "opportunity_model_metrics_same_set" in rules
    assert "replacement_stage_ordering" in rules
    assert "rollback_requires_new_evidence" in rules
    assert "revoked_instance_cannot_be_accepted" in rules


def test_acceptance_validation_result_schema_exists() -> None:
    result = {
        "schema_version": "artifact_acceptance_validation_result.v1",
        "validation_id": "validation-1",
        "validated_at": "2026-07-13T00:00:00+00:00",
        "artifact_set_id": "set-1",
        "artifact_set_type": "CANDIDATE_AI_SET",
        "set_validation_result": "PASS",
        "member_validation_results": {"MODEL": "PASS"},
        "role_validation_result": "PASS",
        "regression_validation_result": "PASS",
        "compatibility_validation_result": "PASS",
        "point_in_time_validation_result": "PASS",
        "eligibility_result": "PASS",
        "overall_result": "PASS",
        "failure_class": "NONE",
        "errors": [],
        "warnings": [],
    }
    _assert_schema_pass("artifact_acceptance_validation_result.schema.json", result)
