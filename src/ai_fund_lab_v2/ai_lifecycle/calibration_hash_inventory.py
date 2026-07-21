from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, stable_json_hash


class CalibrationHashInventoryError(ValueError):
    """Fail-closed error for ambiguous or mismatched calibration hashes."""


HASH_TARGETS: dict[str, dict[str, Any]] = {
    "artifact_file_sha256": {
        "target": "self-reference-safe bytes of written calibration artifact manifest file",
        "bytes": "artifact_manifest.json with artifact_file_sha256 and manifest_sha256 values zeroed",
        "algorithm": "SHA256",
        "canonicalization": "SELF_REFERENCE_HASH_FIELDS_ZEROED_SORT_KEYS_COMPACT_JSON",
        "exclusions": ["hash_inventory.artifact_file_sha256.sha256", "hash_inventory.manifest_sha256.sha256"],
    },
    "serialized_model_sha256": {
        "target": "raw bytes of source model serialization file bound by source_model_artifact",
        "bytes": "source model file",
        "algorithm": "SHA256",
        "canonicalization": "NONE_RAW_BYTES",
        "exclusions": [],
    },
    "serialized_scaler_sha256": {
        "target": "raw bytes of source scaler serialization file bound by source_scaler_artifact",
        "bytes": "source scaler file",
        "algorithm": "SHA256",
        "canonicalization": "NONE_RAW_BYTES",
        "exclusions": [],
    },
    "calibration_parameter_sha256": {
        "target": "canonical JSON of calibration_parameters only",
        "bytes": "canonical JSON",
        "algorithm": "SHA256",
        "canonicalization": "SORT_KEYS_COMPACT_JSON",
        "exclusions": [],
    },
    "manifest_sha256": {
        "target": "self-reference-safe bytes of manifest file as persisted",
        "bytes": "artifact_manifest.json with artifact_file_sha256 and manifest_sha256 values zeroed",
        "algorithm": "SHA256",
        "canonicalization": "SELF_REFERENCE_HASH_FIELDS_ZEROED_SORT_KEYS_COMPACT_JSON",
        "exclusions": ["hash_inventory.artifact_file_sha256.sha256", "hash_inventory.manifest_sha256.sha256"],
    },
    "content_sha256": {
        "target": "canonical JSON manifest payload excluding unstable self references",
        "bytes": "canonical JSON",
        "algorithm": "SHA256",
        "canonicalization": "SORT_KEYS_COMPACT_JSON",
        "exclusions": ["content_hash", "hash_inventory.artifact_file_sha256", "hash_inventory.manifest_sha256", "hash_inventory.content_sha256"],
    },
}


def canonical_content_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in artifact.items() if key != "content_hash"}
    inventory = dict(payload.get("hash_inventory", {}))
    inventory.pop("artifact_file_sha256", None)
    inventory.pop("manifest_sha256", None)
    inventory.pop("content_sha256", None)
    payload["hash_inventory"] = inventory
    return payload


def parameter_hash(parameters: dict[str, Any]) -> str:
    return stable_json_hash(parameters)


def content_hash(artifact: dict[str, Any]) -> str:
    return stable_json_hash(canonical_content_payload(artifact))


def self_reference_safe_manifest_hash(artifact: dict[str, Any]) -> str:
    payload = {key: value for key, value in artifact.items()}
    inventory = dict(payload.get("hash_inventory", {}))
    for key in ("artifact_file_sha256", "manifest_sha256"):
        if key in inventory and isinstance(inventory[key], dict):
            inventory[key] = {**inventory[key], "sha256": "0" * 64}
    payload["hash_inventory"] = inventory
    return stable_json_hash(payload)


def build_initial_hash_inventory(
    *,
    source_model_file: Path,
    source_scaler_file: Path,
    calibration_parameters: dict[str, Any],
    content_sha256: str,
) -> dict[str, Any]:
    return {
        "hash_schema_version": "phase19_ad_u4_c_hash_inventory.v1",
        "artifact_file_sha256": {**HASH_TARGETS["artifact_file_sha256"], "sha256": "0" * 64},
        "serialized_model_sha256": {**HASH_TARGETS["serialized_model_sha256"], "sha256": file_hash(source_model_file)},
        "serialized_scaler_sha256": {**HASH_TARGETS["serialized_scaler_sha256"], "sha256": file_hash(source_scaler_file)},
        "calibration_parameter_sha256": {**HASH_TARGETS["calibration_parameter_sha256"], "sha256": parameter_hash(calibration_parameters)},
        "manifest_sha256": {**HASH_TARGETS["manifest_sha256"], "sha256": "0" * 64},
        "content_sha256": {**HASH_TARGETS["content_sha256"], "sha256": content_sha256},
    }


def finalize_file_hashes(artifact_path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    digest = self_reference_safe_manifest_hash(artifact)
    inventory = dict(artifact["hash_inventory"])
    inventory["artifact_file_sha256"] = {**inventory["artifact_file_sha256"], "sha256": digest}
    inventory["manifest_sha256"] = {**inventory["manifest_sha256"], "sha256": digest}
    return inventory


def validate_hash_inventory(
    *,
    artifact: dict[str, Any],
    artifact_path: Path | None = None,
    source_model_file: Path | None = None,
    source_scaler_file: Path | None = None,
) -> dict[str, Any]:
    reason_codes: list[str] = []
    inventory = artifact.get("hash_inventory") if isinstance(artifact.get("hash_inventory"), dict) else {}
    for key in HASH_TARGETS:
        if key not in inventory:
            reason_codes.append(f"missing_hash:{key}")
        elif not isinstance(inventory[key], dict) or inventory[key].get("algorithm") != "SHA256":
            reason_codes.append(f"invalid_hash_target:{key}")
    if source_model_file and inventory.get("serialized_model_sha256", {}).get("sha256") != file_hash(source_model_file):
        reason_codes.append("serialized_model_sha256_mismatch")
    if source_scaler_file and inventory.get("serialized_scaler_sha256", {}).get("sha256") != file_hash(source_scaler_file):
        reason_codes.append("serialized_scaler_sha256_mismatch")
    if inventory.get("serialized_model_sha256", {}).get("sha256") != artifact.get("source_model_hash"):
        reason_codes.append("source_model_hash_mismatch")
    if inventory.get("serialized_scaler_sha256", {}).get("sha256") != artifact.get("source_scaler_hash"):
        reason_codes.append("source_scaler_hash_mismatch")
    if inventory.get("calibration_parameter_sha256", {}).get("sha256") != parameter_hash(artifact.get("calibration_parameters", {})):
        reason_codes.append("calibration_parameter_sha256_mismatch")
    recomputed_content = content_hash(artifact)
    if inventory.get("content_sha256", {}).get("sha256") != recomputed_content or artifact.get("content_hash") != recomputed_content:
        reason_codes.append("content_sha256_mismatch")
    if artifact_path:
        actual_file_hash = self_reference_safe_manifest_hash(artifact)
        if inventory.get("artifact_file_sha256", {}).get("sha256") != actual_file_hash:
            reason_codes.append("artifact_file_sha256_mismatch")
        if inventory.get("manifest_sha256", {}).get("sha256") != actual_file_hash:
            reason_codes.append("manifest_sha256_mismatch")
    return {
        "status": "PASS" if not reason_codes else "REVIEW_REQUIRED",
        "reason_codes": reason_codes,
        "hash_count": len(inventory),
    }
