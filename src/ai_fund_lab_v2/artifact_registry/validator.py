from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.inventory import directory_inventory, sha256_file, stable_json_hash


VALIDATOR_VERSION = "phase16v_minimal_read_only_validator_v1"
VALIDATION_SCHEMA_VERSION = "artifact_validation_result.v1"
SHA256_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}$")
SENTINEL_HASH_VALUES = {"", "UNKNOWN", "NOT_APPLICABLE", "NOT_FOUND"}
REQUIRED_APPROVAL_TYPES = {"HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL"}
SUCCESS_REGRESSION_VALUES = {"PASS", "NOT_APPLICABLE", None}

ALLOWED_TRANSITIONS = {
    (None, "DRAFT"),
    ("DRAFT", "VALIDATED"),
    ("DRAFT", "REVIEW_REQUIRED"),
    ("VALIDATED", "REVIEW_REQUIRED"),
    ("VALIDATED", "ACCEPTED"),
    ("VALIDATED", "REVOKED"),
    ("REVIEW_REQUIRED", "VALIDATED"),
    ("ACCEPTED", "LEGACY"),
    ("ACCEPTED", "REVOKED"),
    ("LEGACY", "ACCEPTED"),
    ("LEGACY", "REVOKED"),
}
PROHIBITED_TRANSITIONS = {
    ("DRAFT", "ACCEPTED"),
    ("REVIEW_REQUIRED", "ACCEPTED"),
    ("REVOKED", "ACCEPTED"),
    ("REVOKED", "VALIDATED"),
}


class ValidationSafetyError(ValueError):
    pass


def validate_phase16_inventory(input_root: Path, output_root: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    ensure_safe_output_root(input_root, output_root, repo_root=repo_root)
    output_root.mkdir(parents=True, exist_ok=True)
    results_dir = output_root / "validation_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    before_hashes = protected_hashes(repo_root)
    schemas = load_schemas(repo_root / "docs/02_architecture/schemas")
    results: list[dict[str, Any]] = []

    events_path = input_root / "draft_registry_events.jsonl"
    if events_path.exists():
        for index, event in enumerate(read_jsonl(events_path), start=1):
            results.append(validate_phase16p_draft_event(event, subject_ref=f"{events_path}:{index}"))

    index_path = input_root / "draft_registry_index.json"
    if index_path.exists():
        results.append(validate_phase16p_index(read_json(index_path), subject_ref=str(index_path)))

    inventory_path = input_root / "artifact_inventory.json"
    if inventory_path.exists():
        results.append(validate_phase16p_inventory(read_json(inventory_path), subject_ref=str(inventory_path), repo_root=repo_root))

    for manifest_path in sorted(input_root.glob("*_manifest_candidate.json")):
        results.append(validate_phase16p_manifest_candidate(read_json(manifest_path), subject_ref=str(manifest_path)))

    schema_result = validate_schema_collection(schemas, repo_root=repo_root)
    results.append(schema_result)

    for result in results:
        name = safe_filename(result["subject_type"], result["subject_ref"])
        (results_dir / f"{name}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    after_hashes = protected_hashes(repo_root)
    hash_comparison = compare_hashes(before_hashes, after_hashes)
    summary = build_summary(results, before_hashes=before_hashes, after_hashes=after_hashes, hash_comparison=hash_comparison)
    (output_root / "validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "validation_audit.md").write_text(render_audit(summary, results), encoding="utf-8")
    return summary


def validate_registry_event(event: dict[str, Any], *, schemas: dict[str, dict[str, Any]] | None = None, repo_root: Path | None = None, subject_ref: str = "event") -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    schema = (schemas or {}).get("artifact_registry_event.schema.json")
    if schema is not None:
        add_schema_checks(checks, errors, schema_validate(event, schema, field_path="$"))

    add_identity_checks(checks, errors, warnings, event)
    add_hash_format_checks(checks, errors, event)
    add_lifecycle_checks(checks, errors, event)
    add_integrity_checks(checks, errors, warnings, event, repo_root=repo_root)
    add_acceptance_evidence_checks(checks, errors, event, schemas=schemas or {}, repo_root=repo_root)
    add_runtime_eligibility_checks(checks, errors, event)
    return make_result(
        subject_type="registry_event",
        subject_ref=subject_ref,
        validated_schema_version="artifact_registry_event.v1",
        checks=checks,
        errors=errors,
        warnings=warnings,
        evidence_refs=[],
        recommended_action=recommended_action(checks),
    )


def validate_phase16p_draft_event(event: dict[str, Any], *, subject_ref: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings = ["Phase16-P draft event requires transformation before formal Registry use."]
    for field in ("logical_artifact_id", "artifact_instance_id", "artifact_type", "component", "physical_path"):
        add_check(checks, field in event and bool(event.get(field)), "phase16p_identity", f"{field} present", f"$.{field}")
    for field in ("content_hash", "schema_hash"):
        value = event.get(field)
        if value in {None, "NOT_APPLICABLE", "NOT_FOUND"}:
            add_check(checks, True, "phase16p_hash", f"{field} legacy sentinel mappable to null", f"$.{field}", result="WARN", severity="WARNING")
            warnings.append(f"{field} uses legacy sentinel and must be mapped to null.")
        else:
            ok = is_sha256(value)
            add_check(checks, ok, "phase16p_hash", f"{field} sha256 format", f"$.{field}", failure_class="HALT")
            if not ok:
                errors.append(f"{field} is not SHA-256: {value}")
    status = event.get("status")
    if status == "ACCEPTED":
        add_check(checks, False, "phase16p_acceptance", "Phase16-P event must not be ACCEPTED", "$.status", failure_class="HALT")
        errors.append("Phase16-P event unexpectedly has ACCEPTED status.")
    else:
        add_check(checks, True, "phase16p_acceptance", "Phase16-P event is not ACCEPTED", "$.status")
    return make_result(
        subject_type="phase16p_draft_event",
        subject_ref=subject_ref,
        validated_schema_version="MAPPABLE_WITH_TRANSFORMATION",
        checks=checks,
        errors=errors,
        warnings=warnings,
        evidence_refs=[subject_ref],
        recommended_action="Migrate to formal event schema as DRAFT or VALIDATED only; do not auto-accept.",
    )


def validate_phase16p_index(index: dict[str, Any], *, subject_ref: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings = ["Phase16-P index is a draft derived artifact, not a formal materialized Registry Index."]
    errors: list[str] = []
    add_check(checks, index.get("index_type") == "DRAFT_REGISTRY_INDEX", "phase16p_index", "draft index type", "$.index_type", result="WARN", severity="WARNING")
    add_check(checks, int(index.get("accepted_event_count") or 0) == 0, "phase16p_index", "accepted event count is zero", "$.accepted_event_count")
    add_check(checks, isinstance(index.get("entries"), dict), "phase16p_index", "entries object present", "$.entries")
    return make_result(
        subject_type="phase16p_draft_index",
        subject_ref=subject_ref,
        validated_schema_version="MAPPABLE_WITH_TRANSFORMATION",
        checks=checks,
        errors=errors,
        warnings=warnings,
        evidence_refs=[subject_ref],
        recommended_action="Use as migration input only; rebuild formal index from Event Log later.",
    )


def validate_phase16p_inventory(inventory: dict[str, Any], *, subject_ref: str, repo_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    artifacts = list(inventory.get("artifacts") or [])
    add_check(checks, bool(artifacts), "inventory", "artifact list present", "$.artifacts")
    accepted = [a for a in artifacts if a.get("accepted_status_candidate") == "ACCEPTED"]
    add_check(checks, not accepted, "inventory_acceptance", "no ACCEPTED inventory candidates", "$.artifacts")
    runtime_states = [a for a in artifacts if a.get("artifact_type") == "RUNTIME_AUTHORITY_STATE"]
    add_check(checks, bool(runtime_states), "runtime_authority_boundary", "runtime authority states are boundary evidence only", "$.artifacts", result="WARN", severity="WARNING")
    for artifact in artifacts:
        path = artifact.get("current_physical_path")
        if path:
            expected_exists = bool(artifact.get("exists"))
            actual_exists = (repo_root / path).exists()
            if expected_exists != actual_exists:
                add_check(checks, False, "inventory_path", f"path existence mismatch: {path}", "$.artifacts", failure_class="REVIEW_REQUIRED")
                warnings.append(f"path existence differs from inventory for {path}")
    return make_result(
        subject_type="phase16p_artifact_inventory",
        subject_ref=subject_ref,
        validated_schema_version="PHASE16P_INVENTORY",
        checks=checks,
        errors=errors,
        warnings=warnings,
        evidence_refs=[subject_ref],
        recommended_action="Use inventory as read-only migration evidence.",
    )


def validate_phase16p_manifest_candidate(manifest: dict[str, Any], *, subject_ref: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings = ["Phase16-P manifest candidate requires transformation to formal Artifact Set Manifest schema."]
    artifacts = list(manifest.get("artifacts") or [])
    logical_ids = {str(a.get("logical_artifact_id_candidate") or "") for a in artifacts}
    subject_lower = subject_ref.lower()
    add_check(checks, bool(artifacts), "artifact_set", "member artifacts present", "$.artifacts")
    add_check(checks, bool(manifest.get("set_hash_candidate")), "artifact_set", "set hash candidate present", "$.set_hash_candidate")
    if "opportunity" in subject_lower:
        required = {
            "ai.opportunity.model.accepted",
            "ai.opportunity.metrics.accepted",
            "ai.opportunity.training_metadata",
            "ai.opportunity.validation_evidence",
        }
        missing = sorted(required - logical_ids)
        add_check(checks, not missing, "opportunity_set_required_members", "Opportunity required members present", "$.artifacts", failure_class="HALT")
        if missing:
            errors.append("Opportunity set missing required members: " + ",".join(missing))
        phase5e = [item for item in logical_ids if "phase5e" in item]
        add_check(checks, not phase5e, "opportunity_set_model_metrics", "Phase5-E metrics not mixed into Opportunity accepted set", "$.artifacts", failure_class="HALT")
        if phase5e:
            errors.append("Opportunity set contains Phase5-E metrics: " + ",".join(phase5e))
        if not any("feature_schema" in item or item.endswith(".schema") for item in logical_ids):
            add_check(checks, False, "opportunity_set_feature_schema", "Opportunity feature schema ref is absent in Phase16-P candidate", "$.artifacts", result="WARN", severity="WARNING", failure_class="REVIEW_REQUIRED")
            warnings.append("Opportunity feature schema ref must be added before formal ACCEPTED set.")
    return make_result(
        subject_type="phase16p_manifest_candidate",
        subject_ref=subject_ref,
        validated_schema_version="MAPPABLE_WITH_TRANSFORMATION",
        checks=checks,
        errors=errors,
        warnings=warnings,
        evidence_refs=[subject_ref],
        recommended_action="Transform to formal Artifact Set Manifest; keep runtime_use_eligible=false until accepted.",
    )


def validate_artifact_set_manifest(manifest: dict[str, Any], *, schemas: dict[str, dict[str, Any]] | None = None, subject_ref: str = "artifact_set") -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    schema = (schemas or {}).get("artifact_set_manifest.schema.json")
    if schema is not None:
        add_schema_checks(checks, errors, schema_validate(manifest, schema, field_path="$"))
    add_artifact_set_contract_checks(checks, errors, warnings, manifest)
    return make_result(
        subject_type="artifact_set_manifest",
        subject_ref=subject_ref,
        validated_schema_version="artifact_set_manifest.v1",
        checks=checks,
        errors=errors,
        warnings=warnings,
        evidence_refs=[],
        recommended_action=recommended_action(checks),
    )


def validate_schema_collection(schemas: dict[str, dict[str, Any]], *, repo_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    ids = [schema.get("$id") for schema in schemas.values()]
    add_check(checks, len(ids) == len(set(ids)), "schema_collection", "$id values are unique", "$id")
    for name, schema in sorted(schemas.items()):
        add_check(checks, schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "schema_collection", f"{name} uses Draft 2020-12", "$.$schema")
        add_check(checks, schema.get("type") == "object", "schema_collection", f"{name} type object", "$.type")
        add_check(checks, schema.get("additionalProperties") is False, "schema_collection", f"{name} additionalProperties false", "$.additionalProperties")
        required = set(schema.get("required") or [])
        properties = set((schema.get("properties") or {}).keys())
        add_check(checks, required.issubset(properties), "schema_collection", f"{name} required fields defined in properties", "$.required")
    return make_result(
        subject_type="schema_collection",
        subject_ref=str(repo_root / "docs/02_architecture/schemas"),
        validated_schema_version="SCHEMA_COLLECTION",
        checks=checks,
        errors=errors,
        warnings=[],
        evidence_refs=[],
        recommended_action=recommended_action(checks),
    )


def schema_validate(value: Any, schema: dict[str, Any], *, field_path: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    _schema_validate(value, schema, field_path, issues)
    return issues


def _schema_validate(value: Any, schema: dict[str, Any], field_path: str, issues: list[dict[str, Any]]) -> None:
    if "const" in schema and value != schema["const"]:
        issues.append(issue(False, "schema_const", f"const mismatch expected {schema['const']!r}", field_path, "VALIDATION_ERROR"))
    if "enum" in schema and value not in schema["enum"]:
        issues.append(issue(False, "schema_enum", f"enum mismatch: {value!r}", field_path, "VALIDATION_ERROR"))
    expected_type = schema.get("type")
    if expected_type is not None and not type_matches(value, expected_type):
        issues.append(issue(False, "schema_type", f"type mismatch expected {expected_type}", field_path, "VALIDATION_ERROR"))
        return
    if isinstance(value, str) and schema.get("pattern") and not re.fullmatch(schema["pattern"], value):
        issues.append(issue(False, "schema_pattern", "pattern mismatch", field_path, "VALIDATION_ERROR"))
    if isinstance(value, str) and schema.get("format") == "date-time" and not is_datetime(value):
        issues.append(issue(False, "schema_format", "date-time format mismatch", field_path, "VALIDATION_ERROR"))
    if isinstance(value, str) and schema.get("minLength") is not None and len(value) < int(schema["minLength"]):
        issues.append(issue(False, "schema_min_length", f"minLength mismatch expected {schema['minLength']}", field_path, "VALIDATION_ERROR"))
    if isinstance(value, dict):
        required = schema.get("required") or []
        properties = schema.get("properties") or {}
        for field in required:
            if field not in value:
                issues.append(issue(False, "schema_required", f"missing required field {field}", f"{field_path}.{field}", "VALIDATION_ERROR"))
        additional = schema.get("additionalProperties")
        if additional is False:
            for field in value:
                if field not in properties:
                    issues.append(issue(False, "schema_additional_properties", f"additional property {field}", f"{field_path}.{field}", "VALIDATION_ERROR"))
        elif isinstance(additional, dict):
            for field, child_value in value.items():
                if field not in properties:
                    _schema_validate(child_value, additional, f"{field_path}.{field}", issues)
        for field, child_schema in properties.items():
            if field in value:
                _schema_validate(value[field], child_schema, f"{field_path}.{field}", issues)
    if isinstance(value, list) and "items" in schema:
        if schema.get("minItems") is not None and len(value) < int(schema["minItems"]):
            issues.append(issue(False, "schema_min_items", f"minItems mismatch expected {schema['minItems']}", field_path, "VALIDATION_ERROR"))
        for index, item in enumerate(value):
            _schema_validate(item, schema["items"], f"{field_path}[{index}]", issues)


def type_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(type_matches(value, item) for item in expected)
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def add_schema_checks(checks: list[dict[str, Any]], errors: list[str], issues: list[dict[str, Any]]) -> None:
    if not issues:
        add_check(checks, True, "schema_validation", "schema validation passed", "$")
        return
    for item in issues:
        checks.append(item)
        errors.append(item["message"])


def add_identity_checks(checks: list[dict[str, Any]], errors: list[str], warnings: list[str], event: dict[str, Any]) -> None:
    for field in ("logical_artifact_id", "artifact_instance_id", "artifact_type", "component", "physical_path"):
        add_check(checks, field in event and event.get(field) not in {"", "UNKNOWN", "NOT_APPLICABLE"}, "identity", f"{field} valid", f"$.{field}", failure_class="VALIDATION_ERROR")
    logical = str(event.get("logical_artifact_id") or "")
    if re.search(r"phase\d+", logical.lower()):
        add_check(checks, False, "identity", "logical_artifact_id must not use phase number", "$.logical_artifact_id", failure_class="REVIEW_REQUIRED")
        warnings.append("logical_artifact_id contains phase-like text.")


def add_hash_format_checks(checks: list[dict[str, Any]], errors: list[str], event: dict[str, Any]) -> None:
    for field in ("content_hash", "schema_hash"):
        value = event.get(field)
        ok = value is None or is_sha256(value)
        add_check(checks, ok, "hash_format", f"{field} is null or SHA-256", f"$.{field}", failure_class="HALT")
        if not ok:
            errors.append(f"{field} invalid: {value!r}")
    for index, item in enumerate(event.get("source_hashes") or []):
        value = item.get("hash")
        ok = value is None or is_sha256(value)
        add_check(checks, ok, "source_hash_format", "source hash is null or SHA-256", f"$.source_hashes[{index}].hash", failure_class="HALT")
        if not ok:
            errors.append(f"source_hash invalid: {value!r}")


def add_lifecycle_checks(checks: list[dict[str, Any]], errors: list[str], event: dict[str, Any]) -> None:
    previous = event.get("previous_status")
    new = event.get("new_status")
    transition = (previous, new)
    if transition in PROHIBITED_TRANSITIONS:
        add_check(checks, False, "lifecycle", f"prohibited transition {previous}->{new}", "$.new_status", failure_class="HALT")
        errors.append(f"prohibited transition {previous}->{new}")
    elif transition in ALLOWED_TRANSITIONS or event.get("event_type") in {"PATH_REGISTERED", "PATH_MIGRATED", "ELIGIBILITY_CHANGED", "CHECKPOINT_CREATED"}:
        add_check(checks, True, "lifecycle", "lifecycle transition allowed", "$.new_status")
    else:
        add_check(checks, False, "lifecycle", f"illegal transition {previous}->{new}", "$.new_status", failure_class="HALT")
        errors.append(f"illegal transition {previous}->{new}")

    if event.get("runtime_use_eligible") is True and new != "ACCEPTED":
        add_check(checks, False, "runtime_eligibility", "runtime_use_eligible true requires ACCEPTED status", "$.runtime_use_eligible", failure_class="HALT")
        errors.append("runtime_use_eligible=true without ACCEPTED status")
    if event.get("event_type") == "PATH_MIGRATED":
        old_path = event.get("previous_physical_path")
        new_path = event.get("new_physical_path")
        add_check(checks, bool(old_path), "path_migrated", "previous_physical_path present", "$.previous_physical_path", failure_class="HALT")
        add_check(checks, bool(new_path), "path_migrated", "new_physical_path present", "$.new_physical_path", failure_class="HALT")
        add_check(checks, bool(old_path and new_path and old_path != new_path), "path_migrated", "previous and new paths differ", "$.new_physical_path", failure_class="HALT")
        if not old_path or not new_path or old_path == new_path:
            errors.append("PATH_MIGRATED requires distinct previous/new physical paths")


def add_integrity_checks(checks: list[dict[str, Any]], errors: list[str], warnings: list[str], event: dict[str, Any], *, repo_root: Path | None) -> None:
    path_value = event.get("physical_path")
    if repo_root is None or not path_value:
        return
    if (
        event.get("artifact_type") == "ARTIFACT_SET"
        and event.get("new_status") in {"DRAFT", "VALIDATED"}
        and event.get("runtime_use_eligible") is False
    ):
        add_check(checks, True, "integrity_hash", "non-eligible Artifact Set registration path hash is not Runtime authority", "$.content_hash", result="SKIPPED", severity="INFO")
        return
    path = repo_root / str(path_value)
    exists = path.exists()
    failure_class = criticality_failure_class(event)
    add_check(checks, exists, "integrity_path", "physical path exists", "$.physical_path", failure_class=failure_class)
    if not exists:
        if failure_class == "REVIEW_REQUIRED":
            warnings.append(f"physical path not found: {path_value}")
        else:
            errors.append(f"critical physical path not found: {path_value}")
        return
    content_hash = event.get("content_hash")
    if path.is_file() and content_hash:
        actual = sha256_file(path)
        expected = strip_sha_prefix(str(content_hash))
        add_check(checks, actual == expected, "integrity_hash", "content hash matches file", "$.content_hash", failure_class="HALT")
        if actual != expected:
            errors.append(f"content hash mismatch for {path_value}")
    elif path.is_dir() and content_hash:
        actual, _, _ = directory_inventory(path)
        expected = strip_sha_prefix(str(content_hash))
        add_check(checks, actual == expected, "integrity_directory_hash", "directory inventory hash matches", "$.content_hash", failure_class="HALT")
        if actual != expected:
            errors.append(f"directory hash mismatch for {path_value}")


def add_acceptance_evidence_checks(
    checks: list[dict[str, Any]],
    errors: list[str],
    event: dict[str, Any],
    *,
    schemas: dict[str, dict[str, Any]],
    repo_root: Path | None,
) -> None:
    if event.get("new_status") != "ACCEPTED" and event.get("runtime_use_eligible") is not True:
        add_check(checks, True, "acceptance_evidence", "acceptance evidence not applicable", "$.new_status", result="SKIPPED", severity="INFO")
        return
    subject = acceptance_subject_ref(event)
    for field in ("acceptance_report_ref", "review_ref", "regression_ref"):
        ok = bool(event.get(field))
        add_check(checks, ok, "acceptance_evidence", f"{field} present for ACCEPTED", f"$.{field}", failure_class="HALT")
        if not ok:
            errors.append(f"{field} missing for ACCEPTED event")
    if repo_root is None or any(not event.get(field) for field in ("acceptance_report_ref", "review_ref", "regression_ref")):
        return

    report_ref = str(event["acceptance_report_ref"])
    recorded_report_hash = source_hash_for_ref(event, report_ref)
    report_path = resolve_evidence_ref(report_ref, repo_root=repo_root)
    if recorded_report_hash and report_path is not None and report_path.is_file():
        current_report_hash = sha256_file(report_path)
        if current_report_hash != recorded_report_hash:
            add_check(
                checks,
                True,
                "acceptance_evidence",
                "acceptance report current path differs from event source hash; recorded source hash retained",
                "$.acceptance_report_ref",
                result="WARN",
                severity="WARNING",
            )
            return

    report = read_evidence_json(event["acceptance_report_ref"], repo_root=repo_root)
    if report is None:
        add_check(checks, False, "acceptance_evidence", "acceptance report exists", "$.acceptance_report_ref", failure_class="HALT")
        errors.append("acceptance report missing or unreadable")
    else:
        add_schema_checks(checks, errors, schema_validate(report, schemas["artifact_acceptance_report.schema.json"], field_path="$.acceptance_report"))
        add_check(checks, report.get("decision") == "ACCEPT", "acceptance_evidence", "acceptance report decision ACCEPT", "$.acceptance_report.decision", failure_class="HALT")
        add_check(checks, report.get("artifact_or_set_ref") == subject, "acceptance_evidence", "acceptance report subject matches", "$.acceptance_report.artifact_or_set_ref", failure_class="HALT")
        set_hash_ok = report.get("artifact_set_hash") == event.get("content_hash")
        member_hash_ok = evidence_hash_matches(report.get("reviewed_artifact_hashes"), event.get("content_hash"))
        add_check(checks, set_hash_ok or member_hash_ok, "acceptance_evidence", "acceptance report content hash matches", "$.acceptance_report.reviewed_artifact_hashes", failure_class="HALT")
        schema_mapping = report.get("reviewed_schema_hashes")
        set_schema_hash_ok = isinstance(schema_mapping, dict) and stable_json_hash(schema_mapping) == event.get("schema_hash")
        member_schema_hash_ok = evidence_hash_matches(schema_mapping, event.get("schema_hash"), allow_null=True)
        add_check(checks, set_schema_hash_ok or member_schema_hash_ok, "acceptance_evidence", "acceptance report schema hash matches", "$.acceptance_report.reviewed_schema_hashes", failure_class="HALT")

    regression = read_evidence_json(event["regression_ref"], repo_root=repo_root)
    if regression is None:
        add_check(checks, False, "acceptance_evidence", "regression evidence exists", "$.regression_ref", failure_class="HALT")
        errors.append("regression evidence missing or unreadable")
    else:
        add_schema_checks(checks, errors, schema_validate(regression, schemas["artifact_regression_evidence.schema.json"], field_path="$.regression"))
        add_check(checks, regression.get("artifact_or_set_ref") == subject, "acceptance_evidence", "regression subject matches", "$.regression.artifact_or_set_ref", failure_class="HALT")
        add_check(checks, regression.get("result") == "PASS", "acceptance_evidence", "regression result PASS", "$.regression.result", failure_class="HALT")
        parity_ok = not regression.get("failures") and all(regression.get(field) in SUCCESS_REGRESSION_VALUES for field in regression_parity_fields())
        add_check(checks, parity_ok, "acceptance_evidence", "regression has no critical parity failure", "$.regression", failure_class="HALT")

    approvals = read_approval_evidence(event["review_ref"], repo_root=repo_root)
    if approvals is None:
        add_check(checks, False, "acceptance_evidence", "review approvals exist", "$.review_ref", failure_class="HALT")
        errors.append("review approvals missing or unreadable")
    else:
        for index, approval in enumerate(approvals):
            add_schema_checks(checks, errors, schema_validate(approval, schemas["artifact_review_approval.schema.json"], field_path=f"$.approvals[{index}]"))
        approval_types = {approval.get("approval_type") for approval in approvals if approval.get("decision") == "APPROVED"}
        add_check(checks, REQUIRED_APPROVAL_TYPES.issubset(approval_types), "acceptance_evidence", "all required approval roles exist", "$.review_ref", failure_class="HALT")
        for approval in approvals:
            add_check(checks, approval.get("subject_ref") == subject, "acceptance_evidence", "approval subject matches", "$.review_ref.subject_ref", failure_class="HALT")
            add_check(checks, approval.get("decision") == "APPROVED", "acceptance_evidence", "approval decision APPROVED", "$.review_ref.decision", failure_class="HALT")
            add_check(checks, bool(approval.get("evidence_refs")), "acceptance_evidence", "approval evidence refs present", "$.review_ref.evidence_refs", failure_class="HALT")


def add_runtime_eligibility_checks(checks: list[dict[str, Any]], errors: list[str], event: dict[str, Any]) -> None:
    new = event.get("new_status")
    eligible = bool(event.get("runtime_use_eligible"))
    if new in {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "LEGACY", "REVOKED", "REJECTED"}:
        ok = not eligible
        add_check(checks, ok, "runtime_eligibility", f"{new} is runtime ineligible", "$.runtime_use_eligible", failure_class="HALT")
        if not ok:
            errors.append(f"{new} event has runtime_use_eligible=true")
    if new == "REVOKED":
        ok = not eligible
        add_check(checks, ok, "runtime_eligibility", "REVOKED must be runtime ineligible", "$.runtime_use_eligible", failure_class="HALT")


def make_result(
    *,
    subject_type: str,
    subject_ref: str,
    validated_schema_version: str | None,
    checks: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    evidence_refs: list[str],
    recommended_action: str | None,
) -> dict[str, Any]:
    failure_class = classify_failure(checks)
    if failure_class in {"HALT", "VALIDATION_ERROR"}:
        overall = "FAIL"
    elif failure_class == "REVIEW_REQUIRED":
        overall = "REVIEW_REQUIRED"
    elif any(check["result"] == "WARN" for check in checks) or warnings:
        overall = "PASS_WITH_WARNINGS"
    else:
        overall = "PASS"
    fingerprint = stable_json_hash(
        {
            "subject_type": subject_type,
            "subject_ref": subject_ref,
            "checks": [(c["check_type"], c["result"], c["field_path"], c["message"]) for c in checks],
        }
    )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "validation_id": f"validation-{uuid.uuid4()}-{fingerprint[:16]}",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "subject_type": subject_type,
        "subject_ref": subject_ref,
        "validator_version": VALIDATOR_VERSION,
        "validated_schema_version": validated_schema_version,
        "overall_result": overall,
        "failure_class": failure_class,
        "checks": [
            {key: check[key] for key in ("check_id", "check_type", "result", "severity", "message", "field_path", "evidence_ref")}
            for check in checks
        ],
        "errors": list(dict.fromkeys(errors + [c["message"] for c in checks if c["result"] == "FAIL"])),
        "warnings": list(dict.fromkeys(warnings + [c["message"] for c in checks if c["result"] == "WARN"])),
        "evidence_refs": evidence_refs,
        "recommended_action": recommended_action,
    }


def add_check(
    checks: list[dict[str, Any]],
    ok: bool,
    check_type: str,
    message: str,
    field_path: str,
    *,
    result: str | None = None,
    severity: str | None = None,
    failure_class: str = "VALIDATION_ERROR",
    evidence_ref: str | None = None,
) -> None:
    if result is None:
        result = "PASS" if ok else "FAIL"
    if severity is None:
        severity = "INFO" if result in {"PASS", "SKIPPED"} else ("WARNING" if result == "WARN" else "ERROR")
    item = {
        "check_id": f"{check_type}:{len(checks) + 1}",
        "check_type": check_type,
        "result": result if ok or result != "PASS" else "PASS",
        "severity": severity,
        "message": message,
        "field_path": field_path,
        "evidence_ref": evidence_ref,
        "_failure_class": "NONE" if ok or result in {"PASS", "SKIPPED", "WARN"} else failure_class,
    }
    checks.append(item)


def issue(ok: bool, check_type: str, message: str, field_path: str, failure_class: str) -> dict[str, Any]:
    return {
        "check_id": check_type,
        "check_type": check_type,
        "result": "PASS" if ok else "FAIL",
        "severity": "INFO" if ok else "ERROR",
        "message": message,
        "field_path": field_path,
        "evidence_ref": None,
        "_failure_class": "NONE" if ok else failure_class,
    }


def classify_failure(checks: list[dict[str, Any]]) -> str:
    classes = {check.get("_failure_class") for check in checks if check.get("_failure_class") and check.get("_failure_class") != "NONE"}
    if "HALT" in classes:
        return "HALT"
    if "VALIDATION_ERROR" in classes:
        return "VALIDATION_ERROR"
    if "REVIEW_REQUIRED" in classes:
        return "REVIEW_REQUIRED"
    return "NONE"


def recommended_action(checks: list[dict[str, Any]]) -> str:
    failure = classify_failure(checks)
    if failure == "HALT":
        return "Stop and review before Registry use."
    if failure == "VALIDATION_ERROR":
        return "Fix schema/field contract before validation can pass."
    if failure == "REVIEW_REQUIRED":
        return "Review missing or ambiguous evidence before Registry use."
    return "No action required for this validation scope."


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and value not in SENTINEL_HASH_VALUES and bool(SHA256_RE.fullmatch(value))


def strip_sha_prefix(value: str) -> str:
    return value[7:] if value.startswith("sha256:") else value


def ensure_safe_output_root(input_root: Path, output_root: Path, *, repo_root: Path) -> None:
    repo = repo_root.resolve()
    input_resolved = (repo_root / input_root).resolve() if not input_root.is_absolute() else input_root.resolve()
    output_resolved = (repo_root / output_root).resolve() if not output_root.is_absolute() else output_root.resolve()
    if output_resolved == input_resolved or is_relative_to(output_resolved, input_resolved):
        raise ValidationSafetyError(f"unsafe output root overlaps input root: {output_resolved}")
    forbidden_roots = [
        repo / ".runtime",
        repo / ".runtime" / "artifact_registry",
        repo / ".runtime" / "artifacts",
        repo / "reports" / "opportunity_ai",
        repo / "src" / "ai_fund_lab_v2" / "runtime_v2",
        repo / "src" / "ai_fund_lab_v2" / "position_management_ai",
    ]
    for forbidden in forbidden_roots:
        resolved = forbidden.resolve() if forbidden.exists() else forbidden
        if output_resolved == resolved or is_relative_to(output_resolved, resolved):
            raise ValidationSafetyError(f"unsafe output root under protected path: {output_resolved}")


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def is_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def criticality_failure_class(event: dict[str, Any]) -> str:
    return "HALT" if artifact_is_runtime_critical(event) else "REVIEW_REQUIRED"


def artifact_is_runtime_critical(event: dict[str, Any]) -> bool:
    artifact_type = str(event.get("artifact_type") or "").upper()
    retention = str(event.get("retention_class") or "").upper()
    consumers = " ".join(str(item) for item in event.get("consumer_compatibility") or []).upper()
    if event.get("runtime_use_eligible") is True or event.get("new_status") == "ACCEPTED":
        return True
    critical_terms = ("MODEL", "METRICS", "CODE_POLICY", "RUNTIME_ADAPTER", "POLICY", "SAFETY", "FEATURE", "DECISION")
    evidence_terms = ("TRAINING", "VALIDATION", "HISTORICAL", "LEGACY", "AUDIT", "EVIDENCE")
    if any(term in artifact_type for term in critical_terms) and not any(term in artifact_type or term in retention for term in evidence_terms):
        return True
    return "RUNTIME" in consumers


def acceptance_subject_ref(event: dict[str, Any]) -> str:
    return str(event.get("artifact_set_id") or event.get("artifact_instance_id") or event.get("logical_artifact_id") or "")


def evidence_hash_matches(mapping: Any, expected: Any, *, allow_null: bool = False) -> bool:
    if expected is None:
        return allow_null
    if not isinstance(mapping, dict):
        return False
    expected_clean = strip_sha_prefix(str(expected))
    values = {strip_sha_prefix(str(value)) for value in mapping.values() if value is not None}
    return expected_clean in values


def source_hash_for_ref(event: dict[str, Any], ref: str) -> str | None:
    for item in event.get("source_hashes") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("ref") or "") == ref:
            value = item.get("hash")
            return strip_sha_prefix(str(value)) if value else None
    return None


def read_evidence_json(ref: str, *, repo_root: Path) -> Any | None:
    path = resolve_evidence_ref(ref, repo_root=repo_root)
    if path is None or not path.is_file():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def read_approval_evidence(ref: str, *, repo_root: Path) -> list[dict[str, Any]] | None:
    path = resolve_evidence_ref(ref, repo_root=repo_root)
    if path is None or not path.exists():
        return None
    try:
        if path.is_dir():
            approvals = [read_json(child) for child in sorted(path.glob("*.json"))]
        else:
            payload = read_json(path)
            approvals = payload if isinstance(payload, list) else [payload]
    except Exception:
        return None
    if not all(isinstance(item, dict) for item in approvals):
        return None
    return approvals


def resolve_evidence_ref(ref: str, *, repo_root: Path) -> Path | None:
    if not ref:
        return None
    path = Path(ref)
    return path if path.is_absolute() else repo_root / path


def regression_parity_fields() -> tuple[str, ...]:
    return (
        "semantic_comparison",
        "hash_comparison",
        "schema_comparison",
        "candidate_decision_parity",
        "opportunity_decision_parity",
        "pm_decision_parity",
        "capital_allocation_parity",
        "planning_parity",
        "pending_parity",
        "submit_guard_parity",
    )


def add_artifact_set_contract_checks(checks: list[dict[str, Any]], errors: list[str], warnings: list[str], manifest: dict[str, Any]) -> None:
    set_type = manifest.get("artifact_set_type")
    members = list(manifest.get("member_artifacts") or [])
    roles = [normalized_member_role(member) for member in members]
    role_set = set(roles)
    required = required_roles_for_manifest(set_type, role_set)
    missing = sorted(required - role_set)
    add_check(checks, not missing, "artifact_set_required_members", f"{set_type} required roles present", "$.member_artifacts", failure_class="HALT")
    if missing:
        errors.append(f"{set_type} missing roles: " + ",".join(missing))
    duplicates = sorted(role for role in role_set if roles.count(role) > 1)
    add_check(checks, not duplicates, "artifact_set_duplicate_members", "member roles are unique", "$.member_artifacts", failure_class="HALT")
    if duplicates:
        errors.append("duplicate member roles: " + ",".join(duplicates))

    member_hashes = manifest.get("member_hashes") or {}
    schema_hashes = manifest.get("schema_hashes") or {}
    for index, member in enumerate(members):
        role = normalized_member_role(member)
        logical_id = str(member.get("logical_artifact_id") or "")
        content_hash = member.get("content_hash")
        schema_hash = member.get("schema_hash")
        add_check(checks, is_sha256(content_hash), "artifact_set_member_hash", f"{role} content hash present", f"$.member_artifacts[{index}].content_hash", failure_class="HALT")
        add_check(checks, is_sha256(schema_hash), "artifact_set_member_schema_hash", f"{role} schema hash present", f"$.member_artifacts[{index}].schema_hash", failure_class="HALT")
        add_check(checks, member_hashes.get(logical_id) == content_hash, "artifact_set_member_hash", f"{role} member hash matches map", "$.member_hashes", failure_class="HALT")
        add_check(checks, schema_hashes.get(logical_id) == schema_hash, "artifact_set_member_schema_hash", f"{role} schema hash matches map", "$.schema_hashes", failure_class="HALT")

    expected_hash = artifact_set_hash(manifest)
    add_check(checks, manifest.get("artifact_set_hash") == expected_hash, "artifact_set_hash", "artifact set hash matches manifest members", "$.artifact_set_hash", failure_class="HALT")
    add_check(checks, manifest.get("status") == "ACCEPTED" or manifest.get("runtime_use_eligible") is False, "artifact_set_runtime_eligibility", "runtime_use_eligible true requires ACCEPTED set", "$.runtime_use_eligible", failure_class="HALT")
    add_check(checks, bool(manifest.get("runtime_consumer_refs")), "artifact_set_consumer", "runtime consumers present", "$.runtime_consumer_refs", failure_class="REVIEW_REQUIRED")

    if normalize_set_type(set_type) == "OPPORTUNITY_AI_SET":
        model = member_by_role(members, "MODEL")
        metrics = member_by_role(members, "METRICS")
        same_set = bool(model and metrics and model.get("artifact_set_id", manifest.get("artifact_set_id")) == metrics.get("artifact_set_id", manifest.get("artifact_set_id")))
        metrics_status = str((metrics or {}).get("migration_status") or (metrics or {}).get("accepted_status") or (metrics or {}).get("status") or "").upper()
        legacy_metrics = metrics_status in {"LEGACY_ONLY", "TRAINING_ONLY", "LEGACY", "REVOKED"}
        add_check(checks, same_set, "opportunity_set_model_metrics", "Opportunity model and metrics belong to same set identity", "$.member_artifacts", failure_class="HALT")
        add_check(checks, not legacy_metrics, "opportunity_set_model_metrics", "Opportunity metrics are runtime-eligible accepted evidence, not legacy/training-only", "$.member_artifacts", failure_class="HALT")
        if legacy_metrics:
            errors.append("Opportunity metrics are classified as legacy/training-only.")


def required_roles_for_set(set_type: Any) -> set[str]:
    legacy = {
        "CANDIDATE_ACCEPTED_SET": {"MODEL", "MODEL_MANIFEST", "FEATURE_SCHEMA", "TRAINING_METADATA", "VALIDATION_EVIDENCE"},
        "OPPORTUNITY_ACCEPTED_SET": {"MODEL", "METRICS", "FEATURE_SCHEMA", "TRAINING_METADATA", "VALIDATION_EVIDENCE"},
        "PM_ACCEPTED_SET": {"CODE_POLICY", "RUNTIME_ADAPTER", "POLICY_VERSION", "FEATURE_VERSION", "CODE_HASH", "ADAPTER_HASH"},
    }
    if str(set_type) in legacy:
        return legacy[str(set_type)]
    return {
        "CANDIDATE_AI_SET": {"MODEL", "MODEL_MANIFEST", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "METRICS_EVIDENCE", "CONSUMER_COMPATIBILITY"},
        "OPPORTUNITY_AI_SET": {"MODEL", "METRICS", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE", "CONSUMER_COMPATIBILITY"},
        "POSITION_MANAGEMENT_POLICY_SET": {"CODE_POLICY", "RUNTIME_ADAPTER", "POLICY_VERSION", "FEATURE_VERSION", "BEHAVIOR_CONTRACT", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"},
        "CAPITAL_ALLOCATION_POLICY_SET": {"POLICY", "POLICY_SCHEMA", "POLICY_VERSION", "VALIDATION_EVIDENCE", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"},
        "FEATURE_SCHEMA_SET": {"FEATURE_SCHEMA", "POINT_IN_TIME_EVIDENCE", "CONSUMER_COMPATIBILITY", "SCHEMA_VALIDATION_EVIDENCE"},
        "SAFETY_POLICY_SET": {"POLICY", "POLICY_SCHEMA", "POLICY_VERSION", "VALIDATION_EVIDENCE", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"},
    }.get(normalize_set_type(set_type), set())


def required_roles_for_manifest(set_type: Any, role_set: set[str]) -> set[str]:
    if str(set_type) == "CAPITAL_ALLOCATION_POLICY_SET" and "POLICY_HASH" in role_set:
        return {"POLICY", "POLICY_SCHEMA", "POLICY_VERSION", "POLICY_HASH", "VALIDATION_EVIDENCE", "CONSUMER_COMPATIBILITY"}
    return required_roles_for_set(set_type)


def normalize_set_type(set_type: Any) -> str:
    aliases = {
        "CANDIDATE_ACCEPTED_SET": "CANDIDATE_AI_SET",
        "OPPORTUNITY_ACCEPTED_SET": "OPPORTUNITY_AI_SET",
        "PM_ACCEPTED_SET": "POSITION_MANAGEMENT_POLICY_SET",
    }
    value = str(set_type)
    return aliases.get(value, value)


def normalized_member_role(member: dict[str, Any]) -> str:
    raw = str(member.get("member_role") or member.get("role") or "")
    aliases = {
        "model": "MODEL",
        "manifest": "MODEL_MANIFEST",
        "metrics": "METRICS",
        "feature_schema": "FEATURE_SCHEMA",
        "training_metadata": "TRAINING_METADATA",
        "training_data_lineage": "TRAINING_DATA_LINEAGE",
        "validation_evidence": "VALIDATION_EVIDENCE",
        "metrics_evidence": "METRICS_EVIDENCE",
        "consumer_compatibility": "CONSUMER_COMPATIBILITY",
        "code_policy": "CODE_POLICY",
        "runtime_adapter": "RUNTIME_ADAPTER",
        "policy_version": "POLICY_VERSION",
        "feature_version": "FEATURE_VERSION",
        "behavior_contract": "BEHAVIOR_CONTRACT",
        "regression_evidence": "REGRESSION_EVIDENCE",
        "policy_artifact": "POLICY",
        "policy": "POLICY",
        "policy_schema": "POLICY_SCHEMA",
        "policy_hash": "POLICY_HASH",
        "code_hash": "CODE_HASH",
        "adapter_hash": "ADAPTER_HASH",
        "point_in_time_evidence": "POINT_IN_TIME_EVIDENCE",
        "schema_validation_evidence": "SCHEMA_VALIDATION_EVIDENCE",
    }
    return aliases.get(raw, raw)


def artifact_set_hash(manifest: dict[str, Any]) -> str:
    payload = {
        "artifact_set_id": manifest.get("artifact_set_id"),
        "artifact_set_type": manifest.get("artifact_set_type"),
        "artifact_set_version": manifest.get("artifact_set_version"),
        "member_artifacts": manifest.get("member_artifacts") or [],
        "member_hashes": manifest.get("member_hashes") or {},
        "schema_hashes": manifest.get("schema_hashes") or {},
        "runtime_consumer_refs": manifest.get("runtime_consumer_refs") or [],
    }
    return stable_json_hash(payload)


def member_by_role(members: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    for member in members:
        if normalized_member_role(member) == role:
            return member
    return None


def load_schemas(schema_root: Path) -> dict[str, dict[str, Any]]:
    return {path.name: read_json(path) for path in sorted(schema_root.glob("artifact_*.schema.json"))}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def safe_filename(subject_type: str, subject_ref: str) -> str:
    raw = f"{subject_type}-{stable_json_hash(subject_ref)[:16]}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)


def protected_paths() -> list[str]:
    return [
        ".runtime/persistent_ledger/state.json",
        ".runtime/persistent_ledger/orders.jsonl",
        ".runtime/pending_order_plan/pending_order_plan.json",
        ".runtime/runtime_state/current_state.json",
        ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
        ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json",
        "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
        "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json",
        "reports/opportunity_ai/phase5e/opportunity_training_metrics.json",
        "src/ai_fund_lab_v2/position_management_ai/inference.py",
        "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
        ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
        ".runtime/operations/feature_artifacts/2026-07-10/candidate_features.parquet",
        ".runtime/runtime_state/position_management/2026-07-10/position_management_decisions.json",
    ]


def protected_hashes(repo_root: Path) -> dict[str, dict[str, Any]]:
    hashes: dict[str, dict[str, Any]] = {}
    for rel in protected_paths():
        path = repo_root / rel
        if path.is_file():
            hashes[rel] = {"exists": True, "type": "file", "sha256": sha256_file(path)}
        elif path.is_dir():
            digest, count, size = directory_inventory(path)
            hashes[rel] = {"exists": True, "type": "directory", "sha256": digest, "file_count": count, "size_bytes": size}
        else:
            hashes[rel] = {"exists": False, "type": "missing", "sha256": None}
    return hashes


def compare_hashes(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(set(before) | set(after)):
        before_item = before.get(path)
        after_item = after.get(path)
        rows.append(
            {
                "path": path,
                "before": before_item,
                "after": after_item,
                "result": "UNCHANGED" if before_item == after_item else "CHANGED",
            }
        )
    return rows


def build_summary(
    results: list[dict[str, Any]],
    *,
    before_hashes: dict[str, dict[str, Any]],
    after_hashes: dict[str, dict[str, Any]],
    hash_comparison: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = {key: 0 for key in ("PASS", "PASS_WITH_WARNINGS", "REVIEW_REQUIRED", "FAIL")}
    failure_counts = {key: 0 for key in ("NONE", "VALIDATION_ERROR", "REVIEW_REQUIRED", "HALT")}
    for result in results:
        counts[result["overall_result"]] += 1
        failure_counts[result["failure_class"]] += 1
    return {
        "schema_version": "phase16v_validation_summary.v1",
        "validator_version": VALIDATOR_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(results),
        "overall_result_counts": counts,
        "failure_class_counts": failure_counts,
        "accepted_artifact_count": 0,
        "runtime_use_eligible_count": 0,
        "formal_registry_path_created": Path(".runtime/artifact_registry").exists(),
        "formal_artifacts_path_created": Path(".runtime/artifacts").exists(),
        "event_log_writer_implemented": False,
        "index_builder_implemented": False,
        "uuid_policy": "uuid4_plus_deterministic_fingerprint_fallback; uuidv7 unavailable in stdlib",
        "protected_before_hashes": before_hashes,
        "protected_after_hashes": after_hashes,
        "protected_hash_comparison": hash_comparison,
        "protected_hash_result": "UNCHANGED" if all(row["result"] == "UNCHANGED" for row in hash_comparison) else "CHANGED",
    }


def render_audit(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase16-V Minimal Read-only Registry Validator Audit",
        "",
        f"- validator_version: {summary['validator_version']}",
        f"- result_count: {summary['result_count']}",
        f"- PASS: {summary['overall_result_counts']['PASS']}",
        f"- PASS_WITH_WARNINGS: {summary['overall_result_counts']['PASS_WITH_WARNINGS']}",
        f"- REVIEW_REQUIRED: {summary['overall_result_counts']['REVIEW_REQUIRED']}",
        f"- FAIL: {summary['overall_result_counts']['FAIL']}",
        f"- HALT: {summary['failure_class_counts']['HALT']}",
        f"- accepted_artifact_count: {summary['accepted_artifact_count']}",
        f"- runtime_use_eligible_count: {summary['runtime_use_eligible_count']}",
        f"- protected_hash_result: {summary['protected_hash_result']}",
        f"- formal_registry_path_created: {summary['formal_registry_path_created']}",
        f"- formal_artifacts_path_created: {summary['formal_artifacts_path_created']}",
        "",
        "## Results",
    ]
    for result in results:
        lines.append(f"- {result['overall_result']} / {result['failure_class']}: {result['subject_type']} `{result['subject_ref']}`")
    lines.extend(["", "## Protected Hash Comparison"])
    for row in summary["protected_hash_comparison"]:
        lines.append(f"- {row['result']}: {row['path']}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase16-V read-only artifact registry validation.")
    parser.add_argument("--input", default="reports/phase16_registry_inventory")
    parser.add_argument("--output", default="reports/phase16_registry_validation")
    args = parser.parse_args(argv)
    try:
        validate_phase16_inventory(Path(args.input), Path(args.output), repo_root=Path.cwd())
    except ValidationSafetyError as exc:
        print(f"VALIDATION_ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
