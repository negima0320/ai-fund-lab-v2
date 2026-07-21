from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import transform_features
from ai_fund_lab_v2.runtime_v2.accepted_generation_consumer_adapter import validate_manifest_compatibility
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import AcceptedGenerationResolution


ComponentName = Literal["candidate", "opportunity"]


class GenerationBoundInferenceError(RuntimeError):
    """Fail-closed Runtime inference error for Accepted Generation bindings."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        super().__init__(message or reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class GenerationBoundInferenceBinding:
    component: ComponentName
    accepted_generation_id: str
    manifest_path: Path
    manifest_hash: str
    model_path: Path
    model_hash: str
    scaler_path: Path
    scaler_hash: str
    calibration_ref: str
    calibration_hash: str
    feature_order: tuple[str, ...]
    feature_order_hash: str
    prediction_schema: dict[str, Any]
    model_payload: dict[str, Any]
    scaler_payload: dict[str, Any]

    def evidence(self) -> dict[str, Any]:
        return {
            "schema_version": "runtime_v2_accepted_generation_bound_inference_v1",
            "component": self.component,
            "accepted_generation_id": self.accepted_generation_id,
            "manifest_path": str(self.manifest_path),
            "manifest_hash": self.manifest_hash,
            "model_file": str(self.model_path),
            "model_hash": self.model_hash,
            "runtime_model_hash": _file_hash(self.model_path),
            "scaler_file": str(self.scaler_path),
            "scaler_hash": self.scaler_hash,
            "runtime_scaler_hash": _file_hash(self.scaler_path),
            "calibration_ref": self.calibration_ref,
            "calibration_hash": self.calibration_hash,
            "feature_order_hash": self.feature_order_hash,
            "feature_order": list(self.feature_order),
            "prediction_schema": self.prediction_schema,
            "preprocessing_contract": "model_payload_preprocessing_then_generation_bound_standard_scaler",
            "transformation_stage": "accepted_generation_bound_imputer_scaler_model",
            "legacy_fallback_used": False,
            "manual_path_used": False,
        }


def load_generation_bound_binding(
    *,
    resolution: AcceptedGenerationResolution,
    component: ComponentName,
    repo_root: Path | str = ".",
) -> GenerationBoundInferenceBinding:
    if not resolution.is_resolved:
        raise GenerationBoundInferenceError("accepted_generation_not_resolved")
    manifest_path = Path(resolution.bundle_manifest_path)
    if not manifest_path.is_file():
        raise GenerationBoundInferenceError("accepted_generation_manifest_missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive integrity boundary
        raise GenerationBoundInferenceError("accepted_generation_manifest_unreadable") from exc
    compatibility = validate_manifest_compatibility(manifest, repo_root=repo_root, load_pickles=True)
    if compatibility.status != "PASS":
        reason = str((compatibility.reason_codes or ("accepted_generation_consumer_compatibility_failed",))[0])
        raise GenerationBoundInferenceError(reason)
    member = compatibility.candidate if component == "candidate" else compatibility.opportunity
    if member is None:
        raise GenerationBoundInferenceError(f"{component}_member_missing")
    model_path = Path(member.model_file)
    scaler_path = Path(member.scaler_file)
    model_payload = _load_pickle_dict(model_path, "model_load_failure")
    scaler_payload = _load_pickle_dict(scaler_path, "scaler_load_failure")
    feature_order = tuple(member.feature_order)
    model_feature_columns = tuple(str(column) for column in model_payload.get("feature_columns") or ())
    scaler_input_columns = tuple(str(column) for column in scaler_payload.get("input_feature_columns") or ())
    if not feature_order or model_feature_columns != feature_order or scaler_input_columns != feature_order:
        raise GenerationBoundInferenceError("feature_order_mismatch")
    if _file_hash(model_path) != member.model_hash:
        raise GenerationBoundInferenceError("model_hash_mismatch")
    if _file_hash(scaler_path) != member.scaler_hash:
        raise GenerationBoundInferenceError("scaler_hash_mismatch")
    if "scaler" not in scaler_payload:
        raise GenerationBoundInferenceError("missing_scaler")
    return GenerationBoundInferenceBinding(
        component=component,
        accepted_generation_id=resolution.generation_id,
        manifest_path=manifest_path,
        manifest_hash=compatibility.manifest_hash,
        model_path=model_path,
        model_hash=member.model_hash,
        scaler_path=scaler_path,
        scaler_hash=member.scaler_hash,
        calibration_ref=member.calibration_ref,
        calibration_hash=member.calibration_hash,
        feature_order=feature_order,
        feature_order_hash=member.feature_order_hash,
        prediction_schema=member.prediction_schema,
        model_payload=model_payload,
        scaler_payload=scaler_payload,
    )


def generation_bound_matrix(binding: GenerationBoundInferenceBinding, frame: pd.DataFrame) -> np.ndarray:
    materialized = _materialize_feature_columns(frame, binding.feature_order)
    raw = transform_features(materialized, list(binding.feature_order), binding.model_payload["preprocessing"])
    result = np.array(raw, dtype=np.float64, copy=True)
    index_by_feature = {feature: idx for idx, feature in enumerate(binding.scaler_payload["input_feature_columns"])}
    try:
        scaled_indices = [index_by_feature[column] for column in binding.scaler_payload["scaled_feature_columns"]]
    except KeyError as exc:
        raise GenerationBoundInferenceError("feature_order_mismatch") from exc
    if scaled_indices:
        result[:, scaled_indices] = binding.scaler_payload["scaler"].transform(result[:, scaled_indices])
    if not np.isfinite(result).all():
        raise GenerationBoundInferenceError("inference_feature_matrix_non_finite")
    return result


def predict_generation_bound_scores(binding: GenerationBoundInferenceBinding, frame: pd.DataFrame) -> np.ndarray:
    matrix = generation_bound_matrix(binding, frame)
    model = binding.model_payload["model"]
    if binding.component == "candidate":
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(matrix)
            if getattr(proba, "ndim", 0) == 2 and proba.shape[1] > 1:
                scores = np.asarray(proba[:, 1], dtype=float)
            else:
                scores = np.asarray(proba, dtype=float).reshape(-1)
        elif hasattr(model, "decision_function"):
            raw = np.asarray(model.decision_function(matrix), dtype=float)
            scores = 1.0 / (1.0 + np.exp(-raw))
        else:
            scores = np.asarray(model.predict(matrix), dtype=float)
    else:
        scores = np.asarray(model.predict(matrix), dtype=float)
    if not np.isfinite(scores).all():
        raise GenerationBoundInferenceError("prediction_non_finite")
    return scores


def _materialize_feature_columns(frame: pd.DataFrame, feature_order: tuple[str, ...]) -> pd.DataFrame:
    materialized = frame.copy()
    missing: list[str] = []
    for column in feature_order:
        if column in materialized.columns:
            continue
        unprefixed = column.replace("feature__", "", 1)
        if unprefixed in materialized.columns:
            materialized[column] = materialized[unprefixed]
        else:
            missing.append(column)
    if missing:
        raise GenerationBoundInferenceError("feature_order_mismatch", f"missing generation-bound features: {missing}")
    return materialized


def _load_pickle_dict(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except Exception as exc:
        raise GenerationBoundInferenceError(reason_code) from exc
    if not isinstance(payload, dict):
        raise GenerationBoundInferenceError(reason_code)
    return payload


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
