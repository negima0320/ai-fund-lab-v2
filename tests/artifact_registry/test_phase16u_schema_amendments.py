import json
import re
from pathlib import Path


SCHEMA_ROOT = Path("docs/02_architecture/schemas")


def _load(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _schemas() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(SCHEMA_ROOT.glob("artifact_*.schema.json"))]


def test_phase16u_all_schemas_parse_and_ids_are_unique() -> None:
    schemas = _schemas()
    ids = [schema["$id"] for schema in schemas]
    assert len(ids) == len(set(ids))
    for schema in schemas:
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert set(schema["required"]).issubset(schema["properties"])


def test_phase16u_non_event_schemas_have_schema_version_const() -> None:
    expected = {
        "artifact_registry_entry.schema.json": "artifact_registry_entry.v1",
        "artifact_set_manifest.schema.json": "artifact_set_manifest.v1",
        "artifact_acceptance_report.schema.json": "artifact_acceptance_report.v1",
        "artifact_regression_evidence.schema.json": "artifact_regression_evidence.v1",
        "artifact_review_approval.schema.json": "artifact_review_approval.v1",
        "artifact_registry_checkpoint.schema.json": "artifact_registry_checkpoint.v1",
        "artifact_validation_result.schema.json": "artifact_validation_result.v1",
        "artifact_acceptance_evidence_bundle.schema.json": "artifact_acceptance_evidence_bundle.v1",
        "artifact_acceptance_validation_result.schema.json": "artifact_acceptance_validation_result.v1",
    }
    for name, const_value in expected.items():
        schema = _load(name)
        assert "schema_version" in schema["required"]
        assert schema["properties"]["schema_version"]["const"] == const_value


def test_phase16u_validation_result_schema_enums() -> None:
    schema = _load("artifact_validation_result.schema.json")
    props = schema["properties"]
    assert props["overall_result"]["enum"] == ["PASS", "PASS_WITH_WARNINGS", "REVIEW_REQUIRED", "FAIL"]
    assert props["failure_class"]["enum"] == ["NONE", "VALIDATION_ERROR", "REVIEW_REQUIRED", "HALT"]
    check_props = props["checks"]["items"]["properties"]
    assert check_props["result"]["enum"] == ["PASS", "WARN", "FAIL", "SKIPPED"]
    assert check_props["severity"]["enum"] == ["INFO", "WARNING", "ERROR", "CRITICAL"]


def test_phase16u_event_hash_policy_disallows_empty_string_and_allows_null() -> None:
    schema = _load("artifact_registry_event.schema.json")
    for field in ("content_hash", "schema_hash"):
        prop = schema["properties"][field]
        assert "null" in prop["type"]
        assert re.fullmatch(prop["pattern"], "a" * 64)
        assert re.fullmatch(prop["pattern"], "sha256:" + "a" * 64)
        assert not re.fullmatch(prop["pattern"], "")
        assert not re.fullmatch(prop["pattern"], "UNKNOWN")
        assert not re.fullmatch(prop["pattern"], "NOT_APPLICABLE")
    source_hash = schema["properties"]["source_hashes"]["items"]["properties"]["hash"]
    assert "null" in source_hash["type"]
    assert not re.fullmatch(source_hash["pattern"], "")


def test_phase16u_path_migrated_fields_exist() -> None:
    schema = _load("artifact_registry_event.schema.json")
    assert "previous_physical_path" in schema["required"]
    assert "new_physical_path" in schema["required"]
    assert schema["properties"]["previous_physical_path"]["type"] == ["string", "null"]
    assert schema["properties"]["new_physical_path"]["type"] == ["string", "null"]
