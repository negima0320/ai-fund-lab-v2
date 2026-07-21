from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, stable_json_hash, validate_artifact_against_schema, write_json
from ai_fund_lab_v2.ai_lifecycle.calibration_hash_inventory import self_reference_safe_manifest_hash


CREATED_AT = "2026-07-20T00:00:00+09:00"


def metric_payload_hash(payload: dict[str, Any]) -> str:
    return stable_json_hash(payload)


def content_hash(payload: dict[str, Any]) -> str:
    base = {k: v for k, v in payload.items() if k != "content_hash"}
    inventory = dict(base.get("hash_inventory", {}))
    for key in ("validation_artifact_file_sha256", "manifest_sha256", "content_sha256"):
        inventory.pop(key, None)
    base["hash_inventory"] = inventory
    return stable_json_hash(base)


def build_hash_inventory(
    *,
    artifact: dict[str, Any],
    candidate_calibration_artifact_path: Path,
    opportunity_calibration_artifact_path: Path,
    source_model_files: list[Path],
    source_scaler_files: list[Path],
    validation_policy_path: Path,
    metric_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "hash_schema_version": "phase19_ad_u5_validation_hash_inventory.v1",
        "validation_artifact_file_sha256": {"target": "self-reference-safe validation artifact manifest", "bytes": "manifest with self hash fields zeroed", "algorithm": "SHA256", "canonicalization": "SELF_REFERENCE_HASH_FIELDS_ZEROED_SORT_KEYS_COMPACT_JSON", "exclusions": ["hash_inventory.validation_artifact_file_sha256.sha256", "hash_inventory.manifest_sha256.sha256"], "sha256": "0" * 64},
        "candidate_calibration_artifact_sha256": {"target": "Candidate Calibration Artifact raw bytes", "bytes": str(candidate_calibration_artifact_path), "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES", "exclusions": [], "sha256": file_hash(candidate_calibration_artifact_path)},
        "opportunity_calibration_artifact_sha256": {"target": "Opportunity Calibration Artifact raw bytes", "bytes": str(opportunity_calibration_artifact_path), "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES", "exclusions": [], "sha256": file_hash(opportunity_calibration_artifact_path)},
        "source_model_raw_sha256": {"target": "source model raw bytes", "bytes": [str(p) for p in source_model_files], "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES", "exclusions": [], "sha256": [file_hash(p) for p in source_model_files]},
        "source_scaler_raw_sha256": {"target": "source scaler raw bytes", "bytes": [str(p) for p in source_scaler_files], "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES", "exclusions": [], "sha256": [file_hash(p) for p in source_scaler_files]},
        "validation_policy_sha256": {"target": "Approved Model Quality Policy raw bytes", "bytes": str(validation_policy_path), "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES", "exclusions": [], "sha256": file_hash(validation_policy_path)},
        "metric_payload_sha256": {"target": "canonical JSON of validation metric payload", "bytes": "canonical JSON", "algorithm": "SHA256", "canonicalization": "SORT_KEYS_COMPACT_JSON", "exclusions": [], "sha256": metric_payload_hash(metric_payload)},
        "content_sha256": {"target": "canonical JSON manifest payload excluding unstable self references", "bytes": "canonical JSON", "algorithm": "SHA256", "canonicalization": "SORT_KEYS_COMPACT_JSON", "exclusions": ["content_hash", "hash_inventory.validation_artifact_file_sha256", "hash_inventory.manifest_sha256", "hash_inventory.content_sha256"], "sha256": content_hash(artifact)},
        "manifest_sha256": {"target": "self-reference-safe validation artifact manifest", "bytes": "manifest with self hash fields zeroed", "algorithm": "SHA256", "canonicalization": "SELF_REFERENCE_HASH_FIELDS_ZEROED_SORT_KEYS_COMPACT_JSON", "exclusions": ["hash_inventory.validation_artifact_file_sha256.sha256", "hash_inventory.manifest_sha256.sha256"], "sha256": "0" * 64},
    }


def write_validation_artifact(*, artifact: dict[str, Any], path: Path, schema_dir: Path) -> dict[str, Any]:
    artifact["content_hash"] = content_hash(artifact)
    if "content_sha256" in artifact["hash_inventory"]:
        artifact["hash_inventory"]["content_sha256"]["sha256"] = artifact["content_hash"]
    write_json(path, artifact)
    safe_hash = self_reference_safe_manifest_hash(artifact)
    artifact["hash_inventory"]["validation_artifact_file_sha256"]["sha256"] = safe_hash
    artifact["hash_inventory"]["manifest_sha256"]["sha256"] = safe_hash
    write_json(path, artifact)
    schema_validation = validate_artifact_against_schema(artifact, schema_dir / "formal_validation_artifact.schema.json")
    return {
        "status": "PASS" if schema_validation["status"] == "PASS" else "BLOCK",
        "artifact": artifact,
        "artifact_path": str(path),
        "schema_validation": schema_validation,
    }

