from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, stable_json_hash, validate_artifact_against_schema, write_json
from ai_fund_lab_v2.ai_lifecycle.calibration_hash_inventory import self_reference_safe_manifest_hash


CREATED_AT = "2026-07-20T00:00:00+09:00"


def build_dual_gate_artifact(
    *,
    artifact_id: str,
    global_gate_result: dict[str, Any],
    selection_gate_result: dict[str, Any],
    dual_gate_result: dict[str, Any],
    bindings: dict[str, Any],
    hash_sources: dict[str, Path],
) -> dict[str, Any]:
    artifact = {
        "artifact_id": artifact_id,
        "artifact_type": "OPPORTUNITY_DUAL_GATE_ARTIFACT",
        "artifact_version": "phase19_ah_opportunity_dual_gate.v1",
        "artifact_status": dual_gate_result["status"],
        "created_at": CREATED_AT,
        "producer": "ai_fund_lab_v2.ai_lifecycle.dual_gate_artifact_writer",
        "source_phase": "PHASE19_AH",
        "schema_version": "phase19_ah_opportunity_dual_gate_artifact.v1",
        "authority": "Generation Acceptance evidence only; not Runtime authority",
        "global_gate_result": global_gate_result,
        "selection_gate_result": selection_gate_result,
        "dual_gate_result": dual_gate_result,
        "bindings": bindings,
        "generation_eligibility": bool(dual_gate_result["generation_eligibility"]),
        "runtime_eligibility": False,
        "accepted": False,
        "hash_inventory": {},
        "content_hash": "0" * 64,
    }
    artifact["hash_inventory"] = build_hash_inventory(artifact=artifact, hash_sources=hash_sources)
    artifact["content_hash"] = _content_hash(artifact)
    artifact["hash_inventory"]["content_sha256"]["sha256"] = artifact["content_hash"]
    return artifact


def build_hash_inventory(*, artifact: dict[str, Any], hash_sources: dict[str, Path]) -> dict[str, Any]:
    return {
        "dual_gate_artifact_file_sha256": _hash_entry("self-reference-safe dual gate artifact", "SELF_REFERENCE_HASH_FIELDS_ZEROED_SORT_KEYS_COMPACT_JSON", "0" * 64, ["hash_inventory.dual_gate_artifact_file_sha256.sha256", "hash_inventory.manifest_sha256.sha256"]),
        "global_gate_payload_sha256": _hash_entry("Global Gate payload canonical JSON", "SORT_KEYS_COMPACT_JSON", stable_json_hash(artifact["global_gate_result"]), []),
        "selection_gate_payload_sha256": _hash_entry("Selection Gate payload canonical JSON", "SORT_KEYS_COMPACT_JSON", stable_json_hash(artifact["selection_gate_result"]), []),
        "candidate_source_artifact_sha256": _file_hash_entry("Candidate source artifact raw bytes", hash_sources["candidate_source_artifact"]),
        "formal_validation_artifact_sha256": _file_hash_entry("Formal Validation artifact raw bytes", hash_sources["formal_validation_artifact"]),
        "dual_gate_contract_sha256": _file_hash_entry("Dual Gate contract raw bytes", hash_sources["dual_gate_contract"]),
        "runtime_separation_contract_sha256": _file_hash_entry("Runtime Separation contract raw bytes", hash_sources["runtime_separation_contract"]),
        "content_sha256": _hash_entry("canonical JSON artifact content", "SORT_KEYS_COMPACT_JSON", "0" * 64, ["content_hash", "hash_inventory.dual_gate_artifact_file_sha256", "hash_inventory.manifest_sha256", "hash_inventory.content_sha256"]),
        "manifest_sha256": _hash_entry("self-reference-safe dual gate artifact", "SELF_REFERENCE_HASH_FIELDS_ZEROED_SORT_KEYS_COMPACT_JSON", "0" * 64, ["hash_inventory.dual_gate_artifact_file_sha256.sha256", "hash_inventory.manifest_sha256.sha256"]),
    }


def write_dual_gate_artifact(*, artifact: dict[str, Any], path: Path, schema_dir: Path) -> dict[str, Any]:
    write_json(path, artifact)
    safe_hash = self_reference_safe_manifest_hash(artifact)
    artifact["hash_inventory"]["dual_gate_artifact_file_sha256"]["sha256"] = safe_hash
    artifact["hash_inventory"]["manifest_sha256"]["sha256"] = safe_hash
    write_json(path, artifact)
    schema_validation = validate_artifact_against_schema(artifact, schema_dir / "opportunity_dual_gate_artifact.schema.json")
    return {
        "status": "PASS" if schema_validation["status"] == "PASS" else "BLOCK",
        "artifact_path": str(path),
        "artifact": artifact,
        "schema_validation": schema_validation,
    }


def _content_hash(artifact: dict[str, Any]) -> str:
    payload = {k: v for k, v in artifact.items() if k != "content_hash"}
    inventory = dict(payload.get("hash_inventory", {}))
    for key in ("dual_gate_artifact_file_sha256", "manifest_sha256", "content_sha256"):
        inventory.pop(key, None)
    payload["hash_inventory"] = inventory
    return stable_json_hash(payload)


def _hash_entry(target: str, canonicalization: str, sha256: str, exclusions: list[str]) -> dict[str, Any]:
    return {
        "target": target,
        "bytes": "canonical JSON" if canonicalization != "NONE_RAW_BYTES" else "raw bytes",
        "algorithm": "SHA256",
        "canonicalization": canonicalization,
        "exclusions": exclusions,
        "sha256": sha256,
    }


def _file_hash_entry(target: str, path: Path) -> dict[str, Any]:
    return {
        "target": target,
        "bytes": str(path),
        "algorithm": "SHA256",
        "canonicalization": "NONE_RAW_BYTES",
        "exclusions": [],
        "sha256": file_hash(path),
    }
