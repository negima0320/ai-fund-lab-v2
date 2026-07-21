from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


class ArtifactSchemaError(ValueError):
    """Fail-closed error for schema-incompatible training artifacts."""


def stable_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_staging_artifact(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    write_json(tmp, payload)
    os.replace(tmp, path)


def cleanup_failed_staging(staging_dir: Path, *, failure_reason: str, partial_artifacts: list[str] | None = None) -> dict[str, Any]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "status": "FAILED",
        "failure_reason": failure_reason,
        "partial_artifacts": partial_artifacts or [],
        "cleanup_status": "RECORDED_NO_FORMAL_COMMIT",
        "formal_generation_candidate_created": False,
        "accepted_decision_created": False,
        "runtime_pointer_written": False,
    }
    write_json(staging_dir / "status.json", status)
    return status


def reset_staging_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def validate_artifact_against_schema(artifact: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    schema = read_json(schema_path)
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    missing = [field for field in required if field not in artifact]
    extra = [field for field in artifact if field not in properties]
    reason_codes = [f"missing:{field}" for field in missing] + [f"additional_property:{field}" for field in extra]
    for field, definition in properties.items():
        if field not in artifact:
            continue
        value = artifact[field]
        if "const" in definition and value != definition["const"]:
            reason_codes.append(f"const_mismatch:{field}")
        enum = definition.get("enum")
        if enum and value not in enum:
            reason_codes.append(f"enum_mismatch:{field}")
        pattern = definition.get("pattern")
        if pattern == "^[a-f0-9]{64}$" and (not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)):
            reason_codes.append(f"hash_pattern_mismatch:{field}")
        expected_type = definition.get("type")
        if expected_type and not _type_matches(value, expected_type):
            reason_codes.append(f"type_mismatch:{field}")
    for rule in schema.get("allOf", []):
        for field, definition in rule.get("properties", {}).items():
            if "const" in definition and artifact.get(field) != definition["const"]:
                reason_codes.append(f"const_mismatch:{field}")
    return {
        "schema_path": str(schema_path),
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "required_count": len(required),
    }


def _type_matches(value: Any, expected_type: Any) -> bool:
    allowed = expected_type if isinstance(expected_type, list) else [expected_type]
    for type_name in allowed:
        if type_name == "string" and isinstance(value, str):
            return True
        if type_name == "null" and value is None:
            return True
        if type_name == "boolean" and isinstance(value, bool):
            return True
        if type_name == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if type_name == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if type_name == "object" and isinstance(value, dict):
            return True
        if type_name == "array" and isinstance(value, list):
            return True
    return False
