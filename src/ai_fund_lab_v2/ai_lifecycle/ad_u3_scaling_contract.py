from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import read_json, stable_json_hash


CREATED_AT = "2026-07-20T00:00:00+09:00"
APPROVED_CORRECTIVE_ACTION = "OPTION_A_CONTRACT_BOUND_FEATURE_SCALING"
APPROVED_POLICY_STATUS = "APPROVED"
APPROVED_REVIEWER = "user:negishi"
APPROVED_DECISION = "APPROVE"
DEFAULT_CORRECTIVE_ACTION_POLICY_PATH = Path(
    ".runtime/ai_lifecycle/policies/corrective_actions/"
    "phase19_ad_u3_i_feature_scaling/corrective_action_policy.json"
)

FeatureClass = Literal[
    "CONTINUOUS_NUMERIC_SCALE",
    "BINARY_FLAG",
    "CATEGORICAL_ENCODED",
    "IDENTIFIER",
    "DATE",
    "TARGET",
    "EXCLUDED",
]


class CorrectiveActionPolicyError(ValueError):
    """Fail-closed error for unapproved corrective-action policies."""


class ScalingContractError(ValueError):
    """Fail-closed error for scaling contract violations."""


@dataclass(frozen=True)
class FittedScaler:
    component: str
    scaler_method: str
    input_feature_columns: tuple[str, ...]
    scaled_feature_columns: tuple[str, ...]
    excluded_feature_columns: tuple[str, ...]
    feature_classes: dict[str, str]
    scaler: StandardScaler
    fit_window: dict[str, Any]
    fit_row_count: int
    fit_business_days: int


def materialize_corrective_action_policy_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "policy_id": "phase19_ad_u3_i_feature_scaling_corrective_action",
        "policy_version": "phase19_ad_u3_i_feature_scaling_corrective_action.v1",
        "policy_status": APPROVED_POLICY_STATUS,
        "reviewer": APPROVED_REVIEWER,
        "decision": APPROVED_DECISION,
        "reviewed_at": CREATED_AT,
        "approved_option": APPROVED_CORRECTIVE_ACTION,
        "approved_scope": {
            "dataset_revision_change_allowed": False,
            "split_change_allowed": False,
            "target_change_allowed": False,
            "feature_generation_change_allowed": False,
            "model_family_change_allowed": False,
            "feature_scaling_contract_allowed": True,
            "fixture_scaling_smoke_allowed": True,
            "formal_corrective_training_allowed": False,
        },
        "prohibited_changes": [
            "max_iter",
            "learning_rate",
            "eta0",
            "alpha",
            "tol",
            "model_family",
            "target_clipping",
            "prediction_clipping",
            "feature_removal",
            "runtime_pointer",
            "accepted_generation",
            "broker_write",
        ],
        "required_artifacts": [
            "scaler_artifact",
            "model_scaler_binding",
            "train_only_fit_evidence",
            "leakage_guard_evidence",
            "fixture_scaling_smoke_evidence",
        ],
        "required_fit_boundary": {
            "fit_on_training_window_only": True,
            "validation_transform_only": True,
            "test_transform_only": True,
            "recent_holdout_transform_only": True,
            "component_cross_fit_allowed": False,
        },
        "source_evidence": [
            "reports/phase19_ad_u3_h_training_root_cause_investigation/root_cause_classification.json",
            "reports/phase19_ad_u3_h_training_root_cause_investigation/opportunity_prediction_distribution.json",
            "reports/phase19_ad_u3_h_training_root_cause_investigation/sgd_configuration_review.json",
        ],
    }
    policy_hash = stable_json_hash({key: value for key, value in payload.items() if key not in {"policy_hash", "reviewed_policy_hash"}})
    payload["policy_hash"] = policy_hash
    payload["reviewed_policy_hash"] = policy_hash
    return payload


def load_approved_corrective_action_policy(path: Path | str = DEFAULT_CORRECTIVE_ACTION_POLICY_PATH) -> dict[str, Any]:
    payload = read_json(Path(path))
    validation = validate_approved_corrective_action_policy(payload)
    if validation["status"] != "PASS":
        raise CorrectiveActionPolicyError(";".join(validation["reason_codes"]))
    return payload


def validate_approved_corrective_action_policy(policy: dict[str, Any]) -> dict[str, Any]:
    reason_codes: list[str] = []
    if policy.get("policy_status") != APPROVED_POLICY_STATUS:
        reason_codes.append("corrective_policy_not_approved")
    if policy.get("reviewer") != APPROVED_REVIEWER:
        reason_codes.append("corrective_policy_wrong_reviewer")
    if policy.get("decision") != APPROVED_DECISION:
        reason_codes.append("corrective_policy_decision_not_approve")
    if policy.get("approved_option") != APPROVED_CORRECTIVE_ACTION:
        reason_codes.append("corrective_policy_wrong_option")
    computed = stable_json_hash({key: value for key, value in policy.items() if key not in {"policy_hash", "reviewed_policy_hash"}})
    if policy.get("policy_hash") != computed:
        reason_codes.append("corrective_policy_hash_mismatch")
    if policy.get("reviewed_policy_hash") != policy.get("policy_hash"):
        reason_codes.append("corrective_policy_reviewed_hash_mismatch")
    scope = policy.get("approved_scope") if isinstance(policy.get("approved_scope"), dict) else {}
    if scope.get("formal_corrective_training_allowed") is not False:
        reason_codes.append("formal_corrective_training_not_blocked_by_policy")
    return {
        "status": "PASS" if not reason_codes else "REJECTED",
        "reason_codes": reason_codes,
        "computed_policy_hash": computed,
        "policy_hash": policy.get("policy_hash"),
        "reviewed_policy_hash": policy.get("reviewed_policy_hash"),
    }


def scaler_method_comparison() -> dict[str, Any]:
    return {
        "status": "PASS",
        "comparison_basis": [
            "Phase19-AD-U3-H identified raw high-magnitude numeric features interacting with sklearn SGD.",
            "Current training matrices are dense numpy arrays, not sparse matrices.",
            "Dataset/target/model family must remain unchanged.",
        ],
        "methods": [
            {
                "method": "StandardScaler",
                "high_magnitude_feature_resistance": "HIGH_FOR_VARIANCE_SCALE_NORMALIZATION",
                "outlier_sensitivity": "MEDIUM",
                "sparse_matrix_compatibility": "NOT_REQUIRED_FOR_CURRENT_DENSE_MATRIX",
                "boolean_flag_handling": "EXCLUDE_BINARY_FLAGS",
                "candidate_opportunity_commonality": "HIGH",
                "runtime_transform_reproducibility": "HIGH_WITH_HASH_BOUND_MEAN_SCALE_PARAMETERS",
                "artifact_serialization": "PICKLE_INTERNAL_HASH_BOUND",
                "sklearn_sgd_compatibility": "HIGH",
            },
            {
                "method": "RobustScaler",
                "high_magnitude_feature_resistance": "HIGH",
                "outlier_sensitivity": "LOWER_THAN_STANDARD_SCALER",
                "sparse_matrix_compatibility": "NOT_REQUIRED_FOR_CURRENT_DENSE_MATRIX",
                "boolean_flag_handling": "EXCLUDE_BINARY_FLAGS",
                "candidate_opportunity_commonality": "HIGH",
                "runtime_transform_reproducibility": "HIGH_WITH_HASH_BOUND_MEDIAN_IQR_PARAMETERS",
                "artifact_serialization": "PICKLE_INTERNAL_HASH_BOUND",
                "sklearn_sgd_compatibility": "COMPATIBLE_BUT_CHANGES_ROBUST_CENTERING_POLICY",
            },
            {
                "method": "MaxAbsScaler",
                "high_magnitude_feature_resistance": "MEDIUM",
                "outlier_sensitivity": "HIGH",
                "sparse_matrix_compatibility": "HIGH_BUT_NOT_NEEDED",
                "boolean_flag_handling": "EXCLUDE_BINARY_FLAGS",
                "candidate_opportunity_commonality": "HIGH",
                "runtime_transform_reproducibility": "HIGH_WITH_HASH_BOUND_MAX_ABS_PARAMETERS",
                "artifact_serialization": "PICKLE_INTERNAL_HASH_BOUND",
                "sklearn_sgd_compatibility": "COMPATIBLE_BUT_DOES_NOT_CENTER_FEATURES",
            },
        ],
    }


def scaler_method_decision() -> dict[str, Any]:
    return {
        "status": "PASS",
        "decision": "STANDARD_SCALER",
        "human_review_required": False,
        "basis": [
            "The diagnosed root cause is SGD sensitivity to raw feature magnitude.",
            "Current matrices are dense, so sparse-preserving MaxAbsScaler is not required.",
            "StandardScaler supplies mean/scale parameters that are simple to hash-bind and replay in Runtime.",
            "Binary flags and categorical encodings are excluded from scaling, limiting semantic drift.",
            "RobustScaler remains a later option if StandardScaler smoke/formal evidence is insufficient.",
        ],
    }


def classify_features(columns: list[str], frame: pd.DataFrame, label_columns: set[str] | None = None) -> dict[str, str]:
    labels = label_columns or set()
    classes: dict[str, str] = {}
    for column in columns:
        if column in labels or column.startswith("label__"):
            classes[column] = "TARGET"
        elif column in {"code", "dataset_version", "feature_version", "label_version", "model_version", "feature_snapshot_id"}:
            classes[column] = "IDENTIFIER"
        elif column.endswith("_date") or column in {"target_date", "as_of_date", "created_at"}:
            classes[column] = "DATE"
        elif column.startswith("feature__missing_flags_") or pd.api.types.is_bool_dtype(frame[column]):
            classes[column] = "BINARY_FLAG"
        elif not pd.api.types.is_numeric_dtype(frame[column]):
            classes[column] = "CATEGORICAL_ENCODED"
        elif column.startswith("feature__"):
            classes[column] = "CONTINUOUS_NUMERIC_SCALE"
        else:
            classes[column] = "EXCLUDED"
    return classes


def scaling_feature_inventory(component: str, frame: pd.DataFrame, feature_columns: list[str], label_columns: list[str]) -> dict[str, Any]:
    classes = classify_features(feature_columns, frame, set(label_columns))
    scaled = [column for column in feature_columns if classes[column] == "CONTINUOUS_NUMERIC_SCALE"]
    excluded = [column for column in feature_columns if column not in scaled]
    return {
        "status": "PASS",
        "component": component,
        "feature_count": len(feature_columns),
        "scaled_feature_columns": scaled,
        "excluded_feature_columns": excluded,
        "feature_classes": classes,
        "policy": {
            "CONTINUOUS_NUMERIC_SCALE": "SCALE",
            "BINARY_FLAG": "PASS_THROUGH",
            "CATEGORICAL_ENCODED": "PASS_THROUGH_PENDING_EXPLICIT_REVIEW",
            "IDENTIFIER": "EXCLUDE",
            "DATE": "EXCLUDE",
            "TARGET": "EXCLUDE",
            "EXCLUDED": "EXCLUDE",
        },
    }


def fit_train_only_scaler(
    *,
    component: str,
    frames: dict[str, pd.DataFrame],
    feature_columns: list[str],
    label_columns: list[str],
    transformed_train: np.ndarray,
    split_definition: dict[str, Any],
) -> FittedScaler:
    inventory = scaling_feature_inventory(component, frames["train"], feature_columns, label_columns)
    scaled = tuple(inventory["scaled_feature_columns"])
    excluded = tuple(inventory["excluded_feature_columns"])
    if any(column in label_columns for column in scaled):
        raise ScalingContractError("target_column_in_scaling_scope")
    index_by_feature = {feature: index for index, feature in enumerate(feature_columns)}
    scaled_indices = [index_by_feature[column] for column in scaled]
    scaler = StandardScaler()
    if scaled_indices:
        scaler.fit(transformed_train[:, scaled_indices])
    else:
        scaler.fit(np.zeros((len(transformed_train), 1)))
    train = frames["train"]
    return FittedScaler(
        component=component,
        scaler_method="StandardScaler",
        input_feature_columns=tuple(feature_columns),
        scaled_feature_columns=scaled,
        excluded_feature_columns=excluded,
        feature_classes=dict(inventory["feature_classes"]),
        scaler=scaler,
        fit_window=dict(split_definition["train"]),
        fit_row_count=int(len(train)),
        fit_business_days=int(train["target_date"].nunique()) if "target_date" in train.columns else int(split_definition["train"].get("business_days", 0)),
    )


def transform_with_scaler(matrix: np.ndarray, fitted: FittedScaler) -> np.ndarray:
    result = np.array(matrix, dtype=np.float64, copy=True)
    index_by_feature = {feature: index for index, feature in enumerate(fitted.input_feature_columns)}
    scaled_indices = [index_by_feature[column] for column in fitted.scaled_feature_columns]
    if scaled_indices:
        result[:, scaled_indices] = fitted.scaler.transform(result[:, scaled_indices])
    return result


def scaler_parameters(fitted: FittedScaler) -> dict[str, Any]:
    return {
        "mean": [float(value) for value in np.ravel(getattr(fitted.scaler, "mean_", [])).tolist()],
        "scale": [float(value) for value in np.ravel(getattr(fitted.scaler, "scale_", [])).tolist()],
        "var": [float(value) for value in np.ravel(getattr(fitted.scaler, "var_", [])).tolist()],
        "n_features_in": int(getattr(fitted.scaler, "n_features_in_", 0)),
    }


def write_scaler_pickle(path: Path, fitted: FittedScaler) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "component": fitted.component,
        "scaler_method": fitted.scaler_method,
        "input_feature_columns": list(fitted.input_feature_columns),
        "scaled_feature_columns": list(fitted.scaled_feature_columns),
        "excluded_feature_columns": list(fitted.excluded_feature_columns),
        "feature_classes": fitted.feature_classes,
        "scaler": fitted.scaler,
    }
    with path.open("wb") as handle:
        pickle.dump(payload, handle)
