from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn

from ai_fund_lab_v2.ai_lifecycle.ad_u3_dataset_input_resolver import ResolvedTrainingInput
from ai_fund_lab_v2.ai_lifecycle.ad_u3_scaling_contract import FittedScaler, scaler_parameters
from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, stable_json_hash, validate_artifact_against_schema


CREATED_AT = "2026-07-20T00:00:00+09:00"


def scaler_artifact_payload(
    *,
    resolved: ResolvedTrainingInput,
    fitted: FittedScaler,
    scaler_file: Path,
    corrective_action_policy: dict[str, Any],
    model_quality_policy: dict[str, Any],
    training_config_hash: str,
    training_code_commit: str,
    artifact_status: str,
    source_phase: str,
    authority: str,
) -> dict[str, Any]:
    parameters = scaler_parameters(fitted)
    parameter_hash = stable_json_hash(parameters)
    config = {
        "method": fitted.scaler_method,
        "with_mean": bool(getattr(fitted.scaler, "with_mean", True)),
        "with_std": bool(getattr(fitted.scaler, "with_std", True)),
        "copy": bool(getattr(fitted.scaler, "copy", True)),
        "fit_scope": "TRAIN_WINDOW_ONLY",
        "transform_scope": ["TRAIN", "VALIDATION", "TEST", "RECENT_HOLDOUT"],
        "binary_flags_scaled": False,
        "categorical_encoded_scaled": False,
    }
    payload: dict[str, Any] = {
        "artifact_id": f"{resolved.component.lower()}_scaler_{file_hash(scaler_file)[:16]}",
        "artifact_type": "SCALER",
        "artifact_version": "phase19_ad_u3_i_scaler_artifact.v1",
        "artifact_status": artifact_status,
        "created_at": CREATED_AT,
        "producer": "ai_fund_lab_v2.ai_lifecycle.ad_u3_scaler_artifact_writer",
        "source_phase": source_phase,
        "component": resolved.component,
        "generation_candidate_id": None,
        "scaler_method": fitted.scaler_method,
        "scaler_library": "sklearn.preprocessing.StandardScaler",
        "scaler_library_version": sklearn.__version__,
        "scaler_file": str(scaler_file),
        "scaler_content_hash": file_hash(scaler_file),
        "scaler_config": config,
        "scaler_config_hash": stable_json_hash(config),
        "fit_window": fitted.fit_window,
        "fit_row_count": fitted.fit_row_count,
        "fit_business_days": fitted.fit_business_days,
        "input_feature_columns": list(fitted.input_feature_columns),
        "scaled_feature_columns": list(fitted.scaled_feature_columns),
        "excluded_feature_columns": list(fitted.excluded_feature_columns),
        "feature_dtypes": {},
        "feature_schema_identity": resolved.feature_schema_identity,
        "fitted_parameters": parameters,
        "parameter_hash": parameter_hash,
        "dataset_input_contract_id": "phase19_ad_r2_ad_u3_dataset_input_contract_corrected"
        if not str(resolved.dataset_revision_id).startswith("fixture_")
        else "phase19_ad_u3_e_fixture_dataset_input_contract",
        "dataset_revision_id": resolved.dataset_revision_id,
        "dataset_content_hash": resolved.dataset_hash,
        "dataset_schema_hash": resolved.dataset_schema_hash,
        "dataset_lineage_hash": resolved.dataset_lineage_hash,
        "split_id": resolved.split_id,
        "split_content_hash": resolved.split_hash,
        "rolling_split_policy_hash": resolved.policy_hashes["rolling_split_policy_hash"],
        "corporate_action_policy_hash": resolved.policy_hashes["corporate_action_policy_hash"],
        "model_quality_policy_hash": str(model_quality_policy["policy_hash"]),
        "corrective_action_policy_hash": str(corrective_action_policy["policy_hash"]),
        "training_config_hash": training_config_hash,
        "training_code_commit": training_code_commit,
        "environment_fingerprint": stable_json_hash({"python": platform.python_version(), "platform": platform.platform(), "sklearn": sklearn.__version__}),
        "randomness_contract": {"randomness_used": False, "random_seed": None},
        "runtime_eligibility": False,
        "generation_eligibility": False,
        "accepted": False,
        "authority": authority,
        "content_hash": "0" * 64,
    }
    payload["content_hash"] = stable_json_hash({key: value for key, value in payload.items() if key != "content_hash"})
    return payload


def scaled_matrix_statistics(matrix: np.ndarray, feature_columns: list[str], scaled_feature_columns: list[str]) -> dict[str, Any]:
    index = {feature: idx for idx, feature in enumerate(feature_columns)}
    stats: dict[str, Any] = {}
    for feature in scaled_feature_columns:
        values = matrix[:, index[feature]]
        stats[feature] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "finite": bool(np.isfinite(values).all()),
        }
    return stats


def scaler_schema_validation(artifact: dict[str, Any], schema_dir: Path) -> dict[str, Any]:
    return validate_artifact_against_schema(artifact, schema_dir / "scaler_artifact.schema.json")


def infer_feature_dtypes(frame: pd.DataFrame, feature_columns: list[str]) -> dict[str, str]:
    return {feature: str(frame[feature].dtype) for feature in feature_columns}
