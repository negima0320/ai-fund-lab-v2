from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import (
    file_hash,
    stable_json_hash,
    validate_artifact_against_schema,
    write_json,
)
from ai_fund_lab_v2.ai_lifecycle.calibration_hash_inventory import (
    build_initial_hash_inventory,
    content_hash,
    finalize_file_hashes,
    parameter_hash,
    validate_hash_inventory,
)


CREATED_AT = "2026-07-20T00:00:00+09:00"


class CalibrationArtifactError(ValueError):
    """Fail-closed error for invalid calibration artifacts."""


def build_calibration_artifact(
    *,
    component: str,
    source_model_artifact: dict[str, Any],
    source_scaler_artifact: dict[str, Any],
    dataset_usage_contract: dict[str, Any],
    source_model_file: Path,
    source_scaler_file: Path,
    calibration_method: str,
    calibration_method_version: str,
    calibration_config: dict[str, Any],
    calibration_parameters: dict[str, Any],
    fit_window: dict[str, Any],
    input_score_schema: dict[str, Any],
    output_score_schema: dict[str, Any],
    quality_metrics: dict[str, Any],
    quality_gate_result: dict[str, Any],
    source_phase: str = "PHASE19_AD_U4_C",
) -> dict[str, Any]:
    model_hash = file_hash(source_model_file)
    scaler_hash = file_hash(source_scaler_file)
    if model_hash != source_model_artifact.get("model_content_hash"):
        raise CalibrationArtifactError("source_model_hash_mismatch")
    if scaler_hash != source_scaler_artifact.get("scaler_content_hash"):
        raise CalibrationArtifactError("source_scaler_hash_mismatch")
    if source_model_artifact.get("artifact_status") not in {"TRAINING_OUTPUT", "FIXTURE_TRAINING_OUTPUT"}:
        raise CalibrationArtifactError("source_artifact_not_training_output")
    if source_model_artifact.get("runtime_eligibility") is not False or source_model_artifact.get("accepted") is not False:
        raise CalibrationArtifactError("source_artifact_runtime_or_accepted")

    config_hash = stable_json_hash(calibration_config)
    payload: dict[str, Any] = {
        "artifact_id": "pending",
        "artifact_status": "CALIBRATION_OUTPUT",
        "schema_version": "phase19_ad_u4_c_calibration_artifact.v1",
        "artifact_type": "CALIBRATION",
        "artifact_version": "phase19_ad_u4_c_calibration_artifact.v1",
        "created_at": CREATED_AT,
        "producer": "ai_fund_lab_v2.ai_lifecycle.calibration_artifact_writer",
        "source_phase": source_phase,
        "component": component,
        "generation_candidate_id": None,
        "authority": "Fixture calibration output only; not Runtime authority",
        "dataset_revision": {"dataset_revision_id": source_model_artifact["dataset_revision_id"]},
        "dataset_revision_id": source_model_artifact["dataset_revision_id"],
        "dataset_content_hash": source_model_artifact["dataset_content_hash"],
        "dataset_schema_hash": source_model_artifact["dataset_schema_hash"],
        "dataset_lineage_hash": source_model_artifact["dataset_lineage_hash"],
        "split_id": source_model_artifact["split_id"],
        "split_content_hash": source_model_artifact["split_content_hash"],
        "dataset_usage_contract": dataset_usage_contract,
        "dataset_usage_contract_hash": dataset_usage_contract["contract_hash"],
        "source_model_artifact": {"artifact_id": source_model_artifact["artifact_id"], "artifact_status": source_model_artifact["artifact_status"]},
        "source_model_artifact_id": source_model_artifact["artifact_id"],
        "source_model_hash": model_hash,
        "source_model_hash_target": {"target": "source model raw serialized bytes", "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES"},
        "source_scaler_artifact": {"artifact_id": source_scaler_artifact["artifact_id"], "artifact_status": source_scaler_artifact["artifact_status"]},
        "source_scaler_artifact_id": source_scaler_artifact["artifact_id"],
        "source_scaler_hash": scaler_hash,
        "source_scaler_hash_target": {"target": "source scaler raw serialized bytes", "algorithm": "SHA256", "canonicalization": "NONE_RAW_BYTES"},
        "feature_order": list(source_model_artifact["feature_columns"]),
        "feature_schema_identity": source_model_artifact["feature_schema_identity"],
        "label_schema_identity": source_model_artifact["label_schema_identity"],
        "trading_calendar_identity": source_model_artifact["trading_calendar_identity"],
        "target_horizon_business_days": source_model_artifact["target_horizon_business_days"],
        "embargo_business_days": source_model_artifact["embargo_business_days"],
        "bootstrap_or_retraining": source_model_artifact["bootstrap_or_retraining"],
        "rolling_split_policy_hash": source_model_artifact["rolling_split_policy_hash"],
        "corporate_action_policy_hash": source_model_artifact["corporate_action_policy_hash"],
        "model_quality_policy_hash": source_model_artifact["model_quality_policy_hash"],
        "calibration_method": calibration_method,
        "calibration_method_version": calibration_method_version,
        "calibration_config": calibration_config,
        "calibration_config_hash": config_hash,
        "calibration_parameters": calibration_parameters,
        "calibration_parameter_hash": parameter_hash(calibration_parameters),
        "fit_window": fit_window,
        "fit_window_role": "CALIBRATION_FIT_WINDOW",
        "input_score_schema": input_score_schema,
        "output_score_schema": output_score_schema,
        "quality_metrics": quality_metrics,
        "quality_gate_result": quality_gate_result,
        "hash_inventory": {},
        "runtime_eligibility": False,
        "generation_eligibility": False,
        "accepted": False,
        "content_hash": "0" * 64,
    }
    payload["artifact_id"] = f"fixture_calibration_{component.lower()}_{stable_json_hash({'component': component, 'parameters': calibration_parameters})[:16]}"
    payload["hash_inventory"] = build_initial_hash_inventory(
        source_model_file=source_model_file,
        source_scaler_file=source_scaler_file,
        calibration_parameters=calibration_parameters,
        content_sha256="0" * 64,
    )
    payload["content_hash"] = content_hash(payload)
    payload["hash_inventory"]["content_sha256"]["sha256"] = payload["content_hash"]
    payload["content_hash"] = content_hash(payload)
    payload["hash_inventory"]["content_sha256"]["sha256"] = payload["content_hash"]
    return payload


def write_calibration_artifact(
    *,
    artifact: dict[str, Any],
    artifact_path: Path,
    schema_dir: Path,
    source_model_file: Path,
    source_scaler_file: Path,
) -> dict[str, Any]:
    write_json(artifact_path, artifact)
    artifact["hash_inventory"] = finalize_file_hashes(artifact_path, artifact)
    write_json(artifact_path, artifact)
    validation = validate_artifact_against_schema(artifact, schema_dir / "calibration_artifact.schema.json")
    hash_validation = validate_hash_inventory(
        artifact=artifact,
        artifact_path=artifact_path,
        source_model_file=source_model_file,
        source_scaler_file=source_scaler_file,
    )
    return {
        "status": "PASS" if validation["status"] == "PASS" and hash_validation["status"] == "PASS" else "REVIEW_REQUIRED",
        "artifact_path": str(artifact_path),
        "schema_validation": validation,
        "hash_validation": hash_validation,
        "artifact": artifact,
    }

