import json
from pathlib import Path

from ai_fund_lab_v2.artifact_registry.inventory import sha256_file
from ai_fund_lab_v2.artifact_registry.validator import (
    load_schemas,
    validate_artifact_set_manifest,
    validate_phase16_inventory,
    validate_registry_event,
)


def _schemas() -> dict:
    return load_schemas(Path("docs/02_architecture/schemas"))


def _valid_event(tmp_path: Path) -> dict:
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"ok": true}\n', encoding="utf-8")
    digest = sha256_file(artifact)
    return {
        "event_id": "event-001",
        "event_type": "ARTIFACT_DISCOVERED",
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": "2026-07-13T00:00:00+00:00",
        "actor_type": "INVENTORY_TOOL",
        "actor_id": "test",
        "authority_ref": None,
        "logical_artifact_id": "ai.test.artifact",
        "artifact_instance_id": "ai.test.artifact@sha256-" + digest[:16],
        "artifact_type": "TEST_ARTIFACT",
        "component": "Test",
        "artifact_version": "v1",
        "previous_status": None,
        "new_status": "DRAFT",
        "runtime_use_eligible": False,
        "physical_path": str(artifact.relative_to(Path.cwd())) if artifact.is_relative_to(Path.cwd()) else str(artifact),
        "content_hash": digest,
        "schema_version": None,
        "schema_hash": None,
        "artifact_set_id": None,
        "business_date": None,
        "feature_date": None,
        "as_of": None,
        "producer": "test",
        "producer_version": None,
        "consumer_compatibility": [],
        "source_refs": [],
        "source_hashes": [],
        "point_in_time_status": "NOT_APPLICABLE",
        "retention_class": "test",
        "path_classification": "TEST",
        "migration_status": "DRAFT",
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _validate(event: dict, tmp_path: Path) -> dict:
    return validate_registry_event(event, schemas=_schemas(), repo_root=Path.cwd(), subject_ref="test-event")


def test_valid_draft_event_pass(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "PASS"
    assert result["failure_class"] == "NONE"


def test_missing_required_field_validation_error(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event.pop("event_id")
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "VALIDATION_ERROR"


def test_empty_hash_fail(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["content_hash"] = ""
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_invalid_sha256_fail(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["schema_hash"] = "not-a-hash"
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_draft_to_accepted_halt(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["previous_status"] = "DRAFT"
    event["new_status"] = "ACCEPTED"
    event["runtime_use_eligible"] = True
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_revoked_to_accepted_halt(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["previous_status"] = "REVOKED"
    event["new_status"] = "ACCEPTED"
    event["runtime_use_eligible"] = True
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_path_migrated_path_missing_fail(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["event_type"] = "PATH_MIGRATED"
    event["previous_status"] = "ACCEPTED"
    event["new_status"] = "ACCEPTED"
    event["previous_physical_path"] = None
    event["new_physical_path"] = "new/path"
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_path_migrated_same_path_fail(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["event_type"] = "PATH_MIGRATED"
    event["previous_status"] = "ACCEPTED"
    event["new_status"] = "ACCEPTED"
    event["previous_physical_path"] = "same/path"
    event["new_physical_path"] = "same/path"
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_opportunity_model_metrics_mismatch_halt() -> None:
    manifest = {
        "schema_version": "artifact_set_manifest.v1",
        "artifact_set_id": "opportunity-set",
        "artifact_set_type": "OPPORTUNITY_ACCEPTED_SET",
        "artifact_set_version": "v1",
        "component": "Opportunity AI",
        "member_artifacts": [
            {"logical_artifact_id": "ai.opportunity.model.accepted", "artifact_instance_id": "model@1", "artifact_type": "OPPORTUNITY_MODEL_ARTIFACT", "content_hash": None, "schema_hash": None, "role": "model"},
            {"logical_artifact_id": "ai.opportunity.metrics.legacy_phase5e", "artifact_instance_id": "phase5e_metrics@1", "artifact_type": "OPPORTUNITY_METRICS_ARTIFACT", "content_hash": None, "schema_hash": None, "role": "metrics"},
            {"logical_artifact_id": "ai.opportunity.feature_schema", "artifact_instance_id": "schema@1", "artifact_type": "FEATURE_SCHEMA", "content_hash": None, "schema_hash": None, "role": "feature_schema"},
            {"logical_artifact_id": "ai.opportunity.training_metadata", "artifact_instance_id": "training@1", "artifact_type": "TRAINING_ARTIFACT", "content_hash": None, "schema_hash": None, "role": "training_metadata"},
            {"logical_artifact_id": "ai.opportunity.validation_evidence", "artifact_instance_id": "validation@1", "artifact_type": "VALIDATION_ARTIFACT", "content_hash": None, "schema_hash": None, "role": "validation_evidence"},
        ],
        "required_member_types": [],
        "member_hashes": {},
        "schema_hashes": {},
        "compatibility_constraints": [],
        "training_period": None,
        "feature_schema_ref": "schema@1",
        "validation_evidence_refs": ["validation@1"],
        "runtime_consumer_refs": ["Opportunity AI"],
        "artifact_set_hash": "0" * 64,
        "status": "VALIDATED",
        "runtime_use_eligible": False,
    }
    result = validate_artifact_set_manifest(manifest, schemas=_schemas())
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_validated_runtime_use_eligible_true_fail(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["previous_status"] = "DRAFT"
    event["new_status"] = "VALIDATED"
    event["runtime_use_eligible"] = True
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_accepted_without_acceptance_report_halt(tmp_path: Path) -> None:
    event = _valid_event(tmp_path)
    event["previous_status"] = "VALIDATED"
    event["new_status"] = "ACCEPTED"
    event["runtime_use_eligible"] = True
    event["acceptance_report_ref"] = None
    event["review_ref"] = None
    event["regression_ref"] = None
    result = _validate(event, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"


def test_existing_input_files_unchanged(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    event_path = input_root / "draft_registry_events.jsonl"
    event_path.write_text(
        json.dumps(
            {
                "event_type": "DRAFT_REGISTER_ARTIFACT_CANDIDATE",
                "logical_artifact_id": "ai.test.artifact",
                "artifact_instance_id": "ai.test.artifact@sha256-" + "a" * 16,
                "artifact_type": "TEST_ARTIFACT",
                "component": "Test",
                "physical_path": "missing",
                "content_hash": "a" * 64,
                "schema_hash": None,
                "path_classification": "TEST",
                "migration_status": "DRAFT",
                "status": "DRAFT",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (input_root / "draft_registry_index.json").write_text(
        json.dumps({"index_type": "DRAFT_REGISTRY_INDEX", "accepted_event_count": 0, "entries": {}, "runtime_authority": {}}),
        encoding="utf-8",
    )
    before = event_path.read_bytes()
    validate_phase16_inventory(input_root, output_root, repo_root=Path.cwd())
    assert event_path.read_bytes() == before
